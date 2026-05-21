"""Layer 5: totals (over/under) market pricer.

SPEC-R Plan 2 T17. Convolves home + away run distributions to total runs,
then computes over/under probabilities for given line.

Half-line (.5): no push. Integer line: push possible.
"""
from __future__ import annotations

from src.domain.mlb_submarket.game_simulator import team_run_distribution


def totals_probability(
    home_dist: dict[int, float],
    away_dist: dict[int, float],
    line: float,
) -> tuple[float, float]:
    """Compute P(over) and P(under) given home/away run distributions.

    Args:
        home_dist: {runs: probability} for home team.
        away_dist: {runs: probability} for away team.
        line: totals line (e.g., 8.5, 9.0).

    Returns:
        (p_over, p_under). If line is integer, push = 1 - p_over - p_under.
    """
    total_dist = team_run_distribution([home_dist, away_dist])

    p_over = 0.0
    p_under = 0.0
    is_half_line = (line * 2) % 2 != 0  # True for .5 lines
    for total_runs, prob in total_dist.items():
        if is_half_line:
            if total_runs > line:
                p_over += prob
            else:
                p_under += prob
        else:
            # Integer line: push when equal
            if total_runs > line:
                p_over += prob
            elif total_runs < line:
                p_under += prob
            # equal → push (neither)
    return p_over, p_under
