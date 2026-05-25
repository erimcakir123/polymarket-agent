"""Tennis market enricher — full pipeline: parse → match → features → predict → edge.

Orchestrator that takes one Polymarket MarketData and returns an EdgeCandidate (or
None for skipped/unpredictable markets).

Pipeline:
  1. Parse question → p1_name, p2_name, market_type, surface
  2. Match player names → PlayerRating objects
  3. Build PlayerSurfaceProfile from surface-specific Glicko ratings
  4. Extract features from Sackmann match history
  5. Classify confidence tier (A / B / skip)
  6. Predict via tennis_predictor
  7. Compute edge = model_p - market_p
  8. Return EdgeCandidate or None

Logging follows ARCH_GUARD Kural 13: strategy skips are NOT logged individually;
cycle summary is logged in orchestration layer.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §5
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from src.config.settings import AppConfig
from src.domain.matching.tennis_player_matcher import build_match_index, match_player
from src.domain.prediction.feature_extractor import FeatureSnapshot, extract_features
from src.domain.prediction.glicko2 import Glicko2Rating
from src.domain.prediction.tennis_predictor import (
    MarketPrediction,
    PlayerSurfaceProfile,
    predict_first_set_winner,
    predict_match_totals_over_under,
    predict_match_winner,
    predict_set_handicap_minus_1_5,
    predict_total_sets_under_2_5,
)
from src.models.market import MarketData

# SackmannMatch and PlayerRating are infrastructure types — importing them here
# would violate ARCH_GUARD Kural 1 (strategy must not import infrastructure).
# Public signatures use Any; callers (orchestration layer) pass concrete objects.
from src.strategy.enrichment.tennis_question_parser import parse_tennis_question
from src.strategy.entry.tennis_entry import EdgeCandidate

logger = logging.getLogger(__name__)


def classify_tier(
    features: FeatureSnapshot,
    cfg: AppConfig,
) -> Literal["A", "B", "skip"]:
    """Classify prediction confidence tier based on data quality.

    Tier A: both players ≥40 matches + ≥15 surface + form <60d + RD <100 + H2H ≥1
    Tier B: both ≥20 matches + ≥8 surface + form <90d + RD <150
    else: skip

    Thresholds from config.tennis.confidence_tier_a / _tier_b.
    """
    tier_a = cfg.tennis.confidence_tier_a
    tier_b = cfg.tennis.confidence_tier_b

    # Tier A check
    if (
        features.p1_match_count_12mo >= tier_a.min_matches_12mo
        and features.p2_match_count_12mo >= tier_a.min_matches_12mo
        and features.p1_surface_count >= tier_a.min_surface_matches
        and features.p2_surface_count >= tier_a.min_surface_matches
        and features.p1_form_data_age_days <= tier_a.max_form_age_days
        and features.p2_form_data_age_days <= tier_a.max_form_age_days
        and features.h2h_matches_total >= 1
    ):
        return "A"

    # Tier B check
    if (
        features.p1_match_count_12mo >= tier_b.min_matches_12mo
        and features.p2_match_count_12mo >= tier_b.min_matches_12mo
        and features.p1_surface_count >= tier_b.min_surface_matches
        and features.p2_surface_count >= tier_b.min_surface_matches
        and features.p1_form_data_age_days <= tier_b.max_form_age_days
        and features.p2_form_data_age_days <= tier_b.max_form_age_days
    ):
        return "B"

    return "skip"


def _build_surface_profile(
    rating: Any,
    surface: str,
) -> PlayerSurfaceProfile:
    """Build PlayerSurfaceProfile from PlayerRating for a given surface."""
    surface_low = surface.lower()
    if surface_low == "clay":
        serve = Glicko2Rating(
            rating=rating.serve_clay.rating,
            rd=rating.serve_clay.rd,
            volatility=rating.serve_clay.volatility,
        )
        return_ = Glicko2Rating(
            rating=rating.return_clay.rating,
            rd=rating.return_clay.rd,
            volatility=rating.return_clay.volatility,
        )
    elif surface_low == "grass":
        serve = Glicko2Rating(
            rating=rating.serve_grass.rating,
            rd=rating.serve_grass.rd,
            volatility=rating.serve_grass.volatility,
        )
        return_ = Glicko2Rating(
            rating=rating.return_grass.rating,
            rd=rating.return_grass.rd,
            volatility=rating.return_grass.volatility,
        )
    else:  # hard (default)
        serve = Glicko2Rating(
            rating=rating.serve_hard.rating,
            rd=rating.serve_hard.rd,
            volatility=rating.serve_hard.volatility,
        )
        return_ = Glicko2Rating(
            rating=rating.return_hard.rating,
            rd=rating.return_hard.rd,
            volatility=rating.return_hard.volatility,
        )
    return PlayerSurfaceProfile(serve=serve, return_=return_)


def _call_predictor(
    market_type: str,
    p1_profile: PlayerSurfaceProfile,
    p2_profile: PlayerSurfaceProfile,
    features: FeatureSnapshot,
) -> Optional[MarketPrediction]:
    """Route to the correct predictor function by market_type."""
    if market_type == "first_set_winner":
        return predict_first_set_winner(p1_profile, p2_profile, features)
    if market_type == "set_handicap_minus_1_5":
        return predict_set_handicap_minus_1_5(p1_profile, p2_profile, features)
    if market_type == "total_sets_under_2_5":
        return predict_total_sets_under_2_5(p1_profile, p2_profile, features)
    if market_type == "match_winner":
        return predict_match_winner(p1_profile, p2_profile, features)
    if market_type == "match_totals_over_under":
        return predict_match_totals_over_under(p1_profile, p2_profile, features)
    return None


def enrich(
    market: MarketData,
    ratings: dict[str, Any],
    sackmann_matches: list[Any],
    cfg: AppConfig,
    snapshot_date: Optional[datetime] = None,
) -> Optional[EdgeCandidate]:
    """Full enrichment pipeline for one MarketData.

    Args:
        market: Polymarket market to evaluate.
        ratings: Player ratings dict (player_id → PlayerRating).
        sackmann_matches: Historical match list for feature extraction.
        cfg: AppConfig (reads edge.min_edge, tennis.confidence_tier_*).
        snapshot_date: Override "now" for feature extraction (test injection).

    Returns:
        EdgeCandidate if edge qualifies, else None.

    Note: name-match indexes are rebuilt per call (tour-scoped — they differ
    per tour so cannot be reused across all markets). The perf cost is
    negligible (small dicts) compared to feature extraction.
    """
    now = snapshot_date or datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC

    # Step 1: Parse question → structured fields
    parsed = parse_tennis_question(
        question=market.question,
        sports_market_type=market.sports_market_type,
        slug=market.slug or "",
    )
    if parsed is None:
        return None  # unsupported market type or unparseable

    p1_name: str = parsed["p1_name"]
    p2_name: str = parsed["p2_name"]
    market_type: str = parsed["market_type"]
    surface: str = parsed["surface"]
    tour: str = parsed["tour"]

    # Step 2: Match player names → PlayerRating (tour-scoped to avoid cross-tour collision)
    by_full, by_last = build_match_index(ratings, tour=tour)

    p1_rating = match_player(p1_name, ratings, by_full=by_full, by_last=by_last, tour=tour)
    p2_rating = match_player(p2_name, ratings, by_full=by_full, by_last=by_last, tour=tour)
    if p1_rating is None or p2_rating is None:
        return None  # one or both players not in ratings cache

    # Step 3: Build surface profiles
    p1_profile = _build_surface_profile(p1_rating, surface)
    p2_profile = _build_surface_profile(p2_rating, surface)

    # Step 4: Extract features
    features = extract_features(
        matches=sackmann_matches,
        p1=p1_rating.player_name,
        p2=p2_rating.player_name,
        surface=surface.capitalize(),   # Sackmann uses "Clay" / "Hard" / "Grass"
        snapshot_date=now,
    )

    # Step 5: Classify confidence tier
    tier = classify_tier(features, cfg)
    if tier == "skip":
        return None

    # Data-driven (tour, market_type, confidence) exclusion — see config.edge.exclude_combos.
    # Kill-switch for bleeding combos (2026-05-26: ATP_set_totals B -$179 net).
    if tier in ("A", "B"):
        smt = market.sports_market_type or ""
        for excl in cfg.edge.exclude_combos:
            if excl.tour == tour and excl.market_type == smt and excl.confidence == tier:
                return None

    # Step 6: Predict
    prediction = _call_predictor(market_type, p1_profile, p2_profile, features)
    if prediction is None:
        return None

    # Step 7: Compute edge — P(YES) anchor always
    # market yes_price = P(YES). model probability = P(p1 wins).
    # BUY YES if model > market (positive edge); BUY NO if model < market.
    model_p = prediction.probability
    market_p = market.yes_price
    edge = model_p - market_p

    return EdgeCandidate(
        event_id=market.event_id or market.condition_id,
        market_type=market_type,
        model_p=model_p,
        market_p=market_p,
        edge=edge,
        tour=tour,
    )
