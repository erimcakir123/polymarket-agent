"""Build Glicko-2 player ratings from Sackmann match history.

Offline batch: read CSV → chronological match list → update ratings iteratively → save to JSON.

Run:
    python scripts/build_tennis_ratings.py

Reads config from config_tennis.yaml > tennis.sackmann_years (main draw + challenger)
and tennis.sackmann_atp_itf_years / sackmann_wta_itf_years (ITF Futures).

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


# Per-tour match weight by source tier. Main draw + Challenger reliable (1.0);
# ITF Futures lower-skill, downweight 50%. Scale-blend approach (not standard
# Glicko-2 partial-update math) — pragmatic dilution of low-tier signal.
_DEFAULT_ITF_WEIGHT = 0.5


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
        # Split main-draw vs ITF for tier-A classifier (singles only here; doubles
        # populated by the doubles pipeline in a later task).
        "match_dates_main": [],
        "match_dates_itf": [],
    }


def _surface_key(surface: str) -> str:
    s = surface.lower()
    if "clay" in s:
        return "clay"
    if "grass" in s:
        return "grass"
    return "hard"


def build_ratings_from_matches(
    atp_main: list[SackmannMatch],
    wta_main: list[SackmannMatch],
    snapshot_date: datetime,
    *,
    atp_itf: list[SackmannMatch] | None = None,
    wta_itf: list[SackmannMatch] | None = None,
    tau: float = 0.5,
    itf_weight: float = _DEFAULT_ITF_WEIGHT,
) -> dict[str, PlayerRating]:
    """Build ratings dict for ATP + WTA, optionally mixing in ITF Futures.

    Keys are tour-prefixed (atp:Name / wta:Name). Per-tour processing:
      1. Main-draw matches feed Glicko updates at weight 1.0.
      2. ITF matches feed Glicko updates at weight `itf_weight` (default 0.5).

    Each tour's ratings are computed independently — no cross-tour matches feed
    into the same player profile (Williams in ATP and WTA are different entities).

    Returns:
        dict mapping "{tour}:{player_name}" → PlayerRating(tour=...)
    """
    atp_itf = atp_itf or []
    wta_itf = wta_itf or []
    output: dict[str, PlayerRating] = {}
    for tour, main_matches, itf_matches in (
        ("atp", atp_main, atp_itf),
        ("wta", wta_main, wta_itf),
    ):
        per_tour = _build_single_tour(
            main_matches=main_matches,
            itf_matches=itf_matches,
            snapshot_date=snapshot_date,
            tau=tau,
            itf_weight=itf_weight,
        )
        for name, rating in per_tour.items():
            output[f"{tour}:{name}"] = PlayerRating(
                player_id=f"{tour}:{name}",
                player_name=name,
                tour=tour,
                overall=rating.overall,
                serve_clay=rating.serve_clay,
                serve_grass=rating.serve_grass,
                serve_hard=rating.serve_hard,
                return_clay=rating.return_clay,
                return_grass=rating.return_grass,
                return_hard=rating.return_hard,
                last_match_date=rating.last_match_date,
                singles_main_count_12mo=rating.singles_main_count_12mo,
                singles_itf_count_12mo=rating.singles_itf_count_12mo,
                doubles_count_12mo=rating.doubles_count_12mo,
            )
    return output


def _build_single_tour(
    main_matches: list[SackmannMatch],
    itf_matches: list[SackmannMatch],
    snapshot_date: datetime,
    tau: float,
    itf_weight: float,
) -> dict[str, PlayerRating]:
    """Per-tour ratings: main matches weight 1.0, ITF matches weight `itf_weight`."""
    if not main_matches and not itf_matches:
        return {}

    profiles: dict[str, dict] = {}
    # Merge with weight annotation, sort chronologically
    weighted: list[tuple[SackmannMatch, float]] = (
        [(m, 1.0) for m in main_matches] + [(m, itf_weight) for m in itf_matches]
    )
    weighted.sort(key=lambda pair: pair[0].match_date)

    for m, weight in weighted:
        winner = m.winner_name
        loser = m.loser_name
        if not winner or not loser:
            continue
        surface_key = _surface_key(m.surface)

        if winner not in profiles:
            profiles[winner] = _new_player()
        if loser not in profiles:
            profiles[loser] = _new_player()

        # Weighted Glicko-2 update via scale-blend.
        _apply_weighted_update(profiles[winner], profiles[loser], "overall", tau, weight, winner_won=True)
        _apply_weighted_update(profiles[loser], profiles[winner], "overall", tau, weight, winner_won=False)

        serve_key = f"serve_{surface_key}"
        _apply_weighted_update(profiles[winner], profiles[loser], serve_key, tau, weight, winner_won=True)
        _apply_weighted_update(profiles[loser], profiles[winner], serve_key, tau, weight, winner_won=False)

        return_key = f"return_{surface_key}"
        _apply_weighted_update(profiles[winner], profiles[loser], return_key, tau, weight, winner_won=True)
        _apply_weighted_update(profiles[loser], profiles[winner], return_key, tau, weight, winner_won=False)

        profiles[winner]["last_match_date"] = m.match_date
        profiles[loser]["last_match_date"] = m.match_date
        # weight == 1.0 → main draw / Challenger; weight < 1.0 → ITF Futures.
        bucket = "match_dates_main" if weight >= 1.0 else "match_dates_itf"
        profiles[winner][bucket].append(m.match_date)
        profiles[loser][bucket].append(m.match_date)

    cutoff = snapshot_date - timedelta(days=365)
    output: dict[str, PlayerRating] = {}
    for name, p in profiles.items():
        main_12mo = sum(1 for d in p["match_dates_main"] if d >= cutoff)
        itf_12mo = sum(1 for d in p["match_dates_itf"] if d >= cutoff)
        last_date = p["last_match_date"]
        output[name] = PlayerRating(
            player_id=name,
            player_name=name,
            tour="atp",  # placeholder — caller overwrites with correct tour
            overall=_glicko_to_surface(p["overall"]),
            serve_clay=_glicko_to_surface(p["serve_clay"]),
            serve_grass=_glicko_to_surface(p["serve_grass"]),
            serve_hard=_glicko_to_surface(p["serve_hard"]),
            return_clay=_glicko_to_surface(p["return_clay"]),
            return_grass=_glicko_to_surface(p["return_grass"]),
            return_hard=_glicko_to_surface(p["return_hard"]),
            last_match_date=last_date.strftime("%Y-%m-%d") if last_date else "1970-01-01",
            singles_main_count_12mo=main_12mo,
            singles_itf_count_12mo=itf_12mo,
            doubles_count_12mo=0,  # populated by doubles pipeline in a later task
        )
    return output


def _apply_weighted_update(
    player_profile: dict,
    opponent_profile: dict,
    rating_key: str,
    tau: float,
    weight: float,
    *,
    winner_won: bool,
) -> None:
    """In-place weighted Glicko update — blends full-update result with old rating by weight.

    weight=1.0 → full standard Glicko-2 update applied.
    weight<1.0 → scale-blend: new = old + weight * (full_update - old). This is NOT
    the standard Glicko-2 partial-update math, but a pragmatic dilution of lower-tier
    signal (e.g. ITF Futures vs main draw).
    """
    old = player_profile[rating_key]
    opp = opponent_profile[rating_key]
    score = 1.0 if winner_won else 0.0
    full_new = update_rating(old, [(opp, score)], tau=tau)
    if weight >= 1.0:
        player_profile[rating_key] = full_new
        return
    player_profile[rating_key] = Glicko2Rating(
        rating=old.rating + weight * (full_new.rating - old.rating),
        rd=old.rd + weight * (full_new.rd - old.rd),
        volatility=old.volatility + weight * (full_new.volatility - old.volatility),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config(Path("config_tennis.yaml"))
    sackmann_dir = Path(cfg.tennis.data_dir)
    ratings_path = Path(cfg.tennis.ratings_cache)

    client = SackmannCsvClient(cache_dir=sackmann_dir)
    atp_main_loaded = client.load_years(cfg.tennis.sackmann_years)
    atp_chall = client.load_challenger_years(cfg.tennis.challenger_years)
    atp_main = sorted(atp_main_loaded + atp_chall, key=lambda m: m.match_date)
    wta_main = client.load_wta_years(cfg.tennis.sackmann_wta_years)
    atp_itf = client.load_itf_years("atp", cfg.tennis.sackmann_atp_itf_years)
    wta_itf = client.load_itf_years("wta", cfg.tennis.sackmann_wta_itf_years)
    logger.info(
        "Loaded %d ATP main (%d + %d chall) + %d WTA main + %d ATP ITF + %d WTA ITF matches",
        len(atp_main), len(atp_main_loaded), len(atp_chall),
        len(wta_main), len(atp_itf), len(wta_itf),
    )

    snapshot_date = datetime.utcnow()
    ratings = build_ratings_from_matches(
        atp_main=atp_main, wta_main=wta_main,
        atp_itf=atp_itf, wta_itf=wta_itf,
        snapshot_date=snapshot_date, tau=cfg.tennis.glicko_tau,
    )
    logger.info("Built ratings for %d player-tour entries", len(ratings))

    store = TennisRatingsStore(path=ratings_path)
    store.save(ratings)
    logger.info("Saved ratings to %s", ratings_path)


if __name__ == "__main__":
    main()
