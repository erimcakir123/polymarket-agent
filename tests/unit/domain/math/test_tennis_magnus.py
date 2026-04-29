"""Klaassen-Magnus + O'Malley closed-form chain tests."""
from __future__ import annotations

import math

import pytest

from src.domain.math.tennis_magnus import (
    MatchState,
    p_game_on_serve,
    p_set,
    p_match_bo3,
    p_match_from_state,
)


def test_p_game_on_serve_at_50pct_is_50pct() -> None:
    """When p=0.5, game outcome is 50/50."""
    assert math.isclose(p_game_on_serve(0.5), 0.5, abs_tol=1e-6)


def test_p_game_on_serve_strong_server_70pct() -> None:
    """At p=0.70 (strong server), game win ~ 90%."""
    g = p_game_on_serve(0.70)
    assert 0.88 < g < 0.92


def test_p_game_on_serve_weak_server_30pct() -> None:
    """At p=0.30 (weak), game win ~ 10%."""
    g = p_game_on_serve(0.30)
    assert 0.08 < g < 0.12


def test_p_game_on_serve_zero() -> None:
    assert p_game_on_serve(0.0) == 0.0


def test_p_game_on_serve_one() -> None:
    assert p_game_on_serve(1.0) == 1.0


def test_p_set_balanced() -> None:
    """Balanced players -> set probability ~50%."""
    s = p_set(p_a=0.65, p_b=0.65)
    assert 0.48 < s < 0.52


def test_p_set_strong_a() -> None:
    """A serve 70%, B serve 60% -> A wins set ~80% (game-on-serve amplifies edge)."""
    s = p_set(p_a=0.70, p_b=0.60)
    assert 0.75 < s < 0.85


def test_p_match_bo3_balanced() -> None:
    """Balanced players -> match ~50%."""
    m = p_match_bo3(p_a=0.65, p_b=0.65)
    assert 0.48 < m < 0.52


def test_p_match_bo3_strong_a() -> None:
    """A 70%, B 60% serve -> A wins match ~90% (BO3 amplifies set edge)."""
    m = p_match_bo3(p_a=0.70, p_b=0.60)
    assert 0.85 < m < 0.95


def test_p_match_from_state_pre_match_matches_bo3() -> None:
    """Pre-match state should equal p_match_bo3."""
    state = MatchState(sets_won_a=0, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    p_bo3 = p_match_bo3(p_a=0.70, p_b=0.60)
    assert math.isclose(p_state, p_bo3, abs_tol=0.02)


def test_p_match_from_state_a_won_first_set() -> None:
    """A won set 1 -> P(A wins match) increases."""
    state = MatchState(sets_won_a=1, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    assert p_state > 0.85


def test_p_match_from_state_a_lost_first_set() -> None:
    """A lost set 1 -> P(A wins match) decreases (must drop below pre-match baseline)."""
    state_pre = MatchState(sets_won_a=0, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    state_lost = MatchState(sets_won_a=0, sets_won_b=1, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_pre = p_match_from_state(p_a=0.70, p_b=0.60, state=state_pre)
    p_lost = p_match_from_state(p_a=0.70, p_b=0.60, state=state_lost)
    assert p_lost < p_pre


def test_p_match_from_state_a_already_won() -> None:
    """A won 2 sets in BO3 -> match over, P(A) = 1."""
    state = MatchState(sets_won_a=2, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    assert p_state == 1.0


def test_p_match_from_state_a_already_lost() -> None:
    """A lost 2 sets in BO3 -> match over, P(A) = 0."""
    state = MatchState(sets_won_a=0, sets_won_b=2, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_state = p_match_from_state(p_a=0.70, p_b=0.60, state=state)
    assert p_state == 0.0
