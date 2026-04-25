"""scale_out.check() birim testleri."""
from __future__ import annotations

from src.strategy.exit.scale_out import ScaleOutResult, check


def test_check_returns_none_below_threshold() -> None:
    assert check(bid_price=0.84, already_scaled=False, threshold=0.85) is None


def test_check_returns_result_at_threshold() -> None:
    result = check(bid_price=0.85, already_scaled=False, threshold=0.85)
    assert result is not None
    assert result.sell_pct == 0.50
    assert result.tier == 1


def test_check_returns_result_above_threshold() -> None:
    result = check(bid_price=0.86, already_scaled=False, threshold=0.85)
    assert result is not None
    assert result.sell_pct == 0.50


def test_check_returns_none_when_already_scaled() -> None:
    assert check(bid_price=0.87, already_scaled=True, threshold=0.85) is None


def test_check_returns_none_when_both_low_and_scaled() -> None:
    assert check(bid_price=0.80, already_scaled=True, threshold=0.85) is None


def test_check_default_threshold() -> None:
    assert check(bid_price=0.84, already_scaled=False) is None
    assert check(bid_price=0.85, already_scaled=False) is not None


def test_result_reason_contains_price() -> None:
    result = check(bid_price=0.87, already_scaled=False, threshold=0.85)
    assert result is not None
    assert "0.87" in result.reason or "0.870" in result.reason
