"""Polymarket CLOB Market Channel WebSocket istemcisi (DECISIONS §8).

Anlık fiyat beslemesi — pozisyonlar için stop-loss / scale-out / near-resolve
reaksiyon. Background thread'de asyncio event loop çalışır; callback main thread'e
token_id + yes_price + bid_price + timestamp gönderir.

Protokol: https://docs.polymarket.com/api-reference/wss/market
  Subscribe: {"assets_ids": [...], "type": "market"}
  Events (event_type field):
    - book          (initial orderbook snapshot: asks DESC, bids ASC)
    - price_change  (price_changes[] with asset_id, price, size, side, best_bid, best_ask)
    - best_bid_ask  (asset_id, best_bid, best_ask)
    - last_trade_price

Polymarket orderbook non-standard sort:
  asks DESC → best ask = asks[-1].price (lowest)
  bids ASC  → best bid = bids[-1].price (highest)
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

import requests
import websockets

logger = logging.getLogger(__name__)

CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
CLOB_REST_BOOK_URL = "https://clob.polymarket.com/book"

RECONNECT_DELAY_BASE_SEC = 2.0
RECONNECT_DELAY_MAX_SEC = 60.0
# SPEC-I: Polymarket WS protokolu 10s ping ister (30s'de server silent close yapar).
HEARTBEAT_INTERVAL_SEC = 10.0
# SPEC-I: 60s data sessizligi → baglanti dondu sayilir, watchdog reconnect tetikler.
STALE_TIMEOUT_SEC = 60.0
WATCHDOG_CHECK_INTERVAL_SEC = 30.0
REST_BOOK_TIMEOUT_SEC = 5.0


@dataclass
class PriceSnapshot:
    token_id: str
    yes_price: float   # best-ask (BUY ederken ödeyeceğimiz)
    bid_price: float   # best-bid (SELL edersek alacağımız)
    timestamp: float   # UNIX epoch


PriceCallback = Callable[[str, float, float, float], None]
# (token_id, yes_price, bid_price, timestamp)


def _best_ask_from_snapshot(asks: list) -> float:
    """Best ask = LOWEST price (sort-agnostic).

    SPEC-M (2026-05-19): Eski kod `asks[-1]` ile DESC sort varsayıyordu —
    ASC dönerse HIGHEST ask döndürüyordu (sahte en kötü fiyat). min() defensive.
    """
    if not asks:
        return 0.0
    prices = []
    for a in asks:
        try:
            p = float(a.get("price", 0))
            if p > 0:
                prices.append(p)
        except (TypeError, ValueError, KeyError):
            continue
    return min(prices) if prices else 0.0


def _best_bid_from_snapshot(bids: list) -> float:
    """Best bid = HIGHEST price (sort-agnostic). SPEC-M defensive."""
    if not bids:
        return 0.0
    prices = []
    for b in bids:
        try:
            p = float(b.get("price", 0))
            if p > 0:
                prices.append(p)
        except (TypeError, ValueError, KeyError):
            continue
    return max(prices) if prices else 0.0


class PriceFeed:
    """CLOB WS price feed. Background thread + async loop. Reconnect dahil."""

    def __init__(
        self,
        on_price_update: PriceCallback | None = None,
        max_spike_pct: float = 0.50,
        max_spike_corroboration_spread: float = 0.10,
    ) -> None:
        self._callback = on_price_update
        # SPEC-M: tek tick'te bu yüzdeden fazla fiyat atlama → reject (KBO bug 2026-05-19)
        self._max_spike_pct = max_spike_pct
        # 2026-06-08: sıçrama iki-taraflı kotayla teyit edilirse kabul (gerçek çöküş donmaz)
        self._max_spike_corroboration_spread = max_spike_corroboration_spread
        self._subscriptions: set[str] = set()
        self._sub_lock = threading.Lock()
        self._prices: dict[str, PriceSnapshot] = {}
        self._price_lock = threading.Lock()
        self._running = False
        self._connected = False
        self._ws = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._last_message_ts = 0.0
        self.stats = {"messages_received": 0, "reconnects": 0, "errors": 0, "spikes_rejected": 0}

    # ── Public API ──

    @property
    def connected(self) -> bool:
        return self._connected

    def set_callback(self, cb: PriceCallback) -> None:
        """Callback'i değiştir (feed başlamadan önce çağrılmalı)."""
        self._callback = cb

    def subscribe(self, token_ids: list[str]) -> None:
        """Yeni token'lara abone ol (running'ken de çalışır)."""
        with self._sub_lock:
            new = set(token_ids) - self._subscriptions
            self._subscriptions.update(token_ids)
        if new and self._connected and self._loop:
            asyncio.run_coroutine_threadsafe(self._send_subscribe(list(new)), self._loop)

    def unsubscribe(self, token_ids: list[str]) -> None:
        with self._sub_lock:
            self._subscriptions.difference_update(token_ids)
        # Polymarket WS "unsubscribe" mesajını desteklemiyor — sadece lokal state temizler

    def get_price(self, token_id: str) -> PriceSnapshot | None:
        with self._price_lock:
            return self._prices.get(token_id)

    def start_background(self) -> None:
        """Arka plan thread başlat — sürekli dinle + yeniden bağlan."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Background thread'i kapat."""
        self._running = False
        if self._loop and self._ws:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

    # ── Internals ──

    def _run_forever(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            logger.error("PriceFeed thread crashed: %s", e)
        finally:
            self._loop.close()

    async def _connect_loop(self) -> None:
        delay = RECONNECT_DELAY_BASE_SEC
        while self._running:
            try:
                await self._connect_and_listen()
                delay = RECONNECT_DELAY_BASE_SEC  # Başarılı bağlantı sonrası reset
            except Exception as e:
                self.stats["errors"] += 1
                logger.warning("PriceFeed connection error: %s — reconnecting in %.0fs", e, delay)
                self._connected = False
                self.stats["reconnects"] += 1
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX_SEC)

    async def _connect_and_listen(self) -> None:
        async with websockets.connect(
            CLOB_WS_URL,
            ping_interval=HEARTBEAT_INTERVAL_SEC,
            ping_timeout=HEARTBEAT_INTERVAL_SEC,
        ) as ws:
            self._ws = ws
            self._connected = True
            self._last_message_ts = time.time()
            with self._sub_lock:
                tokens = list(self._subscriptions)
            if tokens:
                # SPEC-I #3: Reconnect sonrasi REST snapshot fetch — disconnect
                # suresince kacan fiyatlari yakala, eski cache ile karar verme.
                self._fetch_rest_snapshots(tokens)
                await self._send_subscribe(tokens)
            # SPEC-I #2: Stale watchdog — 60s data sessizliginde force reconnect
            watchdog_task = asyncio.create_task(self._stale_watchdog(ws))
            try:
                async for msg in ws:
                    self._last_message_ts = time.time()
                    self.stats["messages_received"] += 1
                    self._handle_message(msg)
            finally:
                watchdog_task.cancel()

    async def _stale_watchdog(self, ws) -> None:
        """SPEC-I #2: STALE_TIMEOUT_SEC kadar mesaj gelmezse baglantiyi kapat.

        WS handle acik gozukse de Polymarket bazen sessizce data akisini durdurur
        (GitHub Issue #26 bilinen sorun). Bu watchdog donmayi yakalar, _connect_loop
        reconnect'i tetikler.
        """
        try:
            while True:
                await asyncio.sleep(WATCHDOG_CHECK_INTERVAL_SEC)
                idle = time.time() - self._last_message_ts
                if idle > STALE_TIMEOUT_SEC:
                    logger.warning(
                        "PriceFeed stale (%.0fs no data) — force reconnect", idle,
                    )
                    await ws.close()
                    return
        except asyncio.CancelledError:
            return

    def _fetch_rest_snapshots(self, tokens: list[str]) -> None:
        """SPEC-I #3: REST /book?token_id=... ile guncel snapshot cek + cache update.

        Disconnect surecinde kacan fiyatlari yakalar. Hata olursa o token icin
        cache dokunulmaz (sonraki WS event'i bekler).
        """
        for tid in tokens:
            try:
                resp = requests.get(
                    CLOB_REST_BOOK_URL,
                    params={"token_id": tid},
                    timeout=REST_BOOK_TIMEOUT_SEC,
                )
                if resp.status_code == 404:
                    # SPEC-M (2026-05-19): Market resolved/delisted → cache invalidate.
                    # Eski davranış: cache'e dokunmuyordu → eski fiyat kalıp sonraki
                    # WS spike'ında bot karar veriyordu (KBO bug). Şimdi sil → bot
                    # fiyat bulamayınca exit kararı vermez (zaten get_price()=None handle var).
                    with self._price_lock:
                        self._prices.pop(tid, None)
                    logger.warning("REST /book %s: 404 — cache invalidated", tid[:16])
                    continue
                if resp.status_code != 200:
                    logger.warning("REST /book %s returned %d", tid[:16], resp.status_code)
                    continue
                data = resp.json()
                asks = data.get("asks", []) or []
                bids = data.get("bids", []) or []
                ask = _best_ask_from_snapshot(asks)
                bid = _best_bid_from_snapshot(bids)
                if ask > 0:
                    self._update_price(tid, ask, bid)
            except (requests.RequestException, ValueError) as e:
                logger.warning("REST /book %s fetch failed: %s", tid[:16], e)
                continue

    async def _send_subscribe(self, tokens: list[str]) -> None:
        if not self._ws:
            return
        payload = {"assets_ids": tokens, "type": "market"}
        await self._ws.send(json.dumps(payload))

    def _handle_message(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(data, list):
            for item in data:
                self._dispatch_event(item)
        elif isinstance(data, dict):
            self._dispatch_event(data)

    def _dispatch_event(self, evt: dict) -> None:
        et = evt.get("event_type", "")
        token_id = evt.get("asset_id", "")
        if et == "book":
            asks = evt.get("asks", []) or []
            bids = evt.get("bids", []) or []
            yes_price = _best_ask_from_snapshot(asks)
            bid_price = _best_bid_from_snapshot(bids)
            self._update_price(token_id, yes_price, bid_price)
        elif et == "price_change":
            for change in evt.get("price_changes", []) or []:
                tid = change.get("asset_id", token_id)
                try:
                    ask = float(change.get("best_ask", 0)) or 0.0
                    bid = float(change.get("best_bid", 0)) or 0.0
                except (TypeError, ValueError):
                    continue
                if ask > 0:
                    self._update_price(tid, ask, bid)
        elif et == "best_bid_ask":
            try:
                ask = float(evt.get("best_ask", 0)) or 0.0
                bid = float(evt.get("best_bid", 0)) or 0.0
            except (TypeError, ValueError):
                return
            if token_id and ask > 0:
                self._update_price(token_id, ask, bid)
        # last_trade_price, tick_size_change, new_market, market_resolved — ignored (v2 MVP)

    def _update_price(self, token_id: str, yes_price: float, bid_price: float) -> None:
        if not token_id or yes_price <= 0:
            return
        # SPEC-M (2026-05-19): spike rejection.
        # Önceki fiyattan |Δ| > max_spike_pct atlama → suspicious, reject + log.
        # KBO bug: bot uyku → cache stale → WS sahte spike $0.97 (entry $0.61)
        # tetikledi. Bu guard $0.61 → $0.97 (+59%) gibi atlamayı engeller.
        with self._price_lock:
            prev = self._prices.get(token_id)
        if prev is not None and prev.yes_price > 0:
            pct_change = abs(yes_price - prev.yes_price) / prev.yes_price
            if pct_change > self._max_spike_pct:
                # Gerçek çöküş mü, bayat tek-taraflı baskı mı? İki-taraflı kota
                # tutarlıysa (ask-bid dar) piyasa gerçekten oraya gitmiş → kabul.
                corroborated = (
                    bid_price > 0
                    and (yes_price - bid_price) <= self._max_spike_corroboration_spread
                )
                if not corroborated:
                    self.stats["spikes_rejected"] += 1
                    logger.warning(
                        "price_feed: spike reject %s: %.3f -> %.3f (%.0f%% change > %.0f%% limit, bid=%.3f)",
                        token_id[:16], prev.yes_price, yes_price,
                        pct_change * 100, self._max_spike_pct * 100, bid_price,
                    )
                    return
        snap = PriceSnapshot(
            token_id=token_id, yes_price=yes_price,
            bid_price=bid_price, timestamp=time.time(),
        )
        with self._price_lock:
            self._prices[token_id] = snap
        if self._callback:
            try:
                self._callback(token_id, yes_price, bid_price, snap.timestamp)
            except Exception as e:
                logger.error("PriceFeed callback error: %s", e)
