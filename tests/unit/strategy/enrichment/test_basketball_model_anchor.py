"""Basketball model anchor — market type dispatch."""
from __future__ import annotations

from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.strategy.enrichment.basketball_model_anchor import compute_model_anchor


def test_moneyline_strong_home_returns_high_probability():
    home_elo = EloRating(rating=1600.0)
    away_elo = EloRating(rating=1400.0)
    home_eff = TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0)
    away_eff = TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0)
    p = compute_model_anchor(
        market_type="moneyline",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert p is not None and p > 0.7


def test_unknown_market_returns_none():
    eff = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    p = compute_model_anchor(
        market_type="alley_oop", home_elo=EloRating(), away_elo=EloRating(),
        home_eff=eff, away_eff=eff, home_advantage=0.0, blend_elo=0.55, line=None,
    )
    assert p is None


def test_totals_requires_line():
    eff = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    p = compute_model_anchor(
        market_type="totals", home_elo=EloRating(), away_elo=EloRating(),
        home_eff=eff, away_eff=eff, home_advantage=0.0, blend_elo=0.55, line=None,
    )
    assert p is None
