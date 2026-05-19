"""Build Glicko-2 player ratings from Sackmann match history.

Offline batch: read CSV → chronological match list → update ratings iteratively → save to JSON.

Run:
    python scripts/build_tennis_ratings.py

Reads config from config_tennis.yaml > tennis.sackmann_years.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §4.3
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import load_config
from src.domain.prediction.glicko2 import Glicko2Rating, update_rating
from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient, SackmannMatch
from src.infrastructure.data.tennis_ratings_store import (
    PlayerRating,
    SurfaceRating,
    TennisRatingsStore,
)

logger = logging.getLogger(__name__)


def _glicko_to_surface(g: Glicko2Rating) -> SurfaceRating:
    return SurfaceRating(rating=g.rating, rd=g.rd, volatility=g.volatility)


def _new_player() -> dict:
    """Initial profile: all 1500/350/0.06."""
    initial = Glicko2Rating(rating=1500, rd=350, volatility=0.06)
    return {
        "overall": initial,
        "serve_clay": initial, "serve_grass": initial, "serve_hard": initial,
        "return_clay": initial, "return_grass": initial, "return_hard": initial,
        "last_match_date": None,
        "match_dates": [],  # for 12mo count later
    }


def _surface_key(surface: str) -> str:
    s = surface.lower()
    if "clay" in s:
        return "clay"
    if "grass" in s:
        return "grass"
    return "hard"


def build_ratings_from_matches(
    matches: list[SackmannMatch],
    snapshot_date: datetime,
    tau: float = 0.5,
) -> dict[str, PlayerRating]:
    """Build ratings dict by walking matches chronologically.

    Each match updates winner+loser ratings (overall + surface-specific).

    Args:
        matches: list of SackmannMatch records (any order)
        snapshot_date: reference date for 12-month match count
        tau: Glicko-2 system constant controlling volatility change (0.3–1.2)

    Returns:
        dict mapping player_name → PlayerRating with overall + 6 surface ratings
    """
    if not matches:
        return {}

    profiles: dict[str, dict] = {}
    matches_sorted = sorted(matches, key=lambda m: m.match_date)

    for m in matches_sorted:
        winner = m.winner_name
        loser = m.loser_name
        if not winner or not loser:
            continue

        surface_key = _surface_key(m.surface)

        if winner not in profiles:
            profiles[winner] = _new_player()
        if loser not in profiles:
            profiles[loser] = _new_player()

        # Update overall ratings (winner=1, loser=0)
        w_overall = profiles[winner]["overall"]
        l_overall = profiles[loser]["overall"]
        profiles[winner]["overall"] = update_rating(
            w_overall, [(l_overall, 1.0)], tau=tau,
        )
        profiles[loser]["overall"] = update_rating(
            l_overall, [(w_overall, 0.0)], tau=tau,
        )

        # Update surface-specific serve ratings (proxy: winner served better)
        w_serve_key = f"serve_{surface_key}"
        l_serve_key = f"serve_{surface_key}"
        w_serve = profiles[winner][w_serve_key]
        l_serve = profiles[loser][l_serve_key]
        profiles[winner][w_serve_key] = update_rating(
            w_serve, [(l_serve, 1.0)], tau=tau,
        )
        profiles[loser][l_serve_key] = update_rating(
            l_serve, [(w_serve, 0.0)], tau=tau,
        )

        # Update surface-specific return ratings (proxy: winner returned better)
        w_return_key = f"return_{surface_key}"
        l_return_key = f"return_{surface_key}"
        w_return = profiles[winner][w_return_key]
        l_return = profiles[loser][l_return_key]
        profiles[winner][w_return_key] = update_rating(
            w_return, [(l_return, 1.0)], tau=tau,
        )
        profiles[loser][l_return_key] = update_rating(
            l_return, [(w_return, 0.0)], tau=tau,
        )

        profiles[winner]["last_match_date"] = m.match_date
        profiles[loser]["last_match_date"] = m.match_date
        profiles[winner]["match_dates"].append(m.match_date)
        profiles[loser]["match_dates"].append(m.match_date)

    # Convert to PlayerRating + compute 12mo count
    cutoff = snapshot_date - timedelta(days=365)
    output: dict[str, PlayerRating] = {}
    for name, p in profiles.items():
        count_12mo = sum(1 for d in p["match_dates"] if d >= cutoff)
        last_date = p["last_match_date"]
        output[name] = PlayerRating(
            player_id=name,
            player_name=name,
            overall=_glicko_to_surface(p["overall"]),
            serve_clay=_glicko_to_surface(p["serve_clay"]),
            serve_grass=_glicko_to_surface(p["serve_grass"]),
            serve_hard=_glicko_to_surface(p["serve_hard"]),
            return_clay=_glicko_to_surface(p["return_clay"]),
            return_grass=_glicko_to_surface(p["return_grass"]),
            return_hard=_glicko_to_surface(p["return_hard"]),
            last_match_date=last_date.strftime("%Y-%m-%d") if last_date else "1970-01-01",
            match_count_12mo=count_12mo,
        )
    return output


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config(Path("config_tennis.yaml"))
    sackmann_dir = Path(cfg.tennis.data_dir)
    ratings_path = Path(cfg.tennis.ratings_cache)

    client = SackmannCsvClient(cache_dir=sackmann_dir)
    matches = client.load_years(cfg.tennis.sackmann_years)
    logger.info("Loaded %d total matches from Sackmann", len(matches))

    snapshot_date = datetime.utcnow()
    ratings = build_ratings_from_matches(
        matches, snapshot_date=snapshot_date, tau=cfg.tennis.glicko_tau,
    )
    logger.info("Built ratings for %d players", len(ratings))

    store = TennisRatingsStore(path=ratings_path)
    store.save(ratings)
    logger.info("Saved ratings to %s", ratings_path)


if __name__ == "__main__":
    main()
