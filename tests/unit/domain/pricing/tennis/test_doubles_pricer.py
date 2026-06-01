"""Doubles match pricer — partner rating birleştirme + singles pricer wraparound."""
from __future__ import annotations

from src.domain.pricing.tennis.doubles_pricer import (
    DoublesTeam,
    combine_partner_ratings,
    price_doubles_h2h,
)
from src.domain.pricing.tennis.glicko import Rating


def test_combine_partner_ratings_averages_mu():
    """İki oyuncunun rating'i average — basit doubles modeli."""
    p1 = Rating(mu=1600.0, phi=80.0, sigma=0.06)
    p2 = Rating(mu=1400.0, phi=80.0, sigma=0.06)
    team = combine_partner_ratings(p1, p2)
    assert abs(team.mu - 1500.0) < 0.1


def test_combine_partner_ratings_phi_combined_not_average():
    """Doubles takım phi sqrt(phi_a^2 + phi_b^2) / 2 — combined uncertainty."""
    p = Rating(mu=1500.0, phi=80.0, sigma=0.06)
    team = combine_partner_ratings(p, p)
    # sqrt(80^2 + 80^2) / 2 = sqrt(12800)/2 = ~56.57
    assert abs(team.phi - 56.57) < 0.5


def test_price_doubles_strong_team_wins_more():
    strong = DoublesTeam(rating=Rating(mu=1700.0, phi=70.0, sigma=0.06))
    weak = DoublesTeam(rating=Rating(mu=1300.0, phi=70.0, sigma=0.06))
    p = price_doubles_h2h(strong, weak)
    assert p > 0.7


def test_price_doubles_equal_teams_returns_half():
    eq = DoublesTeam(rating=Rating(mu=1500.0, phi=70.0, sigma=0.06))
    p = price_doubles_h2h(eq, eq)
    assert abs(p - 0.5) < 0.05
