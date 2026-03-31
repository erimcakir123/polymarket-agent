"""Polymarket Sports WebSocket — real-time match state feed.

Connects to wss://sports-api.polymarket.com/ws and receives live match
updates for all active sports events. No subscription message needed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_WS_URL = "wss://sports-api.polymarket.com/ws"
_RECONNECT_BASE = 2.0
_RECONNECT_MAX = 60.0
_HEARTBEAT_INTERVAL = 5.0  # Server pings every 5s
_STALE_TIMEOUT = 30.0  # Consider state stale after 30s without update

# Date suffix pattern: -YYYY-MM-DD at end of slug
_DATE_SUFFIX_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")


class SportsWebSocket:
    """Real-time match state from Polymarket sports feed."""

    def __init__(self) -> None:
        self._states: dict[str, dict] = {}  # slug → match state
        self._lock = threading.Lock()
        self._running = False
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._reconnect_count = 0
        self._last_message_time = 0.0

    @property
    def connected(self) -> bool:
        return self._connected

    def start_background(self) -> None:
        """Start WebSocket feed in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Sports WebSocket already running")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ws-sports-feed",
        )
        self._thread.start()
        logger.info("Sports WebSocket started in background thread")

    def stop(self) -> None:
        """Stop the WebSocket feed."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("Sports WebSocket stopped")

    def get_match_state(self, slug: str) -> Optional[dict]:
        """Get latest match state by slug. Supports date-suffix matching."""
        with self._lock:
            # Exact match first
            if slug in self._states:
                return self._states[slug].copy()
            # Strip date suffix: "nba-cha-bkn-2026-03-30" → "nba-cha-bkn"
            base_slug = _DATE_SUFFIX_RE.sub("", slug)
            if base_slug != slug and base_slug in self._states:
                return self._states[base_slug].copy()
        return None

    def is_ended(self, slug: str) -> bool:
        """Check if match has ended."""
        state = self.get_match_state(slug)
        return bool(state and state.get("ended"))

    def is_live(self, slug: str) -> bool:
        """Check if match is currently live."""
        state = self.get_match_state(slug)
        return bool(state and state.get("live"))

    def _handle_message(self, raw: str) -> None:
        """Parse incoming WebSocket message and update state."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        slug = data.get("slug")
        if not slug:
            return

        with self._lock:
            self._states[slug] = {
                "game_id": data.get("gameId"),
                "league": data.get("leagueAbbreviation", ""),
                "home_team": data.get("homeTeam", ""),
                "away_team": data.get("awayTeam", ""),
                "status": data.get("status", ""),
                "score": data.get("score", ""),
                "period": data.get("period", ""),
                "live": bool(data.get("live", False)),
                "ended": bool(data.get("ended", False)),
                "elapsed": data.get("elapsed", ""),
                "finished_timestamp": data.get("finished_timestamp"),
                "updated_at": time.time(),
            }
        self._last_message_time = time.time()

    def _run_loop(self) -> None:
        """Run the asyncio event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as exc:
            logger.error("Sports WS loop crashed: %s", exc)
        finally:
            self._loop.close()

    async def _connect_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        import websockets

        delay = _RECONNECT_BASE
        while self._running:
            try:
                async with websockets.connect(
                    _WS_URL,
                    ping_interval=_HEARTBEAT_INTERVAL,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._connected = True
                    self._reconnect_count = 0
                    delay = _RECONNECT_BASE
                    logger.info("Sports WebSocket connected to %s", _WS_URL)

                    async for message in ws:
                        if not self._running:
                            break
                        self._handle_message(message)

            except Exception as exc:
                self._connected = False
                self._reconnect_count += 1
                logger.warning(
                    "Sports WS disconnected (attempt %d): %s — reconnecting in %.0fs",
                    self._reconnect_count, exc, delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _RECONNECT_MAX)
