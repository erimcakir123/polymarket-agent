"""ESPN public scoreboard istemcisi (SPEC-B Task 1).

Endpoint: https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard
API key gerektirmez. Public access.

Desteklenen sporlar: hokey (NHL), beyzbol (MLB), basketbol (NBA),
tenis (ATP/WTA — sadece match_start için, skor entegrasyonu yok).
Soccer scope dışı.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

_ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
_ESPN_CORE_URL = "https://sports.core.api.espn.com/v2/sports"
_DEFAULT_HTTP_TIMEOUT = 10
_TENNIS_COMPETITIONS_LIMIT = 50


@dataclass
class ESPNMatchScore:
    """ESPN scoreboard API'den gelen tek bir maçın skor bilgisi."""

    event_id: str
    home_name: str
    away_name: str
    home_team_id: str = ""
    away_team_id: str = ""
    home_score: int | None = None
    away_score: int | None = None
    period: str = ""
    is_completed: bool = False
    is_live: bool = False
    last_updated: str = ""
    commence_time: str = ""
    inning: int | None = None
    inning_half: str | None = None
    period_number: int | None = None
    clock_seconds: int | None = None
    raw_status: dict[str, Any] = field(default_factory=dict)


def _parse_clock_to_seconds(clock: str) -> int | None:
    if not clock or not isinstance(clock, str):
        return None
    parts = clock.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except (ValueError, TypeError):
        return None
    if minutes < 0 or seconds < 0 or seconds >= 60:
        return None
    return minutes * 60 + seconds


def _parse_inning_half(short_detail: str) -> str | None:
    if not short_detail:
        return None
    s = short_detail.strip().lower()
    if s.startswith("top"):
        return "top"
    if s.startswith("bot"):
        return "bottom"
    return None


def _parse_score(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


class ESPNClient:
    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        timeout: int = _DEFAULT_HTTP_TIMEOUT,
        athlete_cache_ttl_sec: int = 86400,
    ) -> None:
        self._http_get = http_get or httpx.get
        self._timeout = timeout
        self._athlete_ttl = athlete_cache_ttl_sec
        self._athlete_cache: dict[str, tuple[float, str]] = {}

    def fetch_scoreboard(
        self,
        sport: str,
        league: str,
        date: str | None = None,
    ) -> list[ESPNMatchScore]:
        url = f"{_ESPN_BASE_URL}/{sport}/{league}/scoreboard"
        params: dict[str, str] = {}
        if date:
            params["dates"] = date

        try:
            resp = self._http_get(url, params=params, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN %s/%s returned %d", sport, league, resp.status_code)
                return []
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN %s/%s fetch failed: %s", sport, league, e)
            return []
        except Exception as e:
            logger.warning("ESPN %s/%s unexpected error: %s", sport, league, e)
            return []

        return self._parse_events(data, sport)

    def fetch_tennis_matches_today(
        self,
        league: str,
        date_yyyymmdd: str,
    ) -> list[ESPNMatchScore]:
        """Tennis için 3-aşamalı bugünkü maç fetch.

        Akış:
          1. scoreboard?dates=DATE → aktif turnuva ID'leri
          2. Her turnuva için competitions?dates=DATE → bugünkü maç competition'ları
          3. Her competition detail + athlete dereference → maç + oyuncu adları

        Athlete fetch'leri _athlete_cache içinde TTL ile saklanır.
        HTTP fail → ilgili maç atlanır, log warning, partial result.
        """
        tournaments = self._fetch_tennis_active_tournaments(league, date_yyyymmdd)
        if not tournaments:
            return []
        # 2. Tum turnuva competition ref'lerini topla
        comp_refs: list[str] = []
        for tid in tournaments:
            comp_refs.extend(self._fetch_tennis_competitions(league, tid, date_yyyymmdd))
        # 3a. Tum competition detail'lerini once cek (athlete ref'leri ortaya cikar)
        comp_details: list[dict[str, Any]] = []
        for ref in comp_refs:
            detail = self._fetch_tennis_competition_detail(ref)
            if detail is not None:
                comp_details.append(detail)
        # 3b. Sonra athlete'leri resolve et (cache: ayni oyuncu = tek HTTP)
        matches: list[ESPNMatchScore] = []
        for comp in comp_details:
            score = self._build_tennis_match_from_detail(comp)
            if score is not None:
                matches.append(score)
        return matches

    def _fetch_tennis_active_tournaments(self, league: str, date: str) -> list[str]:
        url = f"{_ESPN_BASE_URL}/tennis/{league}/scoreboard"
        try:
            resp = self._http_get(url, params={"dates": date}, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN tennis/%s scoreboard returned %d", league, resp.status_code)
                return []
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN tennis/%s scoreboard fetch failed: %s", league, e)
            return []
        events = data.get("events") or []
        iso_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        active: list[str] = []
        for ev in events:
            tid = str(ev.get("id", ""))
            end = ev.get("endDate") or ev.get("date") or ""
            if not tid or not end:
                continue
            # endDate'in tarih kismi >= bugun ise turnuva hala aktif
            if end[:10] < iso_date:
                continue
            active.append(tid)
        return active

    def _fetch_tennis_competitions(self, league: str, tid: str, date: str) -> list[str]:
        url = f"{_ESPN_CORE_URL}/tennis/leagues/{league}/events/{tid}/competitions"
        try:
            resp = self._http_get(
                url,
                params={"dates": date, "limit": _TENNIS_COMPETITIONS_LIMIT},
                timeout=self._timeout,
            )
            if resp.status_code >= 400:
                logger.warning("ESPN tennis/%s/%s competitions returned %d",
                               league, tid, resp.status_code)
                return []
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN tennis/%s/%s competitions fetch failed: %s", league, tid, e)
            return []
        refs: list[str] = []
        for it in data.get("items") or []:
            ref = it.get("$ref")
            if ref:
                refs.append(str(ref))
        return refs

    def _fetch_tennis_competition_detail(self, comp_ref: str) -> dict[str, Any] | None:
        try:
            resp = self._http_get(comp_ref, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN tennis competition %s returned %d", comp_ref, resp.status_code)
                return None
            return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN tennis competition fetch failed (%s): %s", comp_ref, e)
            return None

    def _build_tennis_match_from_detail(self, comp: dict[str, Any]) -> ESPNMatchScore | None:
        competitors = comp.get("competitors") or []
        if len(competitors) < 2:
            return None
        athlete_refs: list[str] = []
        for c in competitors[:2]:
            ref = ((c.get("athlete") or {}).get("$ref") or "").strip()
            if not ref:
                return None
            athlete_refs.append(ref)
        names = [self._resolve_athlete_name(r) for r in athlete_refs]
        if not all(names):
            return None
        return ESPNMatchScore(
            event_id=str(comp.get("id", "")),
            home_name=names[0],
            away_name=names[1],
            commence_time=str(comp.get("date", "")),
        )

    def _resolve_athlete_name(self, athlete_ref: str) -> str:
        now = time.time()
        cached = self._athlete_cache.get(athlete_ref)
        if cached is not None and (now - cached[0]) < self._athlete_ttl:
            return cached[1]
        try:
            resp = self._http_get(athlete_ref, timeout=self._timeout)
            if resp.status_code >= 400:
                logger.warning("ESPN athlete %s returned %d", athlete_ref, resp.status_code)
                return ""
            data = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN athlete fetch failed (%s): %s", athlete_ref, e)
            return ""
        name = str(data.get("displayName") or data.get("fullName") or "")
        if name:
            self._athlete_cache[athlete_ref] = (now, name)
        return name

    def _parse_events(self, data: dict, sport: str) -> list[ESPNMatchScore]:
        events = data.get("events") or []
        if not isinstance(events, list):
            return []
        out: list[ESPNMatchScore] = []
        for ev in events:
            try:
                score = self._parse_event(ev, sport)
                if score is not None:
                    out.append(score)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("ESPN event parse failed (%s): %s", ev.get("id", "?"), e)
                continue
        return out

    def _parse_event(self, ev: dict, sport: str) -> ESPNMatchScore | None:
        event_id = str(ev.get("id", ""))
        if not event_id:
            return None
        commence = str(ev.get("date") or "")
        comps = ev.get("competitions") or []
        if not comps:
            return None
        comp = comps[0]
        competitors = comp.get("competitors") or []
        home, away = self._split_home_away(competitors)
        if home is None or away is None:
            return None

        status = comp.get("status") or {}
        type_info = status.get("type") or {}
        is_completed = bool(type_info.get("completed", False))
        state = (type_info.get("state") or "").lower()
        is_live = state == "in"
        period_str = str(type_info.get("name") or "")

        inning = None
        inning_half = None
        period_num = None
        clock_secs = None

        if sport == "baseball":
            period_raw = status.get("period")
            if isinstance(period_raw, int) and period_raw > 0:
                inning = period_raw
            inning_half = _parse_inning_half(str(status.get("shortDetail") or ""))
        elif sport == "basketball":
            period_raw = status.get("period")
            if isinstance(period_raw, int) and period_raw > 0:
                period_num = period_raw
            clock_secs = _parse_clock_to_seconds(str(status.get("displayClock") or ""))

        raw_status = dict(status) if sport == "hockey" else {}

        return ESPNMatchScore(
            event_id=event_id,
            home_name=str(home.get("team", {}).get("displayName", "")),
            away_name=str(away.get("team", {}).get("displayName", "")),
            home_team_id=str(home.get("team", {}).get("id", "")),
            away_team_id=str(away.get("team", {}).get("id", "")),
            home_score=_parse_score(home.get("score")),
            away_score=_parse_score(away.get("score")),
            period=period_str,
            is_completed=is_completed,
            is_live=is_live,
            last_updated=datetime.now(timezone.utc).isoformat(),
            commence_time=commence,
            inning=inning,
            inning_half=inning_half,
            period_number=period_num,
            clock_seconds=clock_secs,
            raw_status=raw_status,
        )

    @staticmethod
    def _split_home_away(competitors: list[dict]) -> tuple[dict | None, dict | None]:
        home = away = None
        for c in competitors:
            ha = (c.get("homeAway") or "").lower()
            if ha == "home":
                home = c
            elif ha == "away":
                away = c
        return home, away
