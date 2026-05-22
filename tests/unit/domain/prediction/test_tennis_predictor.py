"""Tennis predictor — 3 market orchestrator."""
from __future__ import annotations

import pytest

from src.domain.prediction.feature_extractor import FeatureSnapshot
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


def _profile(serve_rating: float, return_rating: float, rd: float = 80) -> PlayerSurfaceProfile:
    return PlayerSurfaceProfile(
        serve=Glicko2Rating(rating=serve_rating, rd=rd, volatility=0.06),
        return_=Glicko2Rating(rating=return_rating, rd=rd, volatility=0.06),
    )


def _features() -> FeatureSnapshot:
    return FeatureSnapshot(
        p1_name="A", p2_name="B", surface="Hard",
        p1_match_count_12mo=80, p1_surface_count=30,
        p1_form_w_pct_60d=0.60, p1_form_data_age_days=30,
        p2_match_count_12mo=50, p2_surface_count=20,
        p2_form_w_pct_60d=0.50, p2_form_data_age_days=45,
        h2h_matches_total=2, h2h_matches_same_surface=1,
        h2h_p1_wins=1, h2h_last_meeting_days_ago=200,
    )


def test_predict_first_set_winner_returns_prediction():
    p1 = _profile(serve_rating=1800, return_rating=1750)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_first_set_winner(p1, p2, _features())
    assert isinstance(pred, MarketPrediction)
    assert 0.0 <= pred.probability <= 1.0
    # p1 stronger → should be >0.5
    assert pred.probability > 0.5


def test_predict_first_set_winner_equal_players_near_half():
    p1 = _profile(serve_rating=1700, return_rating=1700)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_first_set_winner(p1, p2, _features())
    # Equal Glicko, but form_p1=0.60 vs form_p2=0.50 → slight p1 boost
    assert 0.45 < pred.probability < 0.65


def test_predict_set_handicap_uses_p1_2_0():
    p1 = _profile(serve_rating=1800, return_rating=1750)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_set_handicap_minus_1_5(p1, p2, _features())
    # P(p1 wins 2-0 in BO3) < P(p1 wins first set)
    fs_pred = predict_first_set_winner(p1, p2, _features())
    assert pred.probability < fs_pred.probability


def test_predict_total_sets_under_2_5_close_match_low_prob():
    # Equal players → close match → goes to 3 sets often → under 2.5 unlikely
    p1 = _profile(serve_rating=1700, return_rating=1700)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_total_sets_under_2_5(p1, p2, _features())
    assert pred.probability < 0.6


def test_predict_total_sets_under_2_5_dominant_player_high_prob():
    # Big rating diff → straight sets likely → under 2.5 high
    p1 = _profile(serve_rating=2000, return_rating=1900)
    p2 = _profile(serve_rating=1600, return_rating=1500)
    pred = predict_total_sets_under_2_5(p1, p2, _features())
    assert pred.probability > 0.5


# ── predict_match_winner ───────────────────────────────────────────────────────


def test_predict_match_winner_returns_prediction():
    p1 = _profile(serve_rating=1800, return_rating=1750)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_match_winner(p1, p2, _features())
    assert isinstance(pred, MarketPrediction)
    assert pred.market_type == "match_winner"
    assert 0.0 <= pred.probability <= 1.0


def test_predict_match_winner_stronger_player_above_half():
    # p1 significantly stronger → P(p1 wins match) > 0.5
    p1 = _profile(serve_rating=1900, return_rating=1850)
    p2 = _profile(serve_rating=1600, return_rating=1550)
    pred = predict_match_winner(p1, p2, _features())
    assert pred.probability > 0.5


def test_predict_match_winner_equal_players_near_half():
    p1 = _profile(serve_rating=1700, return_rating=1700)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_match_winner(p1, p2, _features())
    # Equal Glicko with slight p1 form advantage → bounded near 0.5
    assert 0.45 < pred.probability < 0.70


def test_predict_match_winner_probability_exceeds_first_set_winner():
    """Match win prob BO3 > first-set win prob for strong favourite (convexity)."""
    p1 = _profile(serve_rating=2000, return_rating=1950)
    p2 = _profile(serve_rating=1500, return_rating=1450)
    match_pred = predict_match_winner(p1, p2, _features())
    set_pred = predict_first_set_winner(p1, p2, _features())
    # For a heavy favourite: P(win match) >= P(win first set) due to BO3 compounding
    assert match_pred.probability >= set_pred.probability


# ── predict_match_totals_over_under ───────────────────────────────────────────


def test_predict_match_totals_over_under_returns_prediction():
    p1 = _profile(serve_rating=1700, return_rating=1700)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_match_totals_over_under(p1, p2, _features())
    assert isinstance(pred, MarketPrediction)
    assert pred.market_type == "match_totals_over_under"
    assert 0.0 <= pred.probability <= 1.0


def test_predict_match_totals_close_match_low_under_prob():
    """Equal players → likely 3 sets → under probability is low (< 0.6)."""
    p1 = _profile(serve_rating=1700, return_rating=1700)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    pred = predict_match_totals_over_under(p1, p2, _features())
    # P(under) = P(match ends in 2 sets) — same as total_sets_under_2_5
    assert pred.probability < 0.6


def test_predict_match_totals_dominant_player_high_under_prob():
    """Big rating diff → straight sets likely → under probability high (>0.5)."""
    p1 = _profile(serve_rating=2000, return_rating=1900)
    p2 = _profile(serve_rating=1600, return_rating=1500)
    pred = predict_match_totals_over_under(p1, p2, _features())
    assert pred.probability > 0.5


def test_predict_match_totals_agrees_with_total_sets_under_2_5():
    """match_totals_over_under P(under) == total_sets_under_2_5 probability."""
    p1 = _profile(serve_rating=1800, return_rating=1750)
    p2 = _profile(serve_rating=1700, return_rating=1700)
    feat = _features()
    totals = predict_match_totals_over_under(p1, p2, feat)
    sets = predict_total_sets_under_2_5(p1, p2, feat)
    assert abs(totals.probability - sets.probability) < 1e-9
