"""Layer 5: run-line (spread) market pricer.

SPEC-R Plan 2 T18.

home_line = -1.5 means home is favored to win by 1.5+ runs.
home_line = +1.5 means home gets 1.5 run head start.
home_covers iff home_runs + home_line > away_runs.
"""
from __future__ import annotations


def spread_probability(
    home_dist: dict[int, float],
    away_dist: dict[int, float],
    home_line: float,
) -> tuple[float, float]:
    """Compute P(home_covers) and P(away_covers) for run-line bet.

    Args:
        home_dist: {runs: probability} for home team.
        away_dist: {runs: probability} for away team.
        home_line: spread from home perspective (e.g., -1.5, +1.5).

    Returns:
        (p_home_covers, p_away_covers). For .5 lines push impossible.
        For integer lines push = 1 - p_home - p_away.
    """
    p_home = 0.0
    p_away = 0.0
    for h_runs, h_prob in home_dist.items():
        for a_runs, a_prob in away_dist.items():
            joint = h_prob * a_prob
            home_adjusted = h_runs + home_line
            if home_adjusted > a_runs:
                p_home += joint
            elif home_adjusted < a_runs:
                p_away += joint
            # equal → push
    return p_home, p_away
