"""ESPN public scoreboard istemcisi (SPEC-B Task 1).

Endpoint: https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard
API key gerektirmez. Public access.

Desteklenen sporlar: hokey (NHL), beyzbol (MLB), basketbol (NBA), tenis (ATP/WTA).
Tenis: 2026-05-20 (tennis-lab) — top-level "tournament" event içinde
`groupings[].competitions[]` ile match-level dolaşılır; competitors `athlete`
objesi (team değil), score = sets won, period_number = current set,
home/away_score = games in current set (linescores son entry).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

_ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
_DEFAULT_HTTP_TIMEOUT = 10


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


# MatchStatus 2026-05-27'de src/models/match_status.py'a taşındı (strategy + infra
# arası katman ihlalini gidermek için). Geriye dönük import yolu korunur.
from src.models.match_status import MatchStatus  # noqa: E402


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


def _count_tennis_sets_won(linescores: Any) -> int | None:
    """Tenis: athlete'in linescores listesinde `winner=True` set sayısı.

    None döner sadece liste yoksa/geçersizse — boş liste 0 set sayılır (pre-match).
    """
    if not isinstance(linescores, list):
        return None
    return sum(1 for ls in linescores if isinstance(ls, dict) and ls.get("winner") is True)


class ESPNClient:
    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        timeout: int = _DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self._http_get = http_get or httpx.get
        self._timeout = timeout

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

    def get_match_status(self, event_id: str, sport: str) -> MatchStatus | None:
        """Belirli bir event_id için ESPN status'ını döner.

        Returns:
            MatchStatus: maç bulundu ve parse edildi
            None: API hatası, parse hatası, event bulunamadı
        """
        if sport == "tennis":
            leagues = ["atp", "wta"]
        else:
            leagues = [sport]

        for league in leagues:
            url = f"{_ESPN_BASE_URL}/{sport}/{league}/scoreboard"
            try:
                resp = self._http_get(url, params={}, timeout=self._timeout)
                if resp.status_code >= 400:
                    continue
                data = resp.json()
            except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
                logger.warning("ESPN status %s/%s failed: %s", sport, league, e)
                continue
            except Exception as e:
                logger.warning("ESPN status %s/%s unexpected: %s", sport, league, e)
                continue

            status = self._find_event_status(data, event_id, sport)
            if status is not None:
                return status

        return None

    def _find_event_status(self, data: dict, event_id: str, sport: str) -> MatchStatus | None:
        """ESPN scoreboard data'sında event_id'yi bul, MatchStatus döndür.

        Tek bir bozuk event ham aramayı durdurmaz — _parse_events ile aynı
        defansif pattern: per-event try/except + log + continue.
        """
        events = data.get("events") or []
        for ev in events:
            try:
                if sport == "tennis":
                    for grouping in (ev.get("groupings") or []):
                        for comp in (grouping.get("competitions") or []):
                            if str(comp.get("id", "")) == str(event_id):
                                return self._extract_status(comp)
                else:
                    if str(ev.get("id", "")) == str(event_id):
                        comps = ev.get("competitions") or []
                        if comps:
                            return self._extract_status(comps[0])
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("ESPN status event parse failed (%s): %s", ev.get("id", "?"), e)
                continue
        return None

    @staticmethod
    def _extract_status(comp: dict) -> MatchStatus | None:
        """Competition dict'ten MatchStatus üret. None → parse başarısız."""
        status = comp.get("status") or {}
        type_info = status.get("type") or {}
        state = (type_info.get("state") or "").lower()
        if not state:
            return None
        period_raw = status.get("period")
        period = period_raw if isinstance(period_raw, int) and period_raw > 0 else None
        completed = bool(type_info.get("completed", False))
        return MatchStatus(state=state, period=period, is_completed=completed)

    def _parse_events(self, data: dict, sport: str) -> list[ESPNMatchScore]:
        events = data.get("events") or []
        if not isinstance(events, list):
            return []
        out: list[ESPNMatchScore] = []
        for ev in events:
            try:
                if sport == "tennis":
                    # Tournament wrapper → her grouping'in match'lerini ayrı match olarak çıkar.
                    out.extend(self._parse_tennis_event(ev))
                else:
                    score = self._parse_event(ev, sport)
                    if score is not None:
                        out.append(score)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("ESPN event parse failed (%s): %s", ev.get("id", "?"), e)
                continue
        return out

    def _parse_tennis_event(self, ev: dict) -> list[ESPNMatchScore]:
        """Tenis tournament event → match-level ESPNMatchScore listesi.

        ESPN tenis response'u takım sporlarından farklı: top-level `events[i]` bir
        TURNUVA (örn. "Bitpanda Hamburg Open"), her turnuva `groupings[]` (mens-/womens-
        singles vb.) altında `competitions[]` ile gerçek maçları taşır. Her competition
        iki athlete'lı bir maçtır; `linescores[]` set başına oyun sayısını, `status.period`
        cari set numarasını verir. Match-level event_id = competition.id.
        """
        out: list[ESPNMatchScore] = []
        tournament_date = str(ev.get("date") or "")
        for grouping in (ev.get("groupings") or []):
            for comp in (grouping.get("competitions") or []):
                score = self._parse_tennis_competition(comp, tournament_date)
                if score is not None:
                    out.append(score)
        return out

    def _parse_tennis_competition(
        self, comp: dict, fallback_date: str,
    ) -> ESPNMatchScore | None:
        """Tek bir tenis maçını ESPNMatchScore'a çevir."""
        event_id = str(comp.get("id", ""))
        if not event_id:
            return None
        competitors = comp.get("competitors") or []
        home, away = self._split_home_away(competitors)
        if home is None or away is None:
            return None

        status = comp.get("status") or {}
        type_info = status.get("type") or {}
        is_completed = bool(type_info.get("completed", False))
        state = (type_info.get("state") or "").lower()
        is_live = state == "in"
        period_num_raw = status.get("period")
        period_num = period_num_raw if isinstance(period_num_raw, int) and period_num_raw > 0 else None
        # Period string: "Set N" canlıda; "Final" tamamlanmışta. _estimate_elapsed_from_score
        # tennis branch'i bu string'i okuyarak elapsed_pct çıkartır.
        if is_completed:
            period_str = "Final"
        elif period_num is not None:
            period_str = f"Set {period_num}"
        else:
            period_str = str(type_info.get("name") or "")

        home_sets = _count_tennis_sets_won(home.get("linescores"))
        away_sets = _count_tennis_sets_won(away.get("linescores"))
        home_athlete = home.get("athlete") or {}
        away_athlete = away.get("athlete") or {}

        return ESPNMatchScore(
            event_id=event_id,
            home_name=str(home_athlete.get("displayName", "")),
            away_name=str(away_athlete.get("displayName", "")),
            home_team_id=str(home_athlete.get("id", "")),
            away_team_id=str(away_athlete.get("id", "")),
            home_score=home_sets,
            away_score=away_sets,
            period=period_str,
            is_completed=is_completed,
            is_live=is_live,
            last_updated=datetime.now(timezone.utc).isoformat(),
            commence_time=str(comp.get("date") or fallback_date),
            period_number=period_num,
        )

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
