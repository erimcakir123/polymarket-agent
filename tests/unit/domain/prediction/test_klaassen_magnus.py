"""Klaassen-Magnus tennis probability math — pure functions."""
from __future__ import annotations

import pytest

from src.domain.prediction.klaassen_magnus import (
    game_win_prob,
    match_win_prob_bo3,
    match_win_prob_bo5,
    set_win_prob,
)


def test_game_win_prob_equal_point_returns_half():
    # 50% serve point win → game win prob also 0.5
    assert abs(game_win_prob(0.5) - 0.5) < 0.001


def test_game_win_prob_dominant_serve_near_certain():
    # 70% serve point win → near-certain game win
    p = game_win_prob(0.7)
    assert p > 0.9


def test_game_win_prob_weak_serve_near_loss():
    # 30% serve point win → near-certain game loss
    p = game_win_prob(0.3)
    assert p < 0.1


def test_set_win_prob_equal_servers_near_half():
    # Both serve at 65% (typical ATP) → set close to 0.5
    p = set_win_prob(p_serve_a=0.65, p_serve_b=0.65)
    assert abs(p - 0.5) < 0.05


def test_set_win_prob_stronger_server_higher_prob():
    # A serves 70%, B serves 60% → A favored
    p = set_win_prob(p_serve_a=0.70, p_serve_b=0.60)
    assert p > 0.6


def test_match_win_prob_bo3_set_55_pct_matches_formula():
    # Each set 55% → match should be ~57%
    p = match_win_prob_bo3(p_set=0.55)
    expected = 0.55 ** 2 + 2 * 0.55 ** 2 * (1 - 0.55)
    assert abs(p - expected) < 0.001


def test_match_win_prob_bo5_amplifies_favorite_vs_bo3():
    # BO5 amplifies favorite's edge vs BO3
    p_bo3 = match_win_prob_bo3(p_set=0.60)
    p_bo5 = match_win_prob_bo5(p_set=0.60)
    assert p_bo5 > p_bo3


def test_set_win_prob_clamps_to_unit_interval():
    # Extreme inputs should not produce >1 or <0
    p = set_win_prob(p_serve_a=0.95, p_serve_b=0.30)
    assert 0.0 <= p <= 1.0


def test_match_win_prob_bo3_zero_set_returns_zero():
    assert match_win_prob_bo3(p_set=0.0) == 0.0


def test_match_win_prob_bo3_one_set_returns_one():
    assert match_win_prob_bo3(p_set=1.0) == 1.0
