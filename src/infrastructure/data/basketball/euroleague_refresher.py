"""Euroleague API refresher — Faz 3 birincil veri kaynağı.

Bağımlılık: euroleague-api (giasemidis, PyPI sustainable, ~210 weekly download).
Endpoint mantığı: GameStats per season + game.
FIBA possessions katsayısı: 0.46 (NBA 0.44'ten farklı, NCAAB 0.475'ten farklı).

Endpoint factory dependency injection paterni nba_api_refresher ile aynı —
gerçek API çağrısı çağıran orchestration tarafından sağlanır. Bu sayede
test'ler euroleague-api paketi gerektirmeden mock'lanır.
"""
from __future__ import annotations

import logging
from typing import Callable, Iterable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

# FIBA kuralları — 0.46 (Dean Oliver formülünün Avrupa basket için kalibrasyonu).
# Sebep: 24sn shot clock, free throw kuralları farklı.
_FIBA_FTA_POSS_FACTOR = 0.46

# Task 6: Euroleague + EuroCup competition kodu (euroleague-api convention).
_COMPETITION_CODES: dict[str, str] = {
    "euroleague": "E",
    "eurocup": "U",
}


def _row_possessions(row: dict) -> float:
    """Bir takım satırından possessions hesabı (FIBA katsayısı)."""
    fga = float(row.get("FieldGoalsAttempted", row.get("FGA", 0)))
    fta = float(row.get("FreeThrowsAttempted", row.get("FTA", 0)))
    oreb = float(row.get("OffensiveRebounds", row.get("OREB", 0)))
    tov = float(row.get("Turnovers", row.get("TOV", 0)))
    return fga + _FIBA_FTA_POSS_FACTOR * fta - oreb + tov


def _convert_euroleague_row_to_game_record(
    home_row: dict, away_row: dict, league: str = "euroleague",
) -> GameRecord:
    """İki takım satırını GameRecord'a çevir. Euroleague API key isimleri farklı."""
    game_id = str(home_row.get("Gamecode", home_row.get("GameID", "")))
    season_year = int(home_row.get("Season", 2024))
    return GameRecord(
        game_id=game_id,
        season=f"{season_year}-{(season_year + 1) % 100:02d}",
        game_date_utc=str(home_row.get("Date", "2024-10-01T00:00:00Z")),
        home_team=str(home_row.get("TeamCode", home_row.get("Team", "")))[:4],
        away_team=str(away_row.get("TeamCode", away_row.get("Team", "")))[:4],
        home_score=int(home_row.get("Points", home_row.get("PTS", 0))),
        away_score=int(away_row.get("Points", away_row.get("PTS", 0))),
        home_possessions=round(_row_possessions(home_row), 2) or 1.0,
        away_possessions=round(_row_possessions(away_row), 2) or 1.0,
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def fetch_game_log_via_euroleague_api(
    season: str,
    endpoint_factory: Callable,
    competition: str = "euroleague",
) -> list[GameRecord]:
    """euroleague-api üzerinden bir sezonun maç istatistiklerini çek.

    Task 6: competition='euroleague' (default) veya 'eurocup'.
    Endpoint factory `competition_code` parametresi alır (E veya U).
    Boş cevap → boş liste. Bilinmeyen format → ValidationError (Pydantic).
    """
    code = _COMPETITION_CODES.get(competition)
    if code is None:
        raise ValueError(f"Unsupported competition: {competition}")
    endpoint = endpoint_factory(season=season, competition_code=code)
    rows = endpoint.get_game_stats()
    if not rows:
        return []
    return list(_pair_and_convert(rows, league=competition))


def _pair_and_convert(rows: Iterable[dict], league: str = "euroleague") -> Iterable[GameRecord]:
    """Game_id (Gamecode) başına iki satırı (home + away) eşleştir."""
    by_game: dict[str, list[dict]] = {}
    for row in rows:
        gid = str(row.get("Gamecode", row.get("GameID", "")))
        if gid:
            by_game.setdefault(gid, []).append(row)
    for game_id, pair in by_game.items():
        if len(pair) != 2:
            logger.warning(
                "euroleague_api game %s has %d rows, expected 2 — skipping",
                game_id, len(pair),
            )
            continue
        a, b = pair
        # Euroleague'de "home" alanı genelde "Home" boolean veya "HomeAway" string
        home_flag_a = str(a.get("HomeAway", a.get("Home", ""))).lower()
        if home_flag_a in ("home", "true", "1"):
            home, away = a, b
        else:
            home, away = b, a
        try:
            yield _convert_euroleague_row_to_game_record(home, away, league=league)
        except Exception as exc:  # noqa: BLE001 — infra boundary, log + skip
            logger.warning(
                "euroleague_api row pair convert failed for game %s: %s",
                game_id, exc,
            )
