"""PriceFeed WS reconnect + REST fallback regression testleri (FIX 6 — tennis bağlamı).

PriceFeed ana bot'tan miras alındı, tennis context'te ayrı test yapılmamıştı.
Bu suite reconnect davranışını + REST fallback'i mock'lu ortamda doğrular.
Asıl WS spawn etmez — _connect_loop'u doğrudan await ederek davranışı izole eder.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.websocket.price_feed import (
    RECONNECT_DELAY_BASE_SEC,
    RECONNECT_DELAY_MAX_SEC,
    PriceFeed,
)


# ── REST snapshot fallback ────────────────────────────────────────────────────


def test_price_feed_rest_fallback_fetches_book_on_reconnect() -> None:
    """Reconnect sonrası _fetch_rest_snapshots her token için REST /book çağırır.

    SPEC-I #3: disconnect süresince WS event kaçırdık → güncel snapshot için
    REST'i çek. Tennis'te de aynı davranış geçerli (price_feed shared).
    """
    feed = PriceFeed()
    feed.subscribe(["tennis-tok-1", "tennis-tok-2"])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "asks": [{"price": "0.55", "size": "10"}],
        "bids": [{"price": "0.53", "size": "10"}],
    }

    with patch("src.infrastructure.websocket.price_feed.requests.get",
               return_value=mock_response) as mock_get:
        feed._fetch_rest_snapshots(["tennis-tok-1", "tennis-tok-2"])

    # Her token için bir REST çağrı
    assert mock_get.call_count == 2
    # Cache'e fiyat yazıldı
    snap1 = feed.get_price("tennis-tok-1")
    snap2 = feed.get_price("tennis-tok-2")
    assert snap1 is not None and snap1.yes_price == 0.55
    assert snap2 is not None and snap2.yes_price == 0.55


def test_rest_fallback_404_invalidates_cache() -> None:
    """SPEC-M: REST /book 404 → market resolved/delisted → cache invalidate."""
    feed = PriceFeed()
    # Cache'e eski fiyat koy
    feed._update_price("tok-resolved", 0.50, 0.49)
    assert feed.get_price("tok-resolved") is not None

    mock_404 = MagicMock()
    mock_404.status_code = 404

    with patch("src.infrastructure.websocket.price_feed.requests.get",
               return_value=mock_404):
        feed._fetch_rest_snapshots(["tok-resolved"])

    # Cache temizlendi (sonraki get_price → None, exit rule fiyat bulamaz)
    assert feed.get_price("tok-resolved") is None


def test_rest_fallback_network_error_keeps_cache_intact() -> None:
    """REST çağrısı hata atarsa cache dokunulmaz (sonraki WS event'i bekler)."""
    import requests
    feed = PriceFeed()
    feed._update_price("tok-x", 0.40, 0.39)

    with patch("src.infrastructure.websocket.price_feed.requests.get",
               side_effect=requests.RequestException("net down")):
        feed._fetch_rest_snapshots(["tok-x"])

    # Cache değişmedi
    snap = feed.get_price("tok-x")
    assert snap is not None
    assert snap.yes_price == 0.40


# ── Reconnect loop with exponential backoff ───────────────────────────────────


def test_price_feed_reconnects_after_simulated_disconnect() -> None:
    """_connect_loop bağlantı hatasında bekler + tekrar dener (exponential backoff).

    Simulated: ilk iki _connect_and_listen ConnectionError atar, sonra
    feed._running = False yapılarak loop sonlandırılır. Reconnect sayacı +
    bekleme süresinin doğru artması doğrulanır.
    """
    feed = PriceFeed()
    feed._running = True

    call_count = {"n": 0}
    delays_recorded: list[float] = []

    async def fake_connect_and_listen() -> None:
        call_count["n"] += 1
        if call_count["n"] >= 3:
            # 3. denemede loop'tan çık (gerçek senaryoda bağlantı kurulur)
            feed._running = False
            return
        raise ConnectionError("simulated WS down")

    async def fake_sleep(sec: float) -> None:
        delays_recorded.append(sec)

    with (
        patch.object(feed, "_connect_and_listen", side_effect=fake_connect_and_listen),
        patch("src.infrastructure.websocket.price_feed.asyncio.sleep",
              side_effect=fake_sleep),
    ):
        asyncio.run(feed._connect_loop())

    # En az 2 reconnect denemesi (3. başarılı) + reconnect sayacı arttı
    assert call_count["n"] == 3
    assert feed.stats["reconnects"] >= 2
    assert feed.stats["errors"] >= 2
    # İlk delay = base, sonraki delay = base*2 (exponential)
    assert len(delays_recorded) >= 2
    assert delays_recorded[0] == RECONNECT_DELAY_BASE_SEC
    assert delays_recorded[1] == min(RECONNECT_DELAY_BASE_SEC * 2,
                                     RECONNECT_DELAY_MAX_SEC)


def test_reconnect_delay_caps_at_max() -> None:
    """Exponential backoff RECONNECT_DELAY_MAX_SEC'i geçmez."""
    feed = PriceFeed()
    feed._running = True
    delays: list[float] = []

    async def fake_connect_and_listen() -> None:
        if len(delays) >= 8:
            feed._running = False
            return
        raise ConnectionError("down")

    async def fake_sleep(sec: float) -> None:
        delays.append(sec)

    with (
        patch.object(feed, "_connect_and_listen", side_effect=fake_connect_and_listen),
        patch("src.infrastructure.websocket.price_feed.asyncio.sleep",
              side_effect=fake_sleep),
    ):
        asyncio.run(feed._connect_loop())

    # Son birkaç delay MAX'ta saturate olmalı
    assert delays[-1] == RECONNECT_DELAY_MAX_SEC
