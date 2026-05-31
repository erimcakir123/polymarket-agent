"""Team Elo — update, home advantage, win probability."""
from __future__ import annotations
import pytest
from src.domain.pricing.basketball.team_elo import (
    EloRating, expected_win_prob, update_elo, DEFAULT_RATING,
)


def test_default_rating_equals_1500():
    r = EloRating()
    assert r.rating == DEFAULT_RATING
    assert r.games == 0


def test_expected_win_prob_equal_ratings_returns_half():
    home = EloRating(rating=1500.0)
    away = EloRating(rating=1500.0)
    p = expected_win_prob(home, away, home_advantage=0.0)
    assert abs(p - 0.5) < 1e-6


def test_expected_win_prob_home_advantage_boosts_home():
    home = EloRating(rating=1500.0)
    away = EloRating(rating=1500.0)
    p = expected_win_prob(home, away, home_advantage=100.0)
    assert p > 0.5  # home ev avantaji -> daha yuksek


def test_expected_win_prob_higher_rating_wins_more():
    strong = EloRating(rating=1600.0)
    weak = EloRating(rating=1400.0)
    p = expected_win_prob(strong, weak, home_advantage=0.0)
    assert p > 0.7  # 200 puan fark -> guclu %75+ favori


def test_update_elo_winner_gains_loser_loses():
    home = EloRating(rating=1500.0, games=10)
    away = EloRating(rating=1500.0, games=10)
    new_home, new_away = update_elo(
        home, away, home_won=True, k_factor=20.0, home_advantage=0.0,
    )
    assert new_home.rating > home.rating
    assert new_away.rating < away.rating
    # Sum-zero check (klasik Elo)
    assert abs((new_home.rating + new_away.rating) - (home.rating + away.rating)) < 1e-6
    assert new_home.games == 11
    assert new_away.games == 11


def test_update_elo_upset_larger_swing():
    """Underdog'un kazanmasi -> buyuk rating hareketi."""
    strong = EloRating(rating=1700.0, games=20)
    weak = EloRating(rating=1300.0, games=20)
    # Beklenti: strong %91 favori. Eger weak kazanirsa -> buyuk swing.
    new_strong, new_weak = update_elo(
        strong, weak, home_won=False, k_factor=20.0, home_advantage=0.0,
    )
    swing = new_weak.rating - weak.rating
    assert swing > 15  # Klasik Elo: K * (1 - expected) ~ 20 * 0.91 = 18.2
