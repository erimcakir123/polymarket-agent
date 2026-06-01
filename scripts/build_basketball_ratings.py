"""Basketball ratings build CLI — bulk fetch + Elo/Efficiency cache yaz.

Sackmann build_tennis_ratings paterni paralel. Lig-başına:
  NBA / WNBA       → nba_api current season game-log
  NCAAB / WNCAAB   → ESPN scoreboard son 90 gün (paralel scrape)
  Euroleague       → euroleague-api current season

Çıktı: data/basketball_cache/{league}_ratings.json (atomic write).

Kullanım:
  python scripts/build_basketball_ratings.py            # tüm enabled ligler
  python scripts/build_basketball_ratings.py --league nba
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from src.config.settings import load_config
from src.infrastructure.data.basketball.espn_pbp_refresher import (
    fetch_game_log_via_espn,
)
from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
)
from src.infrastructure.data.basketball.schemas import GameRecord
from src.orchestration.basketball_ratings_builder import (
    build_and_persist_snapshots,
)

logger = logging.getLogger(__name__)

# NCAAB/WNCAAB için boot bulk fetch — son N gün ESPN scrape.
_COLLEGE_LOOKBACK_DAYS = 90


def _fetch_nba_or_wnba(league: str) -> list[GameRecord]:
    from nba_api.stats.endpoints import leaguegamelog  # noqa: PLC0415
    current = datetime.now(timezone.utc).year
    season = str(current - 1)  # nba_api 4-digit, current season
    return fetch_game_log_via_nba_api(
        league=league, season=season,
        endpoint_factory=lambda **kw: leaguegamelog.LeagueGameLog(
            season=kw["season"], league_id=kw["league_id"],
            season_type_all_star="Regular Season",
        ),
    )


def _fetch_espn_college(league: str) -> list[GameRecord]:
    out: list[GameRecord] = []
    today = datetime.now(timezone.utc).date()
    for i in range(_COLLEGE_LOOKBACK_DAYS):
        day = (today - timedelta(days=i)).isoformat()
        games = fetch_game_log_via_espn(
            league=league, date_utc=day, http_get=requests.get,
        )
        out.extend(games)
    return out


def _fetch_euroleague(league: str) -> list[GameRecord]:
    """Euroleague + EuroCup — euroleague-api opsiyonel, paket yoksa boş."""
    try:
        from euroleague_api.game_stats import GameStats  # noqa: PLC0415
    except ImportError:
        logger.warning("euroleague-api paketi yüklü değil — %s skip", league)
        return []
    from src.infrastructure.data.basketball.euroleague_refresher import (  # noqa: PLC0415
        fetch_game_log_via_euroleague_api,
    )
    current = datetime.now(timezone.utc).year
    season = str(current - 1)
    return fetch_game_log_via_euroleague_api(
        season=season,
        endpoint_factory=lambda **kw: GameStats(season=int(kw["season"])),
        competition=league,
    )


def _fetch_brscraper_european(league: str) -> list[GameRecord]:
    """BSL/ACB/Lega — BRScraper opsiyonel, paket yoksa boş."""
    try:
        import BRScraper  # noqa: PLC0415, F401
    except ImportError:
        logger.warning("BRScraper paketi yüklü değil — %s skip", league)
        return []
    from src.infrastructure.data.basketball.brscraper_refresher import (  # noqa: PLC0415
        fetch_european_league_games,
    )
    current = datetime.now(timezone.utc).year
    season = f"{current - 1}-{current % 100:02d}"

    def _fetcher(lg: str, sn: str) -> list[dict]:
        # BRScraper API wrapper — gerçek paket installed olunca burada
        # BRScraper.NBA.get_box_scores benzeri çağrı yapılır.
        # Şu an placeholder: paket yüklü değil senaryosu fail-safe boş döner.
        return []

    return fetch_european_league_games(league=league, season=season, fetcher=_fetcher)


_FETCHERS = {
    # nba_api destekli ligler (league_id mapping otomatik)
    "nba": _fetch_nba_or_wnba,
    "wnba": _fetch_nba_or_wnba,
    "g_league": _fetch_nba_or_wnba,
    "summer_league": _fetch_nba_or_wnba,
    # ESPN scoreboard (college)
    "ncaab": _fetch_espn_college,
    "wncaab": _fetch_espn_college,
    # euroleague-api (Avrupa #1 + #2)
    "euroleague": _fetch_euroleague,
    "eurocup": _fetch_euroleague,
    # BRScraper Avrupa yerel ligler
    "bsl": _fetch_brscraper_european,
    "acb": _fetch_brscraper_european,
    "lega": _fetch_brscraper_european,
}


def build_league(league: str, cfg) -> int:
    """Tek lig için fetch + build + persist. Returns yazılan team snapshot sayısı."""
    fetcher = _FETCHERS.get(league)
    params = cfg.basketball.leagues.get(league)
    if fetcher is None or params is None:
        logger.warning("Unknown league: %s", league)
        return 0
    print(f"[BUILD] {league}: fetching game log...")
    try:
        games = fetcher(league)
    except Exception as exc:  # noqa: BLE001 — infra boundary
        logger.warning("Fetch failed for %s: %s", league, exc)
        print(f"[BUILD] {league}: SKIPPED ({exc})")
        return 0
    if not games:
        print(f"[BUILD] {league}: no games fetched")
        return 0
    print(f"[BUILD] {league}: {len(games)} game fetched, building ratings...")
    output_path = Path(cfg.basketball.cache_dir) / f"{league}_ratings.json"
    n = build_and_persist_snapshots(
        games=games, league=league,
        k_factor=params.k_factor, home_advantage=params.home_advantage,
        output_path=output_path,
    )
    print(f"[BUILD] {league}: {n} team snapshot saved -> {output_path}")
    return n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--league",
        help="Sadece tek lig (yoksa enabled_leagues hepsi)",
        default=None,
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_config()
    leagues = [args.league] if args.league else cfg.basketball.enabled_leagues
    total = 0
    for league in leagues:
        total += build_league(league, cfg)
    print(f"[BUILD] DONE — {total} team snapshot total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
