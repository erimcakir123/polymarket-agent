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


def test_ws_feed_fires_callback_with_bid():
    """_handle_book_event must pass best_bid to the registered callback."""
    from src.websocket_feed import WebSocketFeed

    captured: list[tuple] = []
    def cb(asset_id: str, yes_price: float, bid_price: float, ts: float) -> None:
        captured.append((asset_id, yes_price, bid_price, ts))

    feed = WebSocketFeed(on_price_update=cb)
    feed._subscriptions = {"asset-123"}  # Seed subscription so handler accepts

    feed._handle_book_event({
        "asset_id": "asset-123",
        "bids": [{"price": "0.01", "size": "100"}, {"price": "0.74", "size": "50"}],
        "asks": [{"price": "0.99", "size": "100"}, {"price": "0.75", "size": "50"}],
    })

    assert len(captured) == 1
    asset_id, yes_price, bid_price, _ts = captured[0]
    assert asset_id == "asset-123"
    assert yes_price == 0.75   # best_ask (asks[-1])
    assert bid_price == 0.74   # best_bid (bids[-1])


def test_ws_feed_price_change_callback_bid():
    """_handle_price_change_event must forward best_bid from price_changes[]."""
    from src.websocket_feed import WebSocketFeed

    captured: list[tuple] = []
    def cb(asset_id: str, yes_price: float, bid_price: float, ts: float) -> None:
        captured.append((asset_id, yes_price, bid_price, ts))

    feed = WebSocketFeed(on_price_update=cb)
    feed._subscriptions = {"asset-xyz"}

    feed._handle_price_change_event({
        "price_changes": [
            {"asset_id": "asset-xyz", "best_bid": "0.41", "best_ask": "0.42"},
        ],
    })

    assert len(captured) == 1
    assert captured[0][1] == 0.42  # yes_price = best_ask
    assert captured[0][2] == 0.41  # bid_price
