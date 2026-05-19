"""Klaassen-Magnus tennis probability math — pure, no I/O.

Implements:
- game_win_prob(p): Newton-Keller formula for probability of winning a service game
- set_win_prob(p_serve_a, p_serve_b): probability of winning a set (with tie-break at 6-6)
- match_win_prob_bo3/bo5: best-of-3 or best-of-5 match probability from set probability

References:
- Newton, P. K. & Keller, J. B. (2005). "Probability formulas in tennis"
- Klaassen, F. & Magnus, J. R. (2003). "Forecasting the winner of a tennis match"

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §5
"""
from __future__ import annotations


def game_win_prob(p: float) -> float:
    """Probability of winning a service game given point-win probability.

    Uses point-by-point recursion with closed-form deuce resolution.
    At deuce (3-3), the probability is p^2 / (p^2 + q^2) — the geometric
    series sum for winning two consecutive points from deuce.

    Klaassen & Magnus (2003) model: each point iid with probability p.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    q = 1.0 - p
    cache: dict[tuple[int, int], float] = {}

    def rec(a: int, b: int) -> float:
        if a >= 4 and a - b >= 2:
            return 1.0
        if b >= 4 and b - a >= 2:
            return 0.0
        if a == 3 and b == 3:
            # Deuce: closed-form geometric series
            return (p * p) / (p * p + q * q)
        key = (a, b)
        if key in cache:
            return cache[key]
        result = p * rec(a + 1, b) + q * rec(a, b + 1)
        cache[key] = result
        return result

    return rec(0, 0)


def set_win_prob(p_serve_a: float, p_serve_b: float) -> float:
    """Probability A wins a set given each player's serve point win prob.

    Uses recursive game-by-game scoring with tie-break at 6-6.
    """
    if p_serve_a <= 0.0 and p_serve_b >= 1.0:
        return 0.0
    if p_serve_a >= 1.0 and p_serve_b <= 0.0:
        return 1.0

    pA_hold = game_win_prob(p_serve_a)
    pB_hold = game_win_prob(p_serve_b)
    pA_break = 1.0 - pB_hold
    # Average win prob per game (A serves half the games, returns half)
    pA_game = 0.5 * pA_hold + 0.5 * pA_break
    return _set_win_prob_recursive(pA_game)


def _set_win_prob_recursive(pA_game: float) -> float:
    """First-to-6-with-margin set probability via memoized recursion."""
    cache: dict[tuple[int, int], float] = {}

    def rec(a: int, b: int) -> float:
        if a >= 6 and a - b >= 2:
            return 1.0
        if b >= 6 and b - a >= 2:
            return 0.0
        if a == 6 and b == 6:
            return _tiebreak_win_prob(pA_game)
        key = (a, b)
        if key in cache:
            return cache[key]
        result = pA_game * rec(a + 1, b) + (1.0 - pA_game) * rec(a, b + 1)
        cache[key] = result
        return result

    return rec(0, 0)


def _tiebreak_win_prob(pA_point: float) -> float:
    """7-point tiebreak win probability (first to 7, margin >=2).

    At 6-6 in the tiebreak (mini-deuce), uses closed-form: p^2 / (p^2 + q^2).
    """
    q = 1.0 - pA_point
    cache: dict[tuple[int, int], float] = {}

    def rec(a: int, b: int) -> float:
        if a >= 7 and a - b >= 2:
            return 1.0
        if b >= 7 and b - a >= 2:
            return 0.0
        if a == 6 and b == 6:
            # Mini-deuce: closed-form geometric series
            return (pA_point * pA_point) / (pA_point * pA_point + q * q)
        key = (a, b)
        if key in cache:
            return cache[key]
        result = pA_point * rec(a + 1, b) + q * rec(a, b + 1)
        cache[key] = result
        return result

    return rec(0, 0)


def match_win_prob_bo3(p_set: float) -> float:
    """Best-of-3 match win probability given set probability."""
    if p_set <= 0.0:
        return 0.0
    if p_set >= 1.0:
        return 1.0
    # P(win 2-0) + P(win 2-1)
    return p_set ** 2 + 2.0 * (p_set ** 2) * (1.0 - p_set)


def match_win_prob_bo5(p_set: float) -> float:
    """Best-of-5 match win probability given set probability."""
    if p_set <= 0.0:
        return 0.0
    if p_set >= 1.0:
        return 1.0
    # P(3-0) + P(3-1) + P(3-2)
    return (p_set ** 3
            + 3.0 * (p_set ** 3) * (1.0 - p_set)
            + 6.0 * (p_set ** 3) * (1.0 - p_set) ** 2)
