"""WebSocket price feed for real-time CLOB price updates.

Replaces polling for positions that need fast reaction (stop-loss, take-profit,
re-entry triggers). Connects to Polymarket CLOB WebSocket and streams price
changes for subscribed token_ids.

Usage:
    feed = WebSocketFeed(on_price_update=my_callback)
    feed.subscribe(["token_id_1", "token_id_2"])
    await feed.start()  # runs forever, reconnects on failure
    feed.stop()

The callback receives: (token_id: str, yes_price: float, timestamp: float)
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# Reconnect settings
RECONNECT_DELAY_BASE = 2.0   # seconds
RECONNECT_DELAY_MAX = 60.0   # max backoff
HEARTBEAT_INTERVAL = 30.0    # ping every 30s
STALE_TIMEOUT = 120.0        # consider connection stale if no message in 2 min


class PriceSnapshot:
    """Latest price data for a token."""
    __slots__ = ("token_id", "yes_price", "timestamp", "bid", "ask")

    def __init__(self, token_id: str, yes_price: float, timestamp: float,
                 bid: float = 0.0, ask: float = 0.0) -> None:
        self.token_id = token_id
        self.yes_price = yes_price
        self.timestamp = timestamp
        self.bid = bid
        self.ask = ask


PriceCallback = Callable[[str, float, float], None]  # token_id, yes_price, timestamp


class WebSocketFeed:
    """Async WebSocket client for Polymarket CLOB price streaming."""

    def __init__(self, on_price_update: Optional[PriceCallback] = None) -> None:
        self._callback = on_price_update
        self._subscriptions: Set[str] = set()
        self._sub_lock = threading.Lock()  # Thread-safe subscription access
        self._prices: Dict[str, PriceSnapshot] = {}
        self._price_lock = threading.Lock()  # Thread-safe price dict access
        self._running = False
        self._connected = False
        self._ws = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._reconnect_count = 0
        self._last_message_time = 0.0
        self._stats = {"messages_received": 0, "reconnects": 0, "errors": 0}

    def set_on_price_update(self, callback) -> None:
        """Set or replace the price-update callback. Used by ExitMonitor. Must be called before start_background() -- not safe to call after the feed is running."""
        self._callback = callback

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def prices(self) -> Dict[str, PriceSnapshot]:
        with self._price_lock:
            return dict(self._prices)  # Return copy for thread safety

    @property
    def stats(self) -> dict:
        with self._sub_lock:
            sub_count = len(self._subscriptions)
        return {**self._stats, "subscriptions": sub_count,
                "connected": self._connected}

    def get_price(self, token_id: str) -> Optional[float]:
        """Get latest price for a token, or None if not available."""
        with self._price_lock:
            snap = self._prices.get(token_id)
        if snap and (time.time() - snap.timestamp) < STALE_TIMEOUT:
            return snap.yes_price
        return None

    def get_spread(self, token_id: str) -> Optional[dict]:
        """Get bid/ask spread for a token."""
        with self._price_lock:
            snap = self._prices.get(token_id)
        if snap and snap.bid > 0 and snap.ask > 0:
            return {"bid": snap.bid, "ask": snap.ask,
                    "spread": snap.ask - snap.bid, "mid": (snap.bid + snap.ask) / 2}
        return None

    def subscribe(self, token_ids: List[str]) -> None:
        """Add token_ids to subscription list. If connected, subscribes immediately."""
        with self._sub_lock:
            new_ids = set(token_ids) - self._subscriptions
            self._subscriptions.update(token_ids)
        if new_ids and self._ws and self._connected:
            asyncio.run_coroutine_threadsafe(
                self._subscribe_tokens(list(new_ids)), self._loop
            )

    def unsubscribe(self, token_ids: List[str]) -> None:
        """Remove token_ids from subscription list."""
        with self._sub_lock:
            for tid in token_ids:
                self._subscriptions.discard(tid)
        with self._price_lock:
            for tid in token_ids:
                self._prices.pop(tid, None)

    def start_background(self) -> None:
        """Start WebSocket feed in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("WebSocket feed already running")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True,
                                        name="ws-price-feed")
        self._thread.start()
        logger.info("WebSocket price feed started in background thread")

    def stop(self) -> None:
        """Stop the WebSocket feed."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
        self._connected = False
        logger.info("WebSocket price feed stopped")

    def _run_loop(self) -> None:
        """Run the async event loop in a thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            logger.error("WebSocket event loop error: %s", e)
        finally:
            self._loop.close()

    async def _connect_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        import websockets

        while self._running:
            delay = min(RECONNECT_DELAY_BASE * (2 ** self._reconnect_count),
                        RECONNECT_DELAY_MAX)
            try:
                async with websockets.connect(
                    CLOB_WS_URL,
                    ping_interval=HEARTBEAT_INTERVAL,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._connected = True
                    self._reconnect_count = 0
                    self._last_message_time = time.time()
                    with self._sub_lock:
                        sub_count = len(self._subscriptions)
                        sub_list = list(self._subscriptions) if self._subscriptions else []
                    logger.info("WebSocket connected to CLOB (%d subscriptions)", sub_count)

                    # Subscribe to all tracked tokens
                    if sub_list:
                        await self._subscribe_tokens(sub_list)

                    # Message loop
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        self._last_message_time = time.time()
                        self._stats["messages_received"] += 1
                        try:
                            self._handle_message(raw_msg)
                        except Exception as e:
                            logger.debug("WS message parse error: %s", e)
                            self._stats["errors"] += 1

            except Exception as e:
                self._stats["errors"] += 1
                self._stats["reconnects"] += 1
                self._reconnect_count += 1
                self._connected = False
                self._ws = None
                if self._running:
                    logger.warning("WebSocket disconnected: %s -- reconnecting in %.0fs",
                                   e, delay)
                    await asyncio.sleep(delay)

    async def _subscribe_tokens(self, token_ids: List[str]) -> None:
        """Send subscription messages for token_ids."""
        if not self._ws:
            return
        for tid in token_ids:
            try:
                msg = json.dumps({"type": "subscribe", "market": tid, "channel": "price"})
                await self._ws.send(msg)
            except Exception as e:
                logger.debug("Failed to subscribe %s: %s", tid[:16], e)

    def _handle_message(self, raw: str) -> None:
        """Parse and process a WebSocket message."""
        data = json.loads(raw)
        msg_type = data.get("type", "")

        if msg_type in ("price_change", "price"):
            token_id = data.get("market") or data.get("token_id") or data.get("asset_id", "")
            if not token_id:
                return
            with self._sub_lock:
                if token_id not in self._subscriptions:
                    return

            # Extract price -- format varies by message type
            price = data.get("price")
            if price is None:
                prices = data.get("prices", [])
                if prices:
                    price = float(prices[0])
            if price is None:
                return

            price = float(price)
            now = time.time()
            bid = float(data.get("bid", 0) or 0)
            ask = float(data.get("ask", 0) or 0)

            with self._price_lock:
                self._prices[token_id] = PriceSnapshot(token_id, price, now, bid, ask)

            # Fire callback (outside lock to avoid deadlock)
            if self._callback:
                try:
                    self._callback(token_id, price, now)
                except Exception as e:
                    logger.debug("Price callback error: %s", e)

        elif msg_type == "book":
            # Order book snapshot -- extract best bid/ask.
            # Polymarket format: asks DESC-sorted, bids ASC-sorted, so the
            # "best" level sits at [-1] for both sides. Reading [0] would
            # return market-maker sentinel orders (typically 0.99 / 0.01).
            token_id = data.get("market", "")
            if not token_id:
                return
            with self._sub_lock:
                if token_id not in self._subscriptions:
                    return
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            best_bid = float(bids[-1]["price"]) if bids else 0.0
            best_ask = float(asks[-1]["price"]) if asks else 0.0
            mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
            if mid > 0:
                with self._price_lock:
                    snap = self._prices.get(token_id)
                    if snap:
                        snap.bid = best_bid
                        snap.ask = best_ask
                    else:
                        self._prices[token_id] = PriceSnapshot(
                            token_id, mid, time.time(), best_bid, best_ask)

    def sync_subscriptions(self, active_token_ids: List[str]) -> None:
        """Sync subscriptions with currently active positions.

        Adds new token_ids and removes stale ones.
        """
        current = set(active_token_ids)
        with self._sub_lock:
            to_add = current - self._subscriptions
            to_remove = self._subscriptions - current

        if to_add:
            self.subscribe(list(to_add))
        if to_remove:
            self.unsubscribe(list(to_remove))
