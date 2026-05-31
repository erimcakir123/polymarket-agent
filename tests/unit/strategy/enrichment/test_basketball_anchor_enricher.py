"""Basketball anchor enricher — model → BookmakerProbability sarmalı."""
from __future__ import annotations

from src.domain.analysis.enrich_outcome import EnrichFailReason
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
