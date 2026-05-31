"""nba_api üzerinden NBA + WNBA game-log çekme — birincil veri kaynağı.

Bağımlılık: `nba_api>=1.11`. Endpoint: leaguegamelog (her takımın satırı).
Bir maç iki satır olarak gelir (home + away) — `MATCHUP` alanından eşleştirilir.

Possessions formülü (Dean Oliver):
  poss ≈ FGA + 0.44 * FTA - OREB + TOV

Burada I/O yok — endpoint_factory dependency injection ile dışarıdan verilir.
Refresher çağıran orchestration gerçek endpoint'i sağlar.
"""
from __future__ import annotations

import logging
from typing import Callable, Iterable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

_SUPPORTED_LEAGUES = ("nba", "wnba")

# Dean Oliver possessions katsayısı — FTA'nın olası possessions sayısına katkısı.
_FTA_POSS_FACTOR = 0.44


def _row_possessions(row: dict) -> float:
    """Bir takım satırından possessions hesabı (Dean Oliver formülü)."""
    fga = float(row.get("FGA", 0))
    fta = float(row.get("FTA", 0))
    oreb = float(row.get("OREB", 0))
    tov = float(row.get("TOV", 0))
    return fga + _FTA_POSS_FACTOR * fta - oreb + tov


def _convert_nba_api_row_to_game_record(
    home_row: dict, away_row: dict, league: str,
) -> GameRecord:
    """İki takım satırını birleştirip GameRecord üret. Ev sahibi MATCHUP'tan belirlenir."""
    game_id = str(home_row["GAME_ID"])
    season = _format_season(str(home_row["SEASON_ID"]))
    date = str(home_row["GAME_DATE"]) + "T00:00:00Z"
    return GameRecord(
        game_id=game_id,
        season=season,
        game_date_utc=date,
        home_team=str(home_row["TEAM_ABBREVIATION"]),
        away_team=str(away_row["TEAM_ABBREVIATION"]),
        home_score=int(home_row["PTS"]),
        away_score=int(away_row["PTS"]),
        home_possessions=round(_row_possessions(home_row), 2),
        away_possessions=round(_row_possessions(away_row), 2),
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def _format_season(season_id: str) -> str:
    """SEASON_ID '22024' → '2024-25'."""
    if len(season_id) == 5:
        start = int(season_id[1:])
        return f"{start}-{(start + 1) % 100:02d}"
    return season_id


def fetch_game_log_via_nba_api(
    league: str,
    season: str,
    endpoint_factory: Callable,
) -> list[GameRecord]:
    """Bir lig + sezonun tamamlanmış maçlarını GameRecord listesi olarak döndür.

    `endpoint_factory` bir `nba_api.stats.endpoints.leaguegamelog.LeagueGameLog`
    benzeri callable olmalı. Gerçek wiring orchestration katmanında.

    Bilinmeyen lig → ValueError (fail-fast). Boş cevap → boş liste.
    """
    if league not in _SUPPORTED_LEAGUES:
        raise ValueError(f"Unsupported league: {league}")
    endpoint = endpoint_factory(season=season, league_id="00" if league == "nba" else "10")
    payload = endpoint.get_dict()
    rows = _rows_from_payload(payload)
    return list(_pair_and_convert(rows, league))


def _rows_from_payload(payload: dict) -> list[dict]:
    """nba_api result envelope'ından dict satır listesine çevir."""
    rs = payload.get("resultSets", [])
    if not rs:
        return []
    head = rs[0].get("headers", [])
    body = rs[0].get("rowSet", [])
    return [dict(zip(head, row)) for row in body]


def _pair_and_convert(rows: Iterable[dict], league: str) -> Iterable[GameRecord]:
    """Game_id başına iki satırı (home + away) eşleştir."""
    by_game: dict[str, list[dict]] = {}
    for row in rows:
        by_game.setdefault(str(row["GAME_ID"]), []).append(row)
    for game_id, pair in by_game.items():
        if len(pair) != 2:
            logger.warning("nba_api game %s has %d rows, expected 2 — skipping", game_id, len(pair))
            continue
        a, b = pair
        # MATCHUP "LAL vs. GSW" → home, "GSW @ LAL" → away
        home, away = (a, b) if "vs." in str(a.get("MATCHUP", "")) else (b, a)
        try:
            yield _convert_nba_api_row_to_game_record(home, away, league)
        except Exception as exc:  # noqa: BLE001 — infra boundary, log + skip
            logger.warning("nba_api row pair conversion failed for game %s: %s", game_id, exc)
