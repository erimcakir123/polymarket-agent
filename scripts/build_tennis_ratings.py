"""CSV cache → tennis_ratings.json build script.

Orchestration: infra (CSV load) → domain (aggregate + Glicko) → infra (JSON write).
Hook'tan çağrılır (factory._maybe_invoke_sackmann_refresh).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from src.domain.pricing.tennis.glicko import Rating, update_rating
from src.domain.pricing.tennis.serve_metrics import aggregate_serve_stats
from src.infrastructure.data.sackmann_csv_loader import load_matches_from_path
from src.infrastructure.data.tennis_ratings_store import (
    PlayerSnapshot,
    save_ratings,
)

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("data/sackmann_cache")
_DEFAULT_OUTPUT = Path("data/tennis_ratings.json")


def build_ratings(cache_dir: Path, output_path: Path) -> None:
    """All CSVs in cache_dir → aggregate stats + Glicko loop → save JSON."""
    csv_files = sorted(Path(cache_dir).glob("*.csv"))
    all_matches = []
    for csv in csv_files:
        try:
            all_matches.extend(load_matches_from_path(csv))
        except OSError as exc:
            logger.warning("CSV load failed: %s (%s)", csv, exc)
    if not all_matches:
        logger.warning("No matches loaded from %s", cache_dir)
        return

    all_matches.sort(key=lambda m: m.tourney_date)
    logger.info("Building ratings from %d matches", len(all_matches))

    serve_stats = aggregate_serve_stats(all_matches)
    ratings: dict[str, Rating] = defaultdict(Rating)
    for m in all_matches:
        w = ratings[m.winner_name]
        loser_r = ratings[m.loser_name]
        ratings[m.winner_name] = update_rating(w, [loser_r], [1.0])
        ratings[m.loser_name] = update_rating(loser_r, [w], [0.0])

    serve_by_player: dict[str, dict] = defaultdict(dict)
    for (player, surface), stats in serve_stats.items():
        serve_by_player[player][surface] = stats

    snapshot = {
        name: PlayerSnapshot(rating=r, serve_by_surface=serve_by_player.get(name, {}))
        for name, r in ratings.items()
    }
    save_ratings(snapshot, output_path)
    logger.info("Saved %d player ratings to %s", len(snapshot), output_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_ratings(_DEFAULT_CACHE_DIR, _DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
