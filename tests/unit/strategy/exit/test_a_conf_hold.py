"""a_conf_hold.py için birim testler (TDD §6.9)."""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.a_conf_hold import is_a_conf_hold, market_flip_exit


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.65, size_usdc=40, shares=60, current_price=0.65,
        anchor_probability=0.70, confidence="A",
    )
    base.update(over)
    return Position(**base)


# ── is_a_conf_hold ──

def test_a_conf_above_60c_is_hold() -> None:
    assert is_a_conf_hold(_pos(confidence="A", entry_price=0.65)) is True


def test_a_conf_at_60c_is_hold() -> None:
    assert is_a_conf_hold(_pos(confidence="A", entry_price=0.60)) is True


def test_a_conf_below_60c_not_hold() -> None:
    assert is_a_conf_hold(_pos(confidence="A", entry_price=0.55)) is False


def test_b_conf_never_hold() -> None:
    assert is_a_conf_hold(_pos(confidence="B", entry_price=0.70)) is False


def test_buy_no_uses_token_native_entry() -> None:
    # BUY_NO entry_price zaten NO token fiyatı (owned side). 0.65 ≥ 0.60 → hold.
    assert is_a_conf_hold(_pos(confidence="A", entry_price=0.65, direction="BUY_NO")) is True


# ── market_flip_exit ──

def test_early_match_flip_ignored() -> None:
    # elapsed < 0.85 → flip asla tetiklenmez
    p = _pos(entry_price=0.65, current_price=0.30)
    assert market_flip_exit(p, elapsed_pct=0.50) is False
    assert market_flip_exit(p, elapsed_pct=0.84) is False


def test_late_match_flip_triggers_below_50c() -> None:
    p = _pos(entry_price=0.65, current_price=0.40)  # eff = 0.40 < 0.50
    assert market_flip_exit(p, elapsed_pct=0.85) is True


def test_late_match_no_flip_above_50c() -> None:
    p = _pos(entry_price=0.65, current_price=0.55)  # eff 0.55 >= 0.50
    assert market_flip_exit(p, elapsed_pct=0.90) is False


def test_flip_buy_no_uses_token_native() -> None:
    # BUY_NO current_price = NO token fiyatı. 0.40 < 0.50 → owned flip'e düştü.
    p = _pos(entry_price=0.65, direction="BUY_NO", current_price=0.40)
    assert market_flip_exit(p, elapsed_pct=0.90) is True
