# src/domain/math/mlb_pythagoras.py
"""Bill James Pythagorean expectation for MLB win percentage.

Steven Miller (2007) statistically verified exponent 1.83 for MLB.
This is the modern "PythagenPat" baseline; teams over/under-perform
± 4 wins per 162 games on average.

Usage: convert season-to-date RS (runs scored) and RA (runs allowed)
into expected winpct, used as input to log5 head-to-head probability.
"""
from __future__ import annotations

PYTHAGOREAN_EXPONENT_DEFAULT: float = 1.83


def pythagorean_winpct(
    runs_scored: float,
    runs_allowed: float,
    exponent: float = PYTHAGOREAN_EXPONENT_DEFAULT,
) -> float:
    """Bill James Pythagorean expectation.

    Args:
        runs_scored: total runs scored (season or per-game)
        runs_allowed: total runs allowed (same scope)
        exponent: defaults to 1.83 (Steven Miller verified for MLB)

    Returns:
        winpct in [0.0, 1.0]; returns 0.5 on degenerate input.
    """
    if runs_scored <= 0 and runs_allowed <= 0:
        return 0.5
    rs_pow = runs_scored ** exponent
    ra_pow = runs_allowed ** exponent
    total = rs_pow + ra_pow
    if total <= 0:
        return 0.5
    return rs_pow / total
