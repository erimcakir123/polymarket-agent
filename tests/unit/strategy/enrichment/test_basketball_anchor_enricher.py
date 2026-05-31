"""Basketball anchor enricher — model → BookmakerProbability sarmalı."""
from __future__ import annotations

from src.domain.analysis.enrich_outcome import EnrichFailReason
from src.domain.calibration.curve import fit_calibration
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.strategy.enrichment.basketball_anchor_enricher import (
    enrich_basketball_from_model,
)


def test_enrich_complete_data_returns_a_confidence():
    ratings = {
        "LAL": EloRating(rating=1600.0, games=50),
        "GSW": EloRating(rating=1400.0, games=50),
    }
    efficiencies = {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability is not None
    assert res.probability.confidence == "A"
    assert res.fail_reason is None


def test_enrich_missing_team_returns_fail_reason():
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings={}, efficiencies={},
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability is None
    assert res.fail_reason == EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS


def test_enrich_missing_efficiency_returns_data_missing():
    ratings = {
        "LAL": EloRating(rating=1500.0),
        "GSW": EloRating(rating=1500.0),
    }
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies={},
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability is None
    assert res.fail_reason == EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING


def test_enrich_applies_calibration_curve_when_provided():
    """Model %70 dediği yerlerde gerçek %60 olan kalibrasyon → calibrated < uncalibrated."""
    preds = [0.7] * 100
    outs = [1] * 60 + [0] * 40
    curve = fit_calibration(preds, outs, n_bins=10)
    ratings = {
        "LAL": EloRating(rating=1600.0, games=50),
        "GSW": EloRating(rating=1400.0, games=50),
    }
    efficiencies = {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }
    res_uncal = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    res_cal = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
        calibration_curves={"nba:moneyline": curve},
    )
    assert res_uncal.probability is not None
    assert res_cal.probability is not None
    assert res_cal.probability.probability < res_uncal.probability.probability


def test_enrich_clips_extreme_model_output_to_95():
    """Aşırı rating farkı → model %99+ verebilir; cliprange %95'e kırp."""
    ratings = {
        "LAL": EloRating(rating=2200.0),
        "GSW": EloRating(rating=1000.0),
    }
    efficiencies = {
        "LAL": TeamEfficiency(adj_o=140.0, adj_d=80.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=80.0, adj_d=140.0, adj_pace=100.0),
    }
    res = enrich_basketball_from_model(
        home_team="LAL", away_team="GSW",
        market_type="moneyline", league="nba",
        ratings=ratings, efficiencies=efficiencies,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert res.probability is not None
    assert res.probability.probability <= 0.95
