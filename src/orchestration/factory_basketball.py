"""Basketball wiring helpers — factory.py'dan ayrı modül (ARCH_GUARD §3).

build_agent içine inject edilen yardımcılar:
  - _load_basketball_caches: rating cache JSON'larını yükle
  - _make_basketball_fetchers: lig-bazlı primary/secondary fetch çiftleri
  - _maybe_build_basketball_ratings: boot'ta nba_api bulk build
  - _maybe_invoke_basketball_refresh: lig-bazlı refresh hook
  - _select_enricher_for_sport: sport_tag → enricher tipi seçimi
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import AppConfig
from src.infrastructure.data.basketball.team_ratings_store import (
    load_team_snapshots,
)

logger = logging.getLogger(__name__)


_TENNIS_SPORT_TAGS = frozenset({"tennis", "atp", "wta"})
_BASKETBALL_SPORT_TAGS = frozenset({
    "nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl",
    # 2026-06-01 yetki genişletme — gerçek veri kaynaklı ligler.
    "g_league", "summer_league", "eurocup",
})
_PRO_BASKET_LEAGUES = frozenset({"nba", "wnba", "g_league", "summer_league"})
_COLLEGE_BASKET_LEAGUES = frozenset({"ncaab", "wncaab"})
_EUROPE_BASKET_LEAGUES = frozenset({"euroleague", "eurocup"})


def _select_enricher_for_sport(sport_tag: str) -> str:
    """Sport_tag → enricher tipi seçimi.

    'tennis_model'    → Sackmann-anchored (Adım 3-5, tenis paper lab).
    'basketball_model' → Elo + Pace×Efficiency (Plan 1.C).
    'bookmaker'       → Odds API h2h fallback (diğer sporlar).
    """
    s = sport_tag.lower()
    if s in _TENNIS_SPORT_TAGS:
        return "tennis_model"
    if s in _BASKETBALL_SPORT_TAGS:
        return "basketball_model"
    return "bookmaker"


def _load_basketball_caches(cfg: AppConfig) -> tuple[dict, dict]:
    """Lig-başına team_ratings_store JSON'larından ratings + efficiencies oku.

    Returns: ({league: {team: EloRating}}, {league: {team: TeamEfficiency}}).
    Eksik dosya → boş dict (degrade — basketball_dispatch bookmaker fallback).
    """
    from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
    from src.domain.pricing.basketball.team_elo import EloRating

    cache_dir = Path(cfg.basketball.cache_dir)
    ratings: dict[str, dict[str, EloRating]] = {}
    efficiencies: dict[str, dict[str, TeamEfficiency]] = {}
    for league in cfg.basketball.enabled_leagues:
        path = cache_dir / f"{league}_ratings.json"
        snapshots = load_team_snapshots(path, league=league)
        if not snapshots:
            continue
        ratings[league] = {
            team: EloRating(rating=snap.elo_rating, games=snap.elo_games)
            for team, snap in snapshots.items()
        }
        efficiencies[league] = {
            team: TeamEfficiency(
                adj_o=snap.adj_o, adj_d=snap.adj_d, adj_pace=snap.adj_pace,
            )
            for team, snap in snapshots.items()
        }
        logger.info(
            "Basketball ratings yüklendi: %s — %d takım",
            league, len(snapshots),
        )
    return ratings, efficiencies


def _make_basketball_fetchers(
    league: str,
    date_utc: str,
    http_get,
    espn_fetcher,
):
    """Lig-bazlı (primary_fetch, secondary_fetch) callable çifti üret.

    NBA / WNBA: primary nba_api stub (Plan 1.B wiring noktası), secondary ESPN.
    NCAAB / WNCAAB: primary ESPN, secondary boş (yedek kaynak yok).
    Euroleague: primary euroleague-api stub (Faz 3 wiring), secondary boş.
    """
    def _empty_list() -> list:
        return []

    def _espn(_league: str = league, _date: str = date_utc) -> list:
        return espn_fetcher(league=_league, date_utc=_date, http_get=http_get)

    if league in _PRO_BASKET_LEAGUES:
        return _empty_list, _espn
    if league in _COLLEGE_BASKET_LEAGUES:
        return _espn, _empty_list
    if league in _EUROPE_BASKET_LEAGUES:
        return _empty_list, _empty_list
    return _empty_list, _empty_list


def _maybe_build_basketball_ratings(cfg: AppConfig) -> None:
    """Bot başlangıçta basket ratings cache build (Sackmann paralel).

    Her enabled lig için:
      - Cache yoksa veya 24sa+ eskiyse: scripts/build_basketball_ratings.py paterni
      - NBA/WNBA: nba_api bulk fetch (hızlı, 1 API call)
      - NCAAB/WNCAAB/Euroleague: manuel öneri (boot'ta blocking çok yavaş olur)
    """
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    enabled = [lg for lg in cfg.basketball.enabled_leagues if lg in tags_lc]
    if not enabled:
        return
    import time  # noqa: PLC0415
    from datetime import datetime, timezone  # noqa: PLC0415

    cache_dir = Path(cfg.basketball.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    # nba_api destekli liglerin hepsi hızlı bulk build (NBA + WNBA + G League + Summer League).
    fast_build_leagues = {"nba", "wnba", "g_league", "summer_league"}

    for league in enabled:
        cache_path = cache_dir / f"{league}_ratings.json"
        if cache_path.exists():
            age_h = (time.time() - cache_path.stat().st_mtime) / 3600.0
            if age_h < 24.0:
                logger.info(
                    "Basketball ratings fresh: %s (age=%.1fh, skip)",
                    league, age_h,
                )
                continue
        if league not in fast_build_leagues:
            logger.warning(
                "Basketball ratings cache yok/eski: %s. "
                "Manuel build: python scripts/build_basketball_ratings.py --league %s",
                league, league,
            )
            continue
        params = cfg.basketball.leagues.get(league)
        if params is None:
            continue
        try:
            from nba_api.stats.endpoints import leaguegamelog  # noqa: PLC0415

            from src.infrastructure.data.basketball.nba_api_refresher import (  # noqa: PLC0415
                fetch_game_log_via_nba_api,
            )
            from src.orchestration.basketball_ratings_builder import (  # noqa: PLC0415
                build_and_persist_snapshots,
            )
            current = datetime.now(timezone.utc).year
            season = str(current - 1)
            logger.info("Basketball ratings build: %s season=%s", league, season)
            games = fetch_game_log_via_nba_api(
                league=league, season=season,
                endpoint_factory=lambda **kw: leaguegamelog.LeagueGameLog(
                    season=kw["season"], league_id=kw["league_id"],
                    season_type_all_star="Regular Season",
                ),
            )
            n = build_and_persist_snapshots(
                games=games, league=league,
                k_factor=params.k_factor, home_advantage=params.home_advantage,
                output_path=cache_path,
            )
            logger.info(
                "Basketball ratings built: %s — %d takım, %d maç",
                league, n, len(games),
            )
        except Exception as exc:  # noqa: BLE001 — infra boundary
            logger.warning(
                "Basketball ratings build skipped %s: %s", league, exc,
            )


def _maybe_invoke_basketball_refresh(cfg: AppConfig) -> None:
    """Basketball aktif iken refresh hook çağır.

    Lig-bazlı kaynak dispatch:
      NBA / WNBA       → nba_api primary, ESPN secondary
      NCAAB / WNCAAB   → ESPN primary (nba_api college yok), secondary yok
      Euroleague       → euroleague_api primary (Faz 3 wiring), secondary yok
    """
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    enabled = [lg for lg in cfg.basketball.enabled_leagues if lg in tags_lc]
    if not enabled:
        logger.info("basketball refresh skipped — no enabled league in whitelist")
        return
    from datetime import datetime, timezone  # noqa: PLC0415

    import requests  # noqa: PLC0415

    from src.infrastructure.data.basketball.espn_pbp_refresher import (  # noqa: PLC0415
        fetch_game_log_via_espn,
    )
    from src.infrastructure.data.basketball.refresh_runner import (  # noqa: PLC0415
        BasketballRefreshRunner,
    )

    health_path = Path(cfg.basketball.health_file)
    today = datetime.now(timezone.utc).date().isoformat()

    for league in enabled:
        primary_fetch, secondary_fetch = _make_basketball_fetchers(
            league=league, date_utc=today, http_get=requests.get,
            espn_fetcher=fetch_game_log_via_espn,
        )

        runner = BasketballRefreshRunner(
            league=league, health_path=health_path,
            primary_fetch=primary_fetch, secondary_fetch=secondary_fetch,
            now_utc_str=lambda: datetime.now(timezone.utc).isoformat(),
        )
        outcome = runner.run()
        logger.info(
            "basketball refresh: league=%s source=%s games=%d",
            league, outcome.source_used, len(outcome.games),
        )
