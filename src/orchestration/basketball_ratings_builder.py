"""Basketball ratings builder — bot başlangıçta NBA/WNBA için bulk Elo + Efficiency hesabı.

Sackmann pattern paralel (build_tennis_ratings.py muadili). Akış:
  1. nba_api / ESPN üzerinden mevcut sezon game-log delta-fetch
  2. Tarihsel sırayla maçları iterate
  3. Her maç: Elo update + Efficiency hesabı (compute_team_efficiency)
  4. team_ratings_store cache'ine yaz

Bot reboot'unda factory.py'dan opsiyonel çağrılır — başarısızlık degrade
(basketball_dispatch ratings boş bulursa bookmaker fallback).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.domain.pricing.basketball.efficiency_metrics import (
    compute_team_efficiency,
)
from src.domain.pricing.basketball.season_reset import revert_to_mean
from src.domain.pricing.basketball.team_elo import (
    EloRating, update_elo,
)
from src.infrastructure.data.basketball.schemas import (
    GameRecord, TeamSnapshot,
)
from src.infrastructure.data.basketball.team_ratings_store import (
    save_team_snapshots,
)

logger = logging.getLogger(__name__)


def build_ratings_from_games(
    games: list[GameRecord],
    league: str,
    k_factor: float,
    home_advantage: float,
    apply_season_reset: bool = False,
) -> tuple[dict[str, EloRating], dict[str, int]]:
    """Tarihsel maç listesinden Elo + maç sayısı hesapla (kronolojik iter).

    Returns: (elo_by_team, games_count_by_team).
    """
    elo: dict[str, EloRating] = defaultdict(EloRating)
    sorted_games = sorted(games, key=lambda g: g.game_date_utc)
    for g in sorted_games:
        if g.league != league:
            continue
        home_elo = elo[g.home_team]
        away_elo = elo[g.away_team]
        home_won = g.home_score > g.away_score
        new_home, new_away = update_elo(
            home_elo, away_elo, home_won=home_won,
            k_factor=k_factor, home_advantage=home_advantage,
        )
        elo[g.home_team] = new_home
        elo[g.away_team] = new_away
    if apply_season_reset:
        elo = {team: revert_to_mean(rating) for team, rating in elo.items()}
    games_count = {team: rating.games for team, rating in elo.items()}
    return dict(elo), games_count


def build_and_persist_snapshots(
    games: list[GameRecord],
    league: str,
    k_factor: float,
    home_advantage: float,
    output_path: Path,
    apply_season_reset: bool = False,
) -> int:
    """Game listesi → ratings + efficiencies → JSON cache. Returns yazılan sayısı."""
    if not games:
        logger.info("basketball_ratings_builder: %s — no games, skip", league)
        return 0
    elo, _ = build_ratings_from_games(
        games, league, k_factor, home_advantage,
        apply_season_reset=apply_season_reset,
    )
    snapshots: list[TeamSnapshot] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for team, rating in elo.items():
        eff = compute_team_efficiency(games, team)
        if eff is None:
            continue
        snapshots.append(TeamSnapshot(
            team=team, league=league,  # type: ignore[arg-type]
            elo_rating=rating.rating, elo_games=rating.games,
            adj_o=eff.adj_o, adj_d=eff.adj_d, adj_pace=eff.adj_pace,
            last_updated_utc=now_iso,
        ))
    if snapshots:
        save_team_snapshots(output_path, snapshots)
        logger.info(
            "basketball_ratings_builder: %s — %d snapshots saved to %s",
            league, len(snapshots), output_path,
        )
    return len(snapshots)


def refresh_ratings_for_league(
    league: str,
    fetch_games: Callable[[], list[GameRecord]],
    output_dir: Path,
    k_factor: float,
    home_advantage: float,
    apply_season_reset: bool = False,
) -> Optional[int]:
    """Tek lig için: fetch + build + save. Hata → None (degrade)."""
    try:
        games = fetch_games()
    except Exception as exc:  # noqa: BLE001 — infra boundary
        logger.warning(
            "basketball_ratings_builder: fetch failed for %s — %s", league, exc,
        )
        return None
    output_path = output_dir / f"{league}_ratings.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    return build_and_persist_snapshots(
        games, league, k_factor, home_advantage, output_path,
        apply_season_reset=apply_season_reset,
    )
