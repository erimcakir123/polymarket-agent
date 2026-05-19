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


# ── SPEC-I: Reliability fixes ──

def test_heartbeat_interval_is_10s_per_polymarket_protocol() -> None:
    """SPEC-I #1: Polymarket WS protokolü 10s ping ister (30s'de server silent close)."""
    from src.infrastructure.websocket.price_feed import HEARTBEAT_INTERVAL_SEC
    assert HEARTBEAT_INTERVAL_SEC == 10.0


def test_stale_timeout_is_60s_for_data_silence_watchdog() -> None:
    """SPEC-I #2: 60s data sessizliği → bağlantı dondu sayılır."""
    from src.infrastructure.websocket.price_feed import STALE_TIMEOUT_SEC
    assert STALE_TIMEOUT_SEC == 60.0


def test_fetch_book_snapshot_updates_cache_for_token() -> None:
    """SPEC-I #3: REST /book snapshot fetch → cache update doğru."""
    from unittest.mock import MagicMock, patch
    feed = PriceFeed()
    feed._subscriptions = {"token_x"}
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "asks": [{"price": "0.55", "size": "100"}, {"price": "0.50", "size": "100"}],  # DESC, best=last (0.50)
        "bids": [{"price": "0.45", "size": "100"}, {"price": "0.48", "size": "100"}],  # ASC, best=last (0.48)
    }
    with patch("src.infrastructure.websocket.price_feed.requests.get",
               return_value=fake_response) as mock_get:
        feed._fetch_rest_snapshots(["token_x"])
    assert mock_get.called
    snap = feed.get_price("token_x")
    assert snap is not None
    assert snap.yes_price == 0.50  # best ask (lowest)
    assert snap.bid_price == 0.48  # best bid (highest)


def test_fetch_book_snapshot_handles_http_error_gracefully() -> None:
    """SPEC-I #3 edge case: REST 404 / timeout → cache dokunulmaz, hata fırlatmaz."""
    from unittest.mock import MagicMock, patch
    feed = PriceFeed()
    fake_response = MagicMock()
    fake_response.status_code = 404
    with patch("src.infrastructure.websocket.price_feed.requests.get",
               return_value=fake_response):
        feed._fetch_rest_snapshots(["token_x"])  # Should not raise
    assert feed.get_price("token_x") is None


# ── SPEC-M (2026-05-19) — PriceFeed sanity layer ──


def test_update_price_rejects_spike_above_50pct() -> None:
    """SPEC-M: önceki fiyattan +50%'den fazla atlama → reject + stat artar."""
    feed = PriceFeed(max_spike_pct=0.50)
    # İlk fiyat: cache'e oturur (önceki yok)
    feed._update_price("tok", 0.50, 0.49)
    snap1 = feed.get_price("tok")
    assert snap1 is not None and snap1.yes_price == 0.50
    # Spike: 0.50 → 0.97 (+94%) — reject
    feed._update_price("tok", 0.97, 0.50)
    snap2 = feed.get_price("tok")
    assert snap2 is not None and snap2.yes_price == 0.50  # değişmedi
    assert feed.stats["spikes_rejected"] == 1


def test_update_price_accepts_normal_change_below_50pct() -> None:
    """SPEC-M: normal değişimler kabul edilmeli (yanlış pozitif yok)."""
    feed = PriceFeed(max_spike_pct=0.50)
    feed._update_price("tok", 0.60, 0.59)
    feed._update_price("tok", 0.75, 0.74)  # +25% — kabul
    snap = feed.get_price("tok")
    assert snap is not None and snap.yes_price == 0.75
    assert feed.stats["spikes_rejected"] == 0


def test_fetch_rest_snapshots_404_invalidates_existing_cache() -> None:
    """SPEC-M: 404 dönerse cache'deki eski fiyat SİLİNMELİ."""
    from unittest.mock import MagicMock, patch
    feed = PriceFeed()
    # Önce cache'e fiyat koy
    feed._update_price("tok_x", 0.61, 0.60)
    assert feed.get_price("tok_x") is not None
    # REST 404 simüle et
    fake_response = MagicMock()
    fake_response.status_code = 404
    with patch("src.infrastructure.websocket.price_feed.requests.get",
               return_value=fake_response):
        feed._fetch_rest_snapshots(["tok_x"])
    # Cache temizlenmeli
    assert feed.get_price("tok_x") is None


def test_best_ask_works_regardless_of_sort_order() -> None:
    """SPEC-M: min() defensive — sort DESC veya ASC olsa da en düşük ask döner."""
    desc = [{"price": "0.97"}, {"price": "0.85"}, {"price": "0.60"}]
    asc = [{"price": "0.60"}, {"price": "0.85"}, {"price": "0.97"}]
    assert _best_ask_from_snapshot(desc) == 0.60
    assert _best_ask_from_snapshot(asc) == 0.60


def test_best_bid_works_regardless_of_sort_order() -> None:
    """SPEC-M: max() defensive — sort DESC veya ASC olsa da en yüksek bid döner."""
    desc = [{"price": "0.60"}, {"price": "0.45"}, {"price": "0.20"}]
    asc = [{"price": "0.20"}, {"price": "0.45"}, {"price": "0.60"}]
    assert _best_bid_from_snapshot(desc) == 0.60
    assert _best_bid_from_snapshot(asc) == 0.60
