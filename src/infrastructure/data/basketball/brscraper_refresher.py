"""BRScraper Avrupa yerel ligler — BSL (Türkiye), ACB (İspanya), Lega (İtalya).

BRScraper basketball-reference.com'u scrape eder. Bu modül:
  - Dependency injection: `fetcher` Callable[league, season] → list[dict] alır
  - Pydantic GameRecord validation (schema fail-fast)
  - Sessiz hata yok — bozuk satır warning + skip
  - Cache age check çağıran orchestration'da (source_freshness.py)
  - NO DATA → NO TRADE: fetcher exception → boş liste (caller bookmaker'a düşer)

ARCH_GUARD §12: try/except sadece infra'da, log + degrade.
"""
from __future__ import annotations

import logging
from typing import Callable

from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)

# basketball-reference.com Avrupa lig slug'ları (BSL=Türkiye, ACB=İspanya, Lega=İtalya).
_SUPPORTED_BR_LEAGUES = ("bsl", "acb", "lega")

# Dean Oliver possessions katsayısı — FIBA kuralları için 0.46
_FIBA_FTA_POSS_FACTOR = 0.46


def _row_possessions(row: dict, side: str) -> float:
    """Bir takım satırından possessions (Dean Oliver FIBA)."""
    fga = float(row.get(f"{side}_fga", 0) or 0)
    fta = float(row.get(f"{side}_fta", 0) or 0)
    orb = float(row.get(f"{side}_orb", 0) or 0)
    tov = float(row.get(f"{side}_tov", 0) or 0)
    return fga + _FIBA_FTA_POSS_FACTOR * fta - orb + tov


def _convert_row(row: dict, league: str) -> GameRecord:
    """BRScraper satırından GameRecord. Pydantic ValidationError fail-fast."""
    return GameRecord(
        game_id=f"{league}-{row['date']}-{row['home_team_abbr']}-{row['away_team_abbr']}",
        season=str(row.get("season", "2024-25")),
        game_date_utc=str(row["date"]) + "T00:00:00Z",
        home_team=str(row["home_team_abbr"])[:4],
        away_team=str(row["away_team_abbr"])[:4],
        home_score=int(row["home_points"]),
        away_score=int(row["away_points"]),
        home_possessions=round(_row_possessions(row, "home"), 2) or 1.0,
        away_possessions=round(_row_possessions(row, "away"), 2) or 1.0,
        is_final=True,
        league=league,  # type: ignore[arg-type]
    )


def fetch_european_league_games(
    league: str,
    season: str,
    fetcher: Callable[[str, str], list[dict]],
) -> list[GameRecord]:
    """BSL/ACB/Lega bir sezonun tüm tamamlanmış maçlarını çek.

    fetcher: BRScraper.get_schedule veya benzeri — (league, season) → list[dict].
    Sessiz hata yok: bozuk satır warning + skip, network hata empty + warning.
    NO DATA → NO TRADE: empty liste caller'da basketball_anchor_enricher None döner,
    moneyline'da bookmaker fallback, alt-market'te trade YASAK.
    """
    if league not in _SUPPORTED_BR_LEAGUES:
        raise ValueError(f"Unsupported European league: {league}")
    try:
        rows = fetcher(league, season)
    except Exception as exc:  # noqa: BLE001 — infra boundary
        logger.warning("BRScraper fetch failed for %s %s: %s", league, season, exc)
        return []
    out: list[GameRecord] = []
    for row in rows or []:
        try:
            out.append(_convert_row(row, league))
        except Exception as exc:  # noqa: BLE001 — schema fail-fast, log + skip
            logger.warning("BRScraper row skipped (malformed): %s", exc)
    return out
