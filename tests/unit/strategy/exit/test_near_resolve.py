"""near_resolve.check() birim testleri."""
from __future__ import annotations

import pytest
from src.strategy.exit.near_resolve import NearResolveResult, check


def test_check_returns_none_below_threshold() -> None:
    assert check(bid_price=0.93, threshold=0.94) is None


def test_check_returns_result_at_threshold() -> None:
    result = check(bid_price=0.94, threshold=0.94)
    assert result is not None
    assert result.sell_pct == 1.0


def test_check_returns_result_above_threshold() -> None:
    result = check(bid_price=0.95, threshold=0.94)
    assert result is not None
    assert result.sell_pct == 1.0
    assert "0.95" in result.reason


def test_check_default_threshold() -> None:
    # Default threshold is 0.94
    assert check(bid_price=0.93) is None
    assert check(bid_price=0.94) is not None


def test_check_custom_threshold() -> None:
    assert check(bid_price=0.89, threshold=0.90) is None
    assert check(bid_price=0.90, threshold=0.90) is not None


def test_result_reason_contains_prices() -> None:
    result = check(bid_price=0.96, threshold=0.94)
    assert result is not None
    assert "0.960" in result.reason or "0.96" in result.reason
