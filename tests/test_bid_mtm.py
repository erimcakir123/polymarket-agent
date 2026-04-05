"""Tests for bid-side mark-to-market display fix.

Ensures:
  1. Position exposes a new `bid_price` field that defaults to 0.0.
  2. Legacy positions.json (missing the field) round-trip correctly.
  3. The existing unrealized_pnl_* properties keep using current_price.
"""
from __future__ import annotations

from src.models import Position


def _make_pos(**overrides) -> Position:
    defaults = dict(
        condition_id="0xabc",
        token_id="1",
        direction="BUY_YES",
        entry_price=0.50,
        size_usdc=100.0,
        shares=200.0,
        current_price=0.50,
        ai_probability=0.55,
    )
    defaults.update(overrides)
    return Position(**defaults)


def test_bid_price_defaults_to_zero():
    pos = _make_pos()
    assert hasattr(pos, "bid_price")
    assert pos.bid_price == 0.0


def test_legacy_position_roundtrip_missing_bid():
    """A dict saved before this field existed must still load cleanly."""
    legacy = {
        "condition_id": "0xabc",
        "token_id": "1",
        "direction": "BUY_YES",
        "entry_price": 0.50,
        "size_usdc": 100.0,
        "shares": 200.0,
        "current_price": 0.50,
        "ai_probability": 0.55,
    }
    pos = Position.model_validate(legacy)
    assert pos.bid_price == 0.0


def test_unrealized_pnl_uses_current_price_not_bid():
    """bid_price must NOT leak into exit-facing unrealized_pnl_usdc."""
    pos = _make_pos(current_price=0.60, bid_price=0.40)
    # current_price=0.60 → current_value = 200 * 0.60 = 120 → PnL = +20
    assert round(pos.unrealized_pnl_usdc, 4) == 20.0
