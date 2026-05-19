"""Glicko-2 math module — pure functions, no I/O.

References:
- http://www.glicko.net/glicko/glicko2.pdf (Glickman's Glicko-2 paper)
- Test values from Glickman's example (4 opponents)
"""
from __future__ import annotations

import pytest

from src.domain.prediction.glicko2 import (
    Glicko2Rating,
    expected_score,
    update_rating,
)


def test_default_rating_initializes_with_given_values():
    r = Glicko2Rating(rating=1500, rd=350, volatility=0.06)
    assert r.rating == 1500
    assert r.rd == 350


def test_expected_score_equal_rating_returns_half():
    a = Glicko2Rating(rating=1500, rd=200, volatility=0.06)
    b = Glicko2Rating(rating=1500, rd=200, volatility=0.06)
    p = expected_score(a, b)
    assert abs(p - 0.5) < 0.001


def test_expected_score_higher_rating_returns_higher_prob():
    a = Glicko2Rating(rating=1700, rd=100, volatility=0.06)
    b = Glicko2Rating(rating=1500, rd=100, volatility=0.06)
    p = expected_score(a, b)
    assert p > 0.7


def test_update_rating_winner_rating_increases():
    """Glickman's example: player 1500/200, beats 1400/30."""
    player = Glicko2Rating(rating=1500, rd=200, volatility=0.06)
    opponent = Glicko2Rating(rating=1400, rd=30, volatility=0.06)
    new_rating = update_rating(player, [(opponent, 1.0)], tau=0.5)
    assert new_rating.rating > 1500
    # RD should decrease (more certainty)
    assert new_rating.rd < 200


def test_update_rating_loser_rating_decreases():
    player = Glicko2Rating(rating=1500, rd=200, volatility=0.06)
    opponent = Glicko2Rating(rating=1800, rd=30, volatility=0.06)
    new_rating = update_rating(player, [(opponent, 0.0)], tau=0.5)
    assert new_rating.rating < 1500


def test_update_rating_inactive_period_increases_rd():
    """No matches → RD increases (uncertainty grows)."""
    player = Glicko2Rating(rating=1500, rd=200, volatility=0.06)
    new_rating = update_rating(player, [], tau=0.5)
    # Inactivity: rating same, RD grows
    assert abs(new_rating.rating - 1500) < 0.01
    assert new_rating.rd >= 200


def test_glickman_paper_three_opponent_example_matches():
    """Glickman's paper example (3 opponents) — exact match.

    Player 1500/200, opponents:
    - 1400/30 result 1.0
    - 1550/100 result 0.0
    - 1700/300 result 0.0
    Expected per paper: new_rating ≈ 1464, new_rd ≈ 152
    """
    player = Glicko2Rating(rating=1500, rd=200, volatility=0.06)
    opponents = [
        (Glicko2Rating(rating=1400, rd=30, volatility=0.06), 1.0),
        (Glicko2Rating(rating=1550, rd=100, volatility=0.06), 0.0),
        (Glicko2Rating(rating=1700, rd=300, volatility=0.06), 0.0),
    ]
    new_rating = update_rating(player, opponents, tau=0.5)
    # Glickman's expected: rating ≈ 1464, RD ≈ 152
    assert abs(new_rating.rating - 1464) < 5
    assert abs(new_rating.rd - 152) < 5
