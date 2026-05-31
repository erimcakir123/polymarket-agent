"""Match pricer — market_type dispatch → P(YES)."""
from __future__ import annotations
import pytest
from src.domain.pricing.basketball.team_elo import EloRating
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.match_pricer import compute_market_anchor


def test_moneyline_returns_elo_blended_probability():
    home_elo = EloRating(rating=1600.0)
    away_elo = EloRating(rating=1400.0)
    home_eff = TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0)
    away_eff = TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0)
    p = compute_market_anchor(
        market_type="moneyline",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=100.0, blend_elo=0.55, line=None,
    )
    assert p is not None
    assert p > 0.7  # güçlü ev sahibi


def test_totals_over_returns_probability_above_half_when_pace_high():
    home_elo = EloRating(rating=1500.0)
    away_elo = EloRating(rating=1500.0)
    fast = TeamEfficiency(adj_o=115.0, adj_d=110.0, adj_pace=105.0)
    p_over = compute_market_anchor(
        market_type="totals",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=fast, away_eff=fast,
        home_advantage=0.0, blend_elo=0.55, line=215.0,
    )
    assert p_over is not None
    # proj_total ≈ 105 * 225 / 200 * 2 ≈ 236 > 215 → P(over) > 0.5
    assert p_over > 0.5


def test_unknown_market_type_returns_none():
    home_elo = EloRating()
    away_elo = EloRating()
    eff = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    p = compute_market_anchor(
        market_type="player_props",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=eff, away_eff=eff,
        home_advantage=0.0, blend_elo=0.55, line=None,
    )
    assert p is None


def test_spreads_home_favorite_covers_likely_when_margin_exceeds_line():
    home_elo = EloRating(rating=1600.0)
    away_elo = EloRating(rating=1400.0)
    strong = TeamEfficiency(adj_o=120.0, adj_d=105.0, adj_pace=100.0)
    weak = TeamEfficiency(adj_o=105.0, adj_d=120.0, adj_pace=100.0)
    # spread line = -3.5 (home favored by 3.5) — beklenen margin ~15 > 3.5
    p = compute_market_anchor(
        market_type="spreads",
        home_elo=home_elo, away_elo=away_elo,
        home_eff=strong, away_eff=weak,
        home_advantage=0.0, blend_elo=0.55, line=-3.5,
    )
    assert p is not None
    assert p > 0.6  # home covers
