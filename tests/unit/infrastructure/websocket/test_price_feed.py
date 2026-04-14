"""price_feed.py için birim testler — event dispatch + orderbook parsing (pure).

Async connect loop test edilmez (integration'a düşer). Sadece:
  - _handle_message / _dispatch_event event parsing
  - _best_ask/_best_bid helper'ları
  - subscribe/unsubscribe state
  - callback tetikleme
"""
from __future__ import annotations

import json

from src.infrastructure.websocket.price_feed import (
    PriceFeed,
    _best_ask_from_snapshot,
    _best_bid_from_snapshot,
)


def test_best_ask_desc_sort_uses_last() -> None:
    asks = [{"price": "0.99", "size": "10"}, {"price": "0.48", "size": "5"}]
    assert _best_ask_from_snapshot(asks) == 0.48


def test_best_bid_asc_sort_uses_last() -> None:
    bids = [{"price": "0.01", "size": "10"}, {"price": "0.46", "size": "5"}]
    assert _best_bid_from_snapshot(bids) == 0.46


def test_empty_book_returns_zero() -> None:
    assert _best_ask_from_snapshot([]) == 0.0
    assert _best_bid_from_snapshot([]) == 0.0


def test_subscribe_stores_tokens() -> None:
    feed = PriceFeed()
    feed.subscribe(["tok1", "tok2"])
    assert feed._subscriptions == {"tok1", "tok2"}


def test_unsubscribe_removes() -> None:
    feed = PriceFeed()
    feed.subscribe(["tok1", "tok2", "tok3"])
    feed.unsubscribe(["tok2"])
    assert feed._subscriptions == {"tok1", "tok3"}


def test_book_event_updates_price_and_calls_callback() -> None:
    events: list[tuple] = []
    feed = PriceFeed(on_price_update=lambda t, ask, bid, ts: events.append((t, ask, bid)))
    evt = {
        "event_type": "book",
        "asset_id": "tok1",
        "asks": [{"price": "0.99", "size": "10"}, {"price": "0.48", "size": "5"}],
        "bids": [{"price": "0.01", "size": "10"}, {"price": "0.46", "size": "5"}],
    }
    feed._dispatch_event(evt)
    assert len(events) == 1
    tok, ask, bid = events[0]
    assert tok == "tok1"
    assert ask == 0.48
    assert bid == 0.46
    # get_price döner
    snap = feed.get_price("tok1")
    assert snap is not None
    assert snap.yes_price == 0.48


def test_price_change_event() -> None:
    events: list[tuple] = []
    feed = PriceFeed(on_price_update=lambda t, ask, bid, ts: events.append((t, ask, bid)))
    evt = {
        "event_type": "price_change",
        "price_changes": [
            {"asset_id": "tok1", "best_ask": "0.50", "best_bid": "0.49", "side": "BUY", "price": "0.50", "size": "100"},
        ],
    }
    feed._dispatch_event(evt)
    assert len(events) == 1
    assert events[0] == ("tok1", 0.50, 0.49)


def test_best_bid_ask_event() -> None:
    events: list[tuple] = []
    feed = PriceFeed(on_price_update=lambda t, ask, bid, ts: events.append((t, ask, bid)))
    evt = {
        "event_type": "best_bid_ask",
        "asset_id": "tok2",
        "best_ask": "0.62",
        "best_bid": "0.60",
    }
    feed._dispatch_event(evt)
    assert events == [("tok2", 0.62, 0.60)]


def test_unknown_event_type_ignored() -> None:
    events: list[tuple] = []
    feed = PriceFeed(on_price_update=lambda t, a, b, ts: events.append((t, a, b)))
    feed._dispatch_event({"event_type": "last_trade_price", "asset_id": "x", "price": "0.5"})
    feed._dispatch_event({"event_type": "new_market"})
    assert events == []


def test_json_list_message_dispatches_each() -> None:
    events: list[tuple] = []
    feed = PriceFeed(on_price_update=lambda t, a, b, ts: events.append((t, a, b)))
    raw = json.dumps([
        {"event_type": "best_bid_ask", "asset_id": "a", "best_ask": "0.5", "best_bid": "0.49"},
        {"event_type": "best_bid_ask", "asset_id": "b", "best_ask": "0.3", "best_bid": "0.29"},
    ])
    feed._handle_message(raw)
    assert len(events) == 2


def test_invalid_json_silently_ignored() -> None:
    feed = PriceFeed(on_price_update=lambda *a: None)
    # Exception atmamalı
    feed._handle_message("not valid json {")


def test_zero_price_update_ignored() -> None:
    events: list[tuple] = []
    feed = PriceFeed(on_price_update=lambda t, a, b, ts: events.append((t, a, b)))
    evt = {"event_type": "best_bid_ask", "asset_id": "tok", "best_ask": "0", "best_bid": "0"}
    feed._dispatch_event(evt)
    assert events == []


def test_callback_exception_does_not_crash() -> None:
    def bad_cb(*args):
        raise RuntimeError("callback failed")
    feed = PriceFeed(on_price_update=bad_cb)
    evt = {"event_type": "best_bid_ask", "asset_id": "x", "best_ask": "0.5", "best_bid": "0.49"}
    # Dispatch should not raise
    feed._dispatch_event(evt)
