"""Klaassen-Magnus + O'Malley closed-form tennis chain.

Pure domain math. Computes P(player A wins match) given serve
probabilities and current match state. References:
- O'Malley (2008) Probability of Winning at Tennis I.
- Newton & Keller (2005) Probability formulas in tennis.
- Klaassen & Magnus (2003) Forecasting the winner.

H2H only. BO3 fully supported. BO5 stub raises NotImplementedError
(Phase 2 will implement).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MatchState:
    sets_won_a: int
    sets_won_b: int
    games_a: int
    games_b: int
    server_is_a: bool
    format: Literal["BO3", "BO5"]


def p_game_on_serve(p: float) -> float:
    """Newton-Keller closed-form: probability server wins a game given p_serve.

    G(p) = p^4 * (1 + 4q + 10 q^2 + 20 q^3 * p / (p^2 + q^2))
    where q = 1 - p. The first three terms cover wins at 4-0, 4-1, 4-2;
    the final term is the geometric sum at deuce. See Newton & Keller
    (2005) eq. 2 / O'Malley (2008) eq. 3. Verified: G(0.5) = 0.5.

    Edge cases: p=0 -> 0, p=1 -> 1.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    q = 1.0 - p
    deuce_branch = 20.0 * (q ** 3) * p / (p * p + q * q)
    return (p ** 4) * (1.0 + 4.0 * q + 10.0 * (q ** 2) + deuce_branch)


def p_set(p_a: float, p_b: float) -> float:
    """Probability A wins a set, alternating serves, A serves first.

    O'Malley standard formulation: enumerate all paths to A winning
    set 6-x or 7-x (with tiebreak for 6-6).
    """
    g_a = p_game_on_serve(p_a)
    g_b = p_game_on_serve(p_b)

    # P(A wins game on A's serve) = g_a; P(A wins game on B's serve) = 1 - g_b
    # Compute P(A wins exactly k of first n service-game pairs)
    # Then sum over all set-end paths.
    return _set_recursive(g_a, g_b, score_a=0, score_b=0, server_is_a=True)


def _set_recursive(
    g_a_serve: float,
    g_b_serve: float,
    score_a: int,
    score_b: int,
    server_is_a: bool,
) -> float:
    """Recursive helper. Returns P(A wins set | current game score)."""
    # Set ended states
    if score_a == 6 and score_b <= 4:
        return 1.0
    if score_b == 6 and score_a <= 4:
        return 0.0
    if score_a == 7:
        return 1.0
    if score_b == 7:
        return 0.0
    # Tiebreak at 6-6 (simplified: assume tiebreak win prob = avg game)
    if score_a == 6 and score_b == 6:
        avg_game_p = (g_a_serve + (1 - g_b_serve)) / 2
        return _tiebreak_win_prob(avg_game_p)

    # P(A wins this game)
    p_win_game = g_a_serve if server_is_a else (1 - g_b_serve)

    p_a_wins_set_if_wins_this = _set_recursive(
        g_a_serve, g_b_serve, score_a + 1, score_b, not server_is_a
    )
    p_a_wins_set_if_loses_this = _set_recursive(
        g_a_serve, g_b_serve, score_a, score_b + 1, not server_is_a
    )

    return p_win_game * p_a_wins_set_if_wins_this + (1 - p_win_game) * p_a_wins_set_if_loses_this


def _tiebreak_win_prob(p: float) -> float:
    """Simplified tiebreak win probability given average game-win prob.

    For tiebreak detail, see O'Malley (2008) eq. 6. Approximation:
    treat tiebreak as a 7-of-13 best-of contest with point-win ~p.
    Sufficient for set-level approximation.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    # Approximate: tiebreak amplifies edge. Use sigmoid-ish.
    # P(win 7+ points before opponent in tiebreak)
    # For simplicity use binomial cdf approximation: P(>= 7 wins in 13 trials)
    from math import comb
    total = 0.0
    n = 13
    for k in range(7, n + 1):
        total += comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    return total


def p_match_bo3(p_a: float, p_b: float) -> float:
    """Probability A wins best-of-3 match given serve probabilities."""
    s_a = p_set(p_a, p_b)
    # Best of 3: A wins 2 sets first
    # P(2-0) + P(2-1) where each set independent (simplification)
    p_2_0 = s_a * s_a
    p_2_1 = 2 * s_a * (1 - s_a) * s_a
    return p_2_0 + p_2_1


def p_match_from_state(p_a: float, p_b: float, state: MatchState) -> float:
    """P(A wins match) given current match state.

    Handles: pre-match, mid-match (sets won + current game state),
    and terminal states (match over).
    """
    sets_to_win = 2 if state.format == "BO3" else 3

    # Terminal states
    if state.sets_won_a >= sets_to_win:
        return 1.0
    if state.sets_won_b >= sets_to_win:
        return 0.0

    if state.format == "BO5":
        raise NotImplementedError("BO5 implemented in Phase 2")

    # Compute P(A wins current set) given current game score
    g_a_serve = p_game_on_serve(p_a)
    g_b_serve = p_game_on_serve(p_b)
    p_a_wins_current_set = _set_recursive(
        g_a_serve, g_b_serve,
        score_a=state.games_a,
        score_b=state.games_b,
        server_is_a=state.server_is_a,
    )

    # Generic set probability for remaining sets after current
    p_a_wins_future_set = p_set(p_a, p_b)

    # Sets remaining after current = depends on outcome of current
    # If A wins current: needs (sets_to_win - sets_won_a - 1) more
    # If B wins current: A needs (sets_to_win - sets_won_a) more, B needs (sets_to_win - sets_won_b - 1) more
    # Compute combinatorially.
    sets_a_after_win = state.sets_won_a + 1
    sets_a_after_loss = state.sets_won_a
    sets_b_after_win = state.sets_won_b
    sets_b_after_loss = state.sets_won_b + 1

    p_match_if_win_current = _p_match_remaining(sets_a_after_win, sets_b_after_win, sets_to_win, p_a_wins_future_set)
    p_match_if_lose_current = _p_match_remaining(sets_a_after_loss, sets_b_after_loss, sets_to_win, p_a_wins_future_set)

    return p_a_wins_current_set * p_match_if_win_current + (1 - p_a_wins_current_set) * p_match_if_lose_current


def _p_match_remaining(sets_a: int, sets_b: int, sets_to_win: int, p_set: float) -> float:
    """P(A wins match) given remaining future sets are independent with prob p_set."""
    if sets_a >= sets_to_win:
        return 1.0
    if sets_b >= sets_to_win:
        return 0.0
    needed_a = sets_to_win - sets_a
    needed_b = sets_to_win - sets_b
    # P(A wins needed_a sets before B wins needed_b sets), each set IID with prob p_set
    return _negative_binomial_win(needed_a, needed_b, p_set)


def _negative_binomial_win(needed_a: int, needed_b: int, p: float) -> float:
    """P(A reaches needed_a wins before B reaches needed_b wins), each trial IID.

    Sum over k = 0 to needed_b - 1 of: C(needed_a + k - 1, k) * p^needed_a * (1-p)^k
    """
    from math import comb
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    total = 0.0
    for k in range(needed_b):
        total += comb(needed_a + k - 1, k) * (p ** needed_a) * ((1 - p) ** k)
    return total
