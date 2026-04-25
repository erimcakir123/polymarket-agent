"""price_cap.py — SLParams + check() birim testleri (PLAN-014)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.strategy.exit.price_cap import SLParams, check

_SL = SLParams(enabled=True, price_below=0.50, max_loss_usd=12.0, min_elapsed_pct=0.75)


def _pos(current_price: float, unrealized_pnl_usdc: float) -> MagicMock:
    pos = MagicMock()
    pos.current_price = current_price
    pos.unrealized_pnl_usdc = unrealized_pnl_usdc
    return pos


def test_check_false_when_disabled() -> None:
    sl = SLParams(enabled=False, price_below=0.50, max_loss_usd=12.0)
    assert check(_pos(0.30, -15.0), sl, 0.90) is False


def test_check_false_when_too_early() -> None:
    # elapsed_pct < min_elapsed_pct → SL çalışmaz
    assert check(_pos(0.30, -15.0), _SL, 0.50) is False


def test_check_false_when_price_above_threshold() -> None:
    # current_price >= price_below → kayıp yok
    assert check(_pos(0.55, -5.0), _SL, 0.90) is False


def test_check_false_when_loss_below_threshold() -> None:
    # Fiyat düştü ama kayıp max_loss_usd'nin altında
    assert check(_pos(0.35, -8.0), _SL, 0.90) is False


def test_check_true_when_all_conditions_met() -> None:
    # Fiyat < 0.50, loss > 12, elapsed > 0.75 → SL tetiklenir
    assert check(_pos(0.35, -13.0), _SL, 0.90) is True


def test_check_true_at_exact_loss_threshold() -> None:
    # loss == max_loss_usd (>=) → tetiklenir
    assert check(_pos(0.40, -12.0), _SL, 0.80) is True


def test_check_false_at_exact_price_threshold() -> None:
    # current_price == price_below (>=) → tetiklenmez
    assert check(_pos(0.50, -15.0), _SL, 0.90) is False


def test_check_false_at_exact_elapsed_threshold() -> None:
    # elapsed_pct == min_elapsed_pct (< değil) → çalışır, diğer koşullar
    # burada price OK ama kontrol: elapsed'ın tam eşikte davranışı
    assert check(_pos(0.30, -15.0), _SL, 0.75) is True


def test_slparams_default_min_elapsed() -> None:
    sl = SLParams(enabled=True, price_below=0.50, max_loss_usd=12.0)
    assert sl.min_elapsed_pct == 0.75
