"""Tennis predictor — orchestrates Glicko + Klaassen-Magnus + features.

3 markets: First Set Winner, Set Handicap -1.5, Total Sets Under 2.5

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §5
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.prediction.feature_extractor import FeatureSnapshot
from src.domain.prediction.glicko2 import Glicko2Rating
from src.domain.prediction.klaassen_magnus import (
    match_win_prob_bo3,
    set_win_prob,
)

# Point-win-on-serve baseline (tennis avg)
_BASELINE_SERVE_POINT_WIN = 0.60
# Glicko diff sensitivity for point win prob
_POINT_WIN_SENSITIVITY = 200.0
# Form bonus: |form_diff| × this = prediction shift
_FORM_BONUS = 0.05
# H2H surface bonus
_H2H_SURFACE_BONUS = 0.05
# Min/max prediction clamp
_MIN_PROB = 0.05
_MAX_PROB = 0.95


@dataclass(frozen=True)
class PlayerSurfaceProfile:
    """Player's serve + return ratings for a specific surface."""

    serve: Glicko2Rating
    return_: Glicko2Rating


@dataclass(frozen=True)
class MarketPrediction:
    """Single market prediction result."""

    market_type: str    # "first_set_winner" | "set_handicap_minus_1_5" | "total_sets_under_2_5"
    probability: float
    raw_probability: float  # before feature adjustments
    notes: str          # diagnostic explanation


def _point_win_on_serve(server_serve_rating: float, returner_return_rating: float) -> float:
    """Map Glicko rating diff to point-win-on-serve probability.

    Baseline 60% (tennis average), shifted by rating diff.
    """
    delta = server_serve_rating - returner_return_rating
    # Sigmoid-like adjustment: ±300 Glicko = ±15% point win shift
    shift = 0.3 * math.tanh(delta / _POINT_WIN_SENSITIVITY)
    return max(_MIN_PROB, min(_MAX_PROB, _BASELINE_SERVE_POINT_WIN + shift))


def _apply_feature_adjustments(
    base_prob: float, features: FeatureSnapshot,
) -> tuple[float, str]:
    """Apply form + H2H adjustments to base prediction.

    Returns (adjusted_prob, notes_string).
    """
    adjusted = base_prob
    notes: list[str] = []

    # Form bonus: p1 better form → boost
    form_diff = features.p1_form_w_pct_60d - features.p2_form_w_pct_60d
    form_adj = _FORM_BONUS * form_diff
    if abs(form_adj) > 0.005:
        adjusted += form_adj
        notes.append(f"form_adj={form_adj:+.3f}")

    # H2H bonus (same surface)
    if features.h2h_matches_same_surface >= 1:
        h2h_p1_pct = (
            features.h2h_p1_wins / features.h2h_matches_total
            if features.h2h_matches_total > 0 else 0.5
        )
        h2h_adj = _H2H_SURFACE_BONUS * (h2h_p1_pct - 0.5) * 2.0
        # Apply only if recent (< 2 years)
        if features.h2h_last_meeting_days_ago is None or features.h2h_last_meeting_days_ago < 730:
            adjusted += h2h_adj
            notes.append(f"h2h_adj={h2h_adj:+.3f}")

    adjusted = max(_MIN_PROB, min(_MAX_PROB, adjusted))
    return adjusted, "; ".join(notes)


def predict_first_set_winner(
    p1: PlayerSurfaceProfile,
    p2: PlayerSurfaceProfile,
    features: FeatureSnapshot,
) -> MarketPrediction:
    """P(p1 wins first set)."""
    p1_pt = _point_win_on_serve(p1.serve.rating, p2.return_.rating)
    p2_pt = _point_win_on_serve(p2.serve.rating, p1.return_.rating)
    base = set_win_prob(p1_pt, p2_pt)
    adjusted, notes = _apply_feature_adjustments(base, features)
    return MarketPrediction(
        market_type="first_set_winner",
        probability=adjusted,
        raw_probability=base,
        notes=notes,
    )


def predict_set_handicap_minus_1_5(
    p1: PlayerSurfaceProfile,
    p2: PlayerSurfaceProfile,
    features: FeatureSnapshot,
) -> MarketPrediction:
    """P(p1 wins 2-0 in BO3)."""
    p1_pt = _point_win_on_serve(p1.serve.rating, p2.return_.rating)
    p2_pt = _point_win_on_serve(p2.serve.rating, p1.return_.rating)
    p_set = set_win_prob(p1_pt, p2_pt)
    # P(2-0) = P(win set 1) × P(win set 2 | won set 1)
    # Momentum bonus: winner of set 1 slightly favored in set 2
    p_set2 = min(_MAX_PROB, p_set + 0.05)
    base = p_set * p_set2
    adjusted, notes = _apply_feature_adjustments(base, features)
    return MarketPrediction(
        market_type="set_handicap_minus_1_5",
        probability=adjusted,
        raw_probability=base,
        notes=notes,
    )


def predict_total_sets_under_2_5(
    p1: PlayerSurfaceProfile,
    p2: PlayerSurfaceProfile,
    features: FeatureSnapshot,
) -> MarketPrediction:
    """P(match ends in 2 sets) = P(p1 wins 2-0) + P(p2 wins 2-0)."""
    p1_pt_p1 = _point_win_on_serve(p1.serve.rating, p2.return_.rating)
    p2_pt_p1 = _point_win_on_serve(p2.serve.rating, p1.return_.rating)
    p_set_p1 = set_win_prob(p1_pt_p1, p2_pt_p1)
    p_set2_p1 = min(_MAX_PROB, p_set_p1 + 0.05)
    p_p1_2_0 = p_set_p1 * p_set2_p1

    p_set_p2 = 1.0 - p_set_p1  # symmetric
    p_set2_p2 = min(_MAX_PROB, p_set_p2 + 0.05)
    p_p2_2_0 = p_set_p2 * p_set2_p2

    base = p_p1_2_0 + p_p2_2_0
    # Form/H2H affects which side wins straight sets but not whether match ends in 2
    return MarketPrediction(
        market_type="total_sets_under_2_5",
        probability=max(_MIN_PROB, min(_MAX_PROB, base)),
        raw_probability=base,
        notes=f"p_p1_2_0={p_p1_2_0:.3f}, p_p2_2_0={p_p2_2_0:.3f}",
    )
