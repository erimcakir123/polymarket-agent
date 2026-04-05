"""WebSocket price feed for real-time CLOB price updates.

Replaces polling for positions that need fast reaction (stop-loss, take-profit,
re-entry triggers). Connects to Polymarket CLOB Market Channel and streams
book snapshots, price changes, and best-bid/ask updates.

Polymarket Market Channel protocol
(https://docs.polymarket.com/api-reference/wss/market):

  Subscribe:
    {"assets_ids": ["123...", "456..."], "type": "market"}

  Server events (all have `event_type` field, not `type`):
    - "book"           initial orderbook snapshot (asks DESC, bids ASC)
    - "price_change"   incremental level change, contains price_changes[]
                       each with asset_id, price, size, side, best_bid, best_ask
    - "best_bid_ask"   top-of-book only, has asset_id, best_bid, best_ask
    - "last_trade_price"  executed trade at asset_id/price
    - "tick_size_change"
    - "new_market" / "market_resolved"

  All events use `asset_id` to identify the token (not `market` — that's the
  condition_id at event level, not what we're tracking per token).

Usage:
    feed = WebSocketFeed(on_price_update=my_callback)
    feed.subscribe(["token_id_1", "token_id_2"])
    feed.start_background()  # runs forever, reconnects on failure
    feed.stop()

The callback receives: (token_id: str, yes_price: float, timestamp: float)
where yes_price is the best-ask (the price we'd pay to BUY at that moment).
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
        """Stop the WebSocket feed gracefully.

        Signals the connect loop and pinger to exit, closes the socket, then
        joins the background thread. Avoids "event loop stopped before Future"
        warnings by letting the loop finish cleanly rather than hard-stopping.
        """
        self._running = False
        if self._loop and self._loop.is_running() and self._ws is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
            except Exception:
                pass
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
                # Polymarket recommends disabling library-level ping and using
                # application-level `{}` keepalive pings instead.
                async with websockets.connect(
                    CLOB_WS_URL,
                    ping_interval=None,
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

                    # Launch keepalive pinger as a background task
                    ping_task = asyncio.create_task(self._keepalive_pinger(ws))

                    try:
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
                    finally:
                        ping_task.cancel()
                        try:
                            await ping_task
                        except (asyncio.CancelledError, Exception):
                            pass

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

    async def _keepalive_pinger(self, ws) -> None:
        """Send application-level `{}` ping every HEARTBEAT_INTERVAL seconds.

        Polymarket's Market Channel uses a simple `{}` → `{}` keepalive.
        Library-level pings are disabled (ping_interval=None).
        """
        try:
            while self._running:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    await ws.send("{}")
                except Exception:
                    return
        except asyncio.CancelledError:
            return

    async def _subscribe_tokens(self, token_ids: List[str]) -> None:
        """Send subscription message for token_ids (Market Channel protocol).

        Polymarket accepts a single subscription frame listing all asset_ids:
            {"assets_ids": [...], "type": "market"}
        """
        if not self._ws or not token_ids:
            return
        try:
            msg = json.dumps({"assets_ids": list(token_ids), "type": "market"})
            await self._ws.send(msg)
            logger.info("WS subscribed to %d asset(s)", len(token_ids))
        except Exception as e:
            logger.warning("Failed to subscribe %d tokens: %s", len(token_ids), e)

    def _handle_message(self, raw: str) -> None:
        """Parse and process a Polymarket Market Channel WebSocket message.

        Polymarket events carry an `event_type` field (NOT `type`) and
        identify the token via `asset_id`. The server may send an array of
        events in a single frame, or a single event object.
        """
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return

        # Server may send a list of events in one frame
        events = parsed if isinstance(parsed, list) else [parsed]
        for data in events:
            if not isinstance(data, dict):
                continue
            event_type = data.get("event_type", "")
            if event_type == "book":
                self._handle_book_event(data)
            elif event_type == "price_change":
                self._handle_price_change_event(data)
            elif event_type == "best_bid_ask":
                self._handle_best_bid_ask_event(data)
            elif event_type == "last_trade_price":
                self._handle_last_trade_event(data)
            # Ignore tick_size_change / new_market / market_resolved for now

    def _handle_book_event(self, data: dict) -> None:
        """Handle an orderbook snapshot event.

        Polymarket format: asks DESC-sorted, bids ASC-sorted, so the best
        level sits at [-1] for both sides. Index [0] holds market-maker
        sentinel orders (typically 0.99 / 0.01) which must NOT be read.
        """
        asset_id = data.get("asset_id", "")
        if not asset_id:
            return
        with self._sub_lock:
            if asset_id not in self._subscriptions:
                return
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        try:
            best_bid = float(bids[-1]["price"]) if bids else 0.0
            best_ask = float(asks[-1]["price"]) if asks else 0.0
        except (TypeError, ValueError, KeyError, IndexError):
            return
        if best_ask <= 0:
            return
        # Use best-ask as the "fill" price (what we'd pay to BUY right now)
        yes_price = best_ask
        now = time.time()
        with self._price_lock:
            self._prices[asset_id] = PriceSnapshot(
                asset_id, yes_price, now, best_bid, best_ask
            )
        self._fire_callback(asset_id, yes_price, now)

    def _handle_price_change_event(self, data: dict) -> None:
        """Handle an incremental price_change event.

        Contains `price_changes` array; each entry has asset_id, price, size,
        side, best_bid, best_ask. We update whichever assets are subscribed.
        """
        changes = data.get("price_changes", [])
        if not isinstance(changes, list):
            return
        now = time.time()
        for change in changes:
            if not isinstance(change, dict):
                continue
            asset_id = change.get("asset_id", "")
            if not asset_id:
                continue
            with self._sub_lock:
                if asset_id not in self._subscriptions:
                    continue
            try:
                best_bid = float(change.get("best_bid", 0) or 0)
                best_ask = float(change.get("best_ask", 0) or 0)
            except (TypeError, ValueError):
                continue
            if best_ask <= 0:
                continue
            yes_price = best_ask
            with self._price_lock:
                self._prices[asset_id] = PriceSnapshot(
                    asset_id, yes_price, now, best_bid, best_ask
                )
            self._fire_callback(asset_id, yes_price, now)

    def _handle_best_bid_ask_event(self, data: dict) -> None:
        """Handle a top-of-book update (fastest price signal)."""
        asset_id = data.get("asset_id", "")
        if not asset_id:
            return
        with self._sub_lock:
            if asset_id not in self._subscriptions:
                return
        try:
            best_bid = float(data.get("best_bid", 0) or 0)
            best_ask = float(data.get("best_ask", 0) or 0)
        except (TypeError, ValueError):
            return
        if best_ask <= 0:
            return
        yes_price = best_ask
        now = time.time()
        with self._price_lock:
            self._prices[asset_id] = PriceSnapshot(
                asset_id, yes_price, now, best_bid, best_ask
            )
        self._fire_callback(asset_id, yes_price, now)

    def _handle_last_trade_event(self, data: dict) -> None:
        """Handle a trade execution — useful as a liveness signal (price may
        differ from mid, so we only update yes_price if no book snapshot has
        been stored yet)."""
        asset_id = data.get("asset_id", "")
        if not asset_id:
            return
        with self._sub_lock:
            if asset_id not in self._subscriptions:
                return
        try:
            price = float(data.get("price", 0) or 0)
        except (TypeError, ValueError):
            return
        if price <= 0:
            return
        now = time.time()
        with self._price_lock:
            existing = self._prices.get(asset_id)
            if existing is None:
                # No book snapshot yet — seed with trade price
                self._prices[asset_id] = PriceSnapshot(asset_id, price, now, 0.0, 0.0)
            else:
                existing.timestamp = now  # keep connection fresh

    def _fire_callback(self, asset_id: str, yes_price: float, ts: float) -> None:
        """Invoke the registered price callback outside any lock."""
        if self._callback:
            try:
                self._callback(asset_id, yes_price, ts)
            except Exception as e:
                logger.debug("Price callback error: %s", e)

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
