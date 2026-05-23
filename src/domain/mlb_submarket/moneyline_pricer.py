"""Moneyline pricer — P(home wins) and P(away wins) from run distributions.

MLB official games cannot end in a tie (extra innings determine winner).
home_dist + away_dist represent regulation runs (9 inning or 7 inning game).
On regulation tie, we assume 50/50 split — the tie is resolved arbitrarily in extras.

Pattern reference: totals_pricer.py, spread_pricer.py (loop over joint outcomes).
"""
from __future__ import annotations


def moneyline_probability(
    home_dist: dict[int, float],
    away_dist: dict[int, float],
) -> tuple[float, float]:
    """Compute P(home_wins) and P(away_wins) from regulation run distributions.

    Args:
        home_dist: {runs: probability} — home team regulation runs (0-9 or 0-7).
        away_dist: {runs: probability} — away team regulation runs (0-9 or 0-7).

    Returns:
        (p_home, p_away). Always sum to 1.0 (no pushes in moneyline).

    Behavior:
        - home_runs > away_runs: home wins entirely
        - home_runs < away_runs: away wins entirely
        - home_runs == away_runs: 50/50 split (extras determined arbitrarily)
    """
    p_home = 0.0
    p_away = 0.0
    for h_runs, h_prob in home_dist.items():
        for a_runs, a_prob in away_dist.items():
            joint = h_prob * a_prob
            if h_runs > a_runs:
                p_home += joint
            elif h_runs < a_runs:
                p_away += joint
            else:
                # Regulation tie → assume 50/50 in extras
                p_home += joint * 0.5
                p_away += joint * 0.5
    return p_home, p_away
