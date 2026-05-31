"""Glicko-2: Glickman 2013 paper formülleri."""
from src.domain.pricing.tennis.glicko import (
    DEFAULT_RATING,
    DEFAULT_RD,
    DEFAULT_VOL,
    Rating,
    update_rating,
    win_probability,
)


def test_default_rating():
    r = Rating()
    assert r.mu == DEFAULT_RATING
    assert r.phi == DEFAULT_RD
    assert r.sigma == DEFAULT_VOL


def test_win_probability_equal_ratings_is_half():
    r1 = Rating()
    r2 = Rating()
    p = win_probability(r1, r2)
    assert abs(p - 0.5) < 1e-6


def test_win_probability_higher_rating_wins_more():
    strong = Rating(mu=1800, phi=50)
    weak = Rating(mu=1500, phi=50)
    assert win_probability(strong, weak) > 0.7


def test_update_after_win_increases_rating():
    r1 = Rating(mu=1500, phi=200, sigma=0.06)
    r2 = Rating(mu=1500, phi=200, sigma=0.06)
    r1_new = update_rating(r1, opponents=[r2], outcomes=[1.0])
    assert r1_new.mu > r1.mu
    assert r1_new.phi < r1.phi


def test_update_after_loss_decreases_rating():
    r1 = Rating(mu=1500, phi=200, sigma=0.06)
    r2 = Rating(mu=1500, phi=200, sigma=0.06)
    r1_new = update_rating(r1, opponents=[r2], outcomes=[0.0])
    assert r1_new.mu < r1.mu


def test_no_games_only_drifts_rd():
    r = Rating(mu=1500, phi=200, sigma=0.06)
    r_new = update_rating(r, opponents=[], outcomes=[])
    assert r_new.mu == r.mu
    assert r_new.phi >= r.phi
