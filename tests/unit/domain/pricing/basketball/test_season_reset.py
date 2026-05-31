"""Sezon başı rating reset — FiveThirtyEight paterni (%25 mean reversion)."""
from __future__ import annotations

from src.domain.pricing.basketball.season_reset import (
    REVERT_FRACTION,
    revert_to_mean,
)
from src.domain.pricing.basketball.team_elo import DEFAULT_RATING, EloRating


def test_revert_to_mean_strong_team_loses_quarter():
    """%25 ortalamaya çekiş: 1700 → 1500 + 0.75 × (1700-1500) = 1650."""
    pre = EloRating(rating=1700.0, games=80)
    post = revert_to_mean(pre)
    assert abs(post.rating - 1650.0) < 0.01
    assert post.games == pre.games  # games sayacı korunur


def test_revert_to_mean_weak_team_gains_quarter():
    """1300 → 1500 - 0.75 × (1500-1300) = 1350."""
    pre = EloRating(rating=1300.0, games=80)
    post = revert_to_mean(pre)
    assert abs(post.rating - 1350.0) < 0.01


def test_revert_to_mean_average_team_unchanged():
    pre = EloRating(rating=DEFAULT_RATING, games=80)
    post = revert_to_mean(pre)
    assert abs(post.rating - DEFAULT_RATING) < 0.01


def test_revert_fraction_is_quarter():
    """FiveThirtyEight standardı: %25 reversion."""
    assert abs(REVERT_FRACTION - 0.25) < 0.001
