"""ESPN scoreboard endpoint'inden basket maç sonuçları — yedek veri kaynağı.

Endpoint örneği:
  https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/scoreboard?dates=YYYYMMDD

`nba_api` çökerse veya rate limit yerse buradan veri çekilir. ESPN HTML
değil JSON döner — schema drift Pydantic ile yakalanır.
"""
from __future__ import annotations

import logging
from typing import Callable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

_SUPPORTED_LEAGUES = ("nba", "wnba")
_ESPN_LEAGUE_PATH = {"nba": "nba", "wnba": "wnba"}
_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball"

_FTA_POSS_FACTOR = 0.44


def _stat(competitor: dict, name: str) -> float:
    for s in competitor.get("statistics", []):
        if s.get("name") == name:
            return float(s.get("displayValue", "0"))
    return 0.0


def _possessions(competitor: dict) -> float:
    return (
        _stat(competitor, "fieldGoalsAttempted")
        + _FTA_POSS_FACTOR * _stat(competitor, "freeThrowsAttempted")
        - _stat(competitor, "offensiveRebounds")
        + _stat(competitor, "turnovers")
    )


def _convert_espn_event_to_game_record(event: dict, league: str) -> GameRecord:
    """ESPN `event` JSON → GameRecord."""
    comp = event["competitions"][0]
    competitors = comp["competitors"]
    home = next(c for c in competitors if c.get("homeAway") == "home")
    away = next(c for c in competitors if c.get("homeAway") == "away")
    season_year = int(event["season"]["year"])
    return GameRecord(
        game_id=str(event["id"]),
        season=f"{season_year - 1}-{season_year % 100:02d}",
        game_date_utc=str(event["date"]).replace("Z", ":00Z") if "T" in str(event["date"]) and ":" not in str(event["date"])[-6:] else str(event["date"]),
        home_team=str(home["team"]["abbreviation"]),
        away_team=str(away["team"]["abbreviation"]),
        home_score=int(home["score"]),
        away_score=int(away["score"]),
        home_possessions=round(_possessions(home), 2) or 1.0,
        away_possessions=round(_possessions(away), 2) or 1.0,
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def fetch_game_log_via_espn(
    league: str,
    date_utc: str,
    http_get: Callable,
    timeout: int = 30,
) -> list[GameRecord]:
    """ESPN scoreboard endpoint'inden bir günün biten maçlarını çek.

    Date format: 'YYYY-MM-DD'. Tamamlanmamış maçlar atlanır (status.completed=False).
    HTTP/parse hatalarında boş liste + warning log.
    """
    if league not in _SUPPORTED_LEAGUES:
        raise ValueError(f"Unsupported league: {league}")
    yyyymmdd = date_utc.replace("-", "")
    url = f"{_ESPN_BASE}/{_ESPN_LEAGUE_PATH[league]}/scoreboard?dates={yyyymmdd}"
    try:
        resp = http_get(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — infra boundary
        logger.warning("ESPN scoreboard fetch failed: %s — %s", url, exc)
        return []
    if getattr(resp, "status_code", 0) != 200:
        logger.warning("ESPN scoreboard non-200: %s -> %d", url, getattr(resp, "status_code", 0))
        return []
    try:
        events = resp.json().get("events", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("ESPN scoreboard JSON parse failed: %s", exc)
        return []
    out: list[GameRecord] = []
    for ev in events:
        try:
            if not ev.get("status", {}).get("type", {}).get("completed", False):
                continue
            out.append(_convert_espn_event_to_game_record(ev, league))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ESPN event convert failed for id=%s: %s", ev.get("id"), exc)
    return out
