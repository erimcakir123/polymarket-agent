"""CSV cache → tennis_ratings.json build script.

Orchestration: infra (CSV load) → domain (aggregate + Glicko) → infra (JSON write).
Hook'tan çağrılır (factory._maybe_invoke_sackmann_refresh).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from src.domain.pricing.tennis.glicko import fit_ratings
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import aggregate_serve_stats
from src.domain.pricing.tennis.surface_map import build_surface_map
from src.infrastructure.data.sackmann_csv_loader import load_matches_from_path
from src.infrastructure.data.tennis_ratings_store import save_ratings
from src.infrastructure.data.tennis_surface_map_store import save_surface_map
from src.infrastructure.data.tennis_surface_ratings_store import save_all_surfaces

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("data/sackmann_cache")
_DEFAULT_OUTPUT = Path("data/tennis_ratings.json")
_DEFAULT_SURFACE_OUTPUT = Path("data/tennis_ratings_surface.json")
_VALID_SURFACES = ("Hard", "Clay", "Grass")


def build_ratings(
    cache_dir: Path,
    output_path: Path,
    surface_output_path: Path = _DEFAULT_SURFACE_OUTPUT,
) -> None:
    """CSV cache → TEK veri fotoğrafından HEM genel HEM yüzeye-özgü reytingler.

    PLAN-DATA1: iki dosya aynı anda kurulur (homojenlik) — eskiden yüzey dosyası
    ayrı lab scriptiyle elle kuruluyordu ve bayatlıyordu (2026-06-02'de kalmıştı).
    """
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

    surface_map = build_surface_map(all_matches)
    save_surface_map(surface_map, Path(output_path).parent / "tennis_surface_map.json")
    logger.info("Saved surface map (%d tournaments)", len(surface_map))

    all_matches.sort(key=lambda m: m.tourney_date)
    logger.info("Building ratings from %d matches", len(all_matches))

    serve_stats = aggregate_serve_stats(all_matches)
    ratings = fit_ratings([(m.winner_name, m.loser_name) for m in all_matches])

    serve_by_player: dict[str, dict] = defaultdict(dict)
    for (player, surface), stats in serve_stats.items():
        serve_by_player[player][surface] = stats

    snapshot = {
        name: PlayerSnapshot(rating=r, serve_by_surface=serve_by_player.get(name, {}))
        for name, r in ratings.items()
    }
    save_ratings(snapshot, output_path)
    logger.info("Saved %d player ratings to %s", len(snapshot), output_path)

    by_surface = {
        surf: fit_ratings([
            (m.winner_name, m.loser_name) for m in all_matches if m.surface == surf
        ])
        for surf in _VALID_SURFACES
    }
    save_all_surfaces(ratings, by_surface, dict(serve_by_player), surface_output_path)
    logger.info(
        "Saved surface ratings to %s (Hard=%d Clay=%d Grass=%d)",
        surface_output_path,
        len(by_surface["Hard"]), len(by_surface["Clay"]), len(by_surface["Grass"]),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_ratings(_DEFAULT_CACHE_DIR, _DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
