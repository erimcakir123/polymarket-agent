"""The Odds API istemcisi — ham HTTP + cache + quota tracking (TDD §8).

Sadece ham veri döner; parsing ve matching strategy/enrichment katmanında yapılır.
20K kredi/ay bütçe; adaptive refresh (70%/90% kullanımda yavaşla).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
_DEFAULT_TIMEOUT = 10
# Adaptive refresh window (saniye)
_ACTIVE_SPORTS_CACHE_TTL = 3600   # /sports 1h cache
_BASE_REFRESH_SEC = 2 * 3600      # /odds 2h (default)
_SLOW_REFRESH_SEC = 3 * 3600      # ≥70% quota kullanıldığında
_EMERGENCY_REFRESH_SEC = 4 * 3600 # ≥90% quota kullanıldığında


def _default_http_get(url: str, params: dict, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params, timeout=timeout)


class OddsAPIClient:
    """The Odds API ham istemci — GET ve JSON döner, parsing yok."""

    def __init__(
        self,
        api_key: str = "",
        http_get: Callable[..., Any] = _default_http_get,
    ) -> None:
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self._backup_key = os.getenv("ODDS_API_KEY_BACKUP", "")
        self._using_backup = False
        self._http = http_get
        self._cache: dict[str, tuple[Any, float]] = {}  # cache_key → (data, ts)
        self._last_used: int | None = None
        self._last_remaining: int | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    # ── Public API (ham veri döner) ──

    def get_sports(self, include_inactive: bool = False) -> list[dict] | None:
        """/v4/sports — aktif sport listesi. FREE (0 credit)."""
        params = {"all": "true" if include_inactive else "false"}
        return self._cached_get("/sports", params, ttl=_ACTIVE_SPORTS_CACHE_TTL)

    def get_events(self, sport_key: str) -> list[dict] | None:
        """/v4/sports/{key}/events — sport_key için event listesi. FREE."""
        return self._cached_get(f"/sports/{sport_key}/events", {}, ttl=_BASE_REFRESH_SEC)

    def get_odds(self, sport_key: str, params: dict | None = None) -> list[dict] | None:
        """/v4/sports/{key}/odds — event + bookmaker odds listesi. Costly (~1 credit)."""
        merged = dict(params or {})
        return self._cached_get(f"/sports/{sport_key}/odds", merged, ttl=self._current_refresh_sec())

    def get_scores(self, sport_key: str, days_from: int = 1) -> list[dict] | None:
        """/v4/sports/{key}/scores — canlı skorlar. ~0.3 credit."""
        params = {"daysFrom": str(days_from)}
        return self._cached_get(f"/sports/{sport_key}/scores", params, ttl=90)

    # ── HTTP + cache ──

    def _cached_get(self, endpoint: str, params: dict, ttl: int) -> Any:
        if not self.available:
            return None
        cache_key = f"{endpoint}:{sorted(params.items())}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            data, ts = cached
            if (time.time() - ts) < ttl:
                return data
        data = self._api_request(endpoint, params)
        if data is not None:
            self._cache[cache_key] = (data, time.time())
        return data

    def _api_request(self, endpoint: str, params: dict) -> Any:
        if not self.api_key:
            return None
        params_with_key = {**params, "apiKey": self.api_key}
        try:
            resp = self._http(f"{ODDS_API_BASE}{endpoint}", params=params_with_key, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            # Quota header'ları
            self._update_quota(
                resp.headers.get("x-requests-used", ""),
                resp.headers.get("x-requests-remaining", ""),
            )
            return resp.json()
        except Exception as e:
            logger.warning("Odds API error %s: %s", endpoint, e)
            if self._is_auth_error(e):
                return self._try_backup(endpoint, params)
            return None

    def _is_auth_error(self, e: Exception) -> bool:
        s = str(e)
        return "401" in s or "429" in s

    def _try_backup(self, endpoint: str, params: dict) -> Any:
        if not self._using_backup and self._backup_key:
            logger.warning("Odds API primary exhausted → switching to backup")
            self.api_key = self._backup_key
            self._using_backup = True
            return self._api_request(endpoint, params)
        logger.warning("Odds API auth failed — disabling key for session")
        self.api_key = ""
        return None

    def _update_quota(self, used_hdr: str, remaining_hdr: str) -> None:
        try:
            self._last_used = int(used_hdr)
        except (ValueError, TypeError):
            pass
        try:
            self._last_remaining = int(remaining_hdr)
        except (ValueError, TypeError):
            pass

    def _current_refresh_sec(self) -> int:
        """Kota kullanımına göre adaptive refresh interval."""
        if self._last_used is None or self._last_remaining is None:
            return _BASE_REFRESH_SEC
        total = self._last_used + self._last_remaining
        if total <= 0:
            return _BASE_REFRESH_SEC
        usage = self._last_used / total
        if usage >= 0.90:
            return _EMERGENCY_REFRESH_SEC
        if usage >= 0.70:
            return _SLOW_REFRESH_SEC
        return _BASE_REFRESH_SEC

    # ── Helpers ──

    @property
    def quota_used_pct(self) -> float | None:
        """Son çağrıdaki kullanım yüzdesi (0.0-1.0), bilinmiyorsa None."""
        if self._last_used is None or self._last_remaining is None:
            return None
        total = self._last_used + self._last_remaining
        if total <= 0:
            return None
        return self._last_used / total
