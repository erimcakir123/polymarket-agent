"""ESPN NBA injury feed istemcisi — InjuryEvent parse + 60s in-memory cache.

Sadece NBA injuries endpoint'ini çeker; parsing ve filtreleme burada yapılır.
HTTP injectable (test mock için). Hata durumunda boş dict + WARNING log.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)

_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
_CACHE_TTL_SEC = 60   # 1 dakika
_HTTP_TIMEOUT = 15

_KNOWN_STATUSES: frozenset[str] = frozenset(
    {"Out", "Questionable", "Doubtful", "Day-To-Day"}
)


@dataclass
class InjuryEvent:
    athlete_name: str
    status: Literal["Out", "Questionable", "Doubtful", "Day-To-Day"]
    reported_at: datetime   # UTC-aware
    team_id: str
    is_starter: bool


class EspnInjuryClient:
    """ESPN NBA injury feed — fetch + 60s cache."""

    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        cache_ttl_sec: int = _CACHE_TTL_SEC,
        timeout: int = _HTTP_TIMEOUT,
    ) -> None:
        self._http = http_get or httpx.get
        self._cache_ttl_sec = cache_ttl_sec
        self._timeout = timeout
        self._cache: dict[str, tuple[Any, float]] = {}  # key → (data, timestamp)

    # ── Public API ──

    def fetch_nba_injuries(self) -> dict[str, list[InjuryEvent]]:
        """Tüm NBA injury kayıtlarını çek. dict[team_id → list[InjuryEvent]]. 60s cache."""
        cache_key = "nba_injuries"
        cached = self._cache.get(cache_key)
        if cached is not None:
            data, ts = cached
            if (time.time() - ts) < self._cache_ttl_sec:
                return data  # type: ignore[return-value]

        raw = self._fetch_raw()
        if raw is None:
            return {}

        result = self._parse(raw)
        self._cache[cache_key] = (result, time.time())
        return result

    def get_recent_injuries(self, hours: int = 2) -> dict[str, list[InjuryEvent]]:
        """Son N saat içinde bildirilen injury'leri döner. fetch_nba_injuries() cache'ini kullanır."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
        all_injuries = self.fetch_nba_injuries()
        result: dict[str, list[InjuryEvent]] = {}
        for team_id, events in all_injuries.items():
            recent = [e for e in events if e.reported_at >= cutoff]
            if recent:
                result[team_id] = recent
        return result

    # ── Private helpers ──

    def _fetch_raw(self) -> dict | None:
        try:
            resp = self._http(_INJURIES_URL, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("ESPN NBA injuries fetch failed: %s", exc)
            return None

    def _parse(self, raw: dict) -> dict[str, list[InjuryEvent]]:
        result: dict[str, list[InjuryEvent]] = {}
        for team_block in raw.get("injuries") or []:
            team = team_block.get("team") or {}
            team_id: str = str(team.get("id", ""))
            if not team_id:
                continue
            events: list[InjuryEvent] = []
            for injury in team_block.get("injuries") or []:
                event = self._parse_injury(injury, team_id)
                if event is not None:
                    events.append(event)
            if events:
                result[team_id] = events
        return result

    def _parse_injury(self, injury: dict, team_id: str) -> InjuryEvent | None:
        athlete = injury.get("athlete") or {}
        athlete_name: str = athlete.get("displayName", "")

        status_block = athlete.get("status") or {}
        status_type = status_block.get("type") or {}
        status_str: str = status_type.get("description", "")
        if status_str not in _KNOWN_STATUSES:
            return None

        date_str: str = injury.get("date", "")
        try:
            reported_at = datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError) as exc:
            logger.warning("ESPN injury date parse failed (%r): %s", date_str, exc)
            return None

        is_starter: bool = bool(status_block.get("starter", False))

        return InjuryEvent(
            athlete_name=athlete_name,
            status=status_str,  # type: ignore[arg-type]
            reported_at=reported_at,
            team_id=team_id,
            is_starter=is_starter,
        )
