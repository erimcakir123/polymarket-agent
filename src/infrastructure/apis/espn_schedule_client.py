"""ESPN NBA schedule istemcisi — GameEvent parse + B2B detection + 6h in-memory cache.

Takım bazlı schedule çeker; back-to-back detection burada yapılır.
HTTP injectable (test mock için). Hata durumunda boş liste + WARNING log.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SCHEDULE_URL_TEMPLATE = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule"
)
_CACHE_TTL_SEC = 21600  # 6 saat
_HTTP_TIMEOUT = 15


@dataclass
class GameEvent:
    game_id: str
    date: datetime      # UTC-aware
    home_team_id: str
    away_team_id: str
    status: str         # "scheduled", "in_progress", "final", etc.


class EspnScheduleClient:
    """ESPN NBA team schedule — fetch + 6h cache + back-to-back detection."""

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

    def get_team_schedule(self, team_id: str, season: int) -> list[GameEvent]:
        """Takımın verilen sezon maç takvimini çek. 6s cache. HTTP hata → []."""
        cache_key = f"{team_id}:{season}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            data, ts = cached
            if (time.time() - ts) < self._cache_ttl_sec:
                return data  # type: ignore[return-value]

        raw = self._fetch_raw(team_id, season)
        if raw is None:
            return []

        result = self._parse(raw)
        self._cache[cache_key] = (result, time.time())
        return result

    def days_since_last_game(
        self, team_id: str, reference_date: datetime, season: int
    ) -> int | None:
        """Reference date'ten önceki en son tamamlanmış maçın kaç gün önce olduğunu döner.
        'final' olmayan maçlar sayılmaz. Önceki maç yoksa None döner.
        """
        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)

        games = self.get_team_schedule(team_id, season)
        prior_finals = [
            g for g in games
            if g.status == "final" and g.date < reference_date
        ]
        if not prior_finals:
            return None

        most_recent = max(prior_finals, key=lambda g: g.date)
        return (reference_date.date() - most_recent.date.date()).days

    def is_back_to_back(
        self, team_id: str, current_game_date: datetime, season: int
    ) -> bool:
        """Bir önceki maç dün ise True (back-to-back)."""
        return self.days_since_last_game(team_id, current_game_date, season) == 1

    # ── Private helpers ──

    def _fetch_raw(self, team_id: str, season: int) -> dict | None:
        url = _SCHEDULE_URL_TEMPLATE.format(team_id=team_id)
        try:
            resp = self._http(url, params={"season": season}, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("ESPN schedule fetch failed team=%s season=%s: %s", team_id, season, exc)
            return None

    def _parse(self, raw: dict) -> list[GameEvent]:
        result: list[GameEvent] = []
        for event in raw.get("events") or []:
            game = self._parse_event(event)
            if game is not None:
                result.append(game)
        return result

    def _parse_event(self, event: dict) -> GameEvent | None:
        try:
            game_id: str = event["id"]
            date_str: str = event["date"]
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

            competition = event["competitions"][0]
            competitors = competition["competitors"]

            home_team_id = next(
                c["team"]["id"] for c in competitors if c["homeAway"] == "home"
            )
            away_team_id = next(
                c["team"]["id"] for c in competitors if c["homeAway"] == "away"
            )
            status: str = (
                competition["status"]["type"]["description"].lower()
            )
            return GameEvent(
                game_id=game_id,
                date=date,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                status=status,
            )
        except (KeyError, IndexError, ValueError, StopIteration) as exc:
            logger.warning("ESPN schedule event parse failed (%r): %s", event.get("id"), exc)
            return None
