"""
NHL hybrid win probability — empirical-first with Skellam fallback.

Production exit logic should use this module, not the underlying
nhl_empirical_wp / nhl_skellam directly.

Strategy:
1. Try empirical lookup (MoneyPuck 2022-25, 4198 games)
2. If empirical bucket has <30 samples (returns None), fall back to Skellam
3. Tied state (deficit=0) returns 0.50 (v2: home edge)
"""
from __future__ import annotations

from src.domain.math import nhl_empirical_wp, nhl_skellam


def trailing_team_win_probability(
    period: int,
    deficit: int,
    seconds_remaining: int,
) -> tuple[float, str]:
    """
    Hybrid trailing team win probability.

    Returns:
        (probability, source) where source in {"empirical", "skellam_fallback", "trivial"}
    """
    if deficit <= 0:
        return 1.0, "trivial"
    if seconds_remaining <= 0:
        return 0.0, "trivial"

    p_emp = nhl_empirical_wp.trailing_team_win_probability_empirical(
        period, deficit, seconds_remaining
    )
    if p_emp is not None:
        return p_emp, "empirical"

    p_skel = nhl_skellam.trailing_team_win_probability(deficit, seconds_remaining)
    return p_skel, "skellam_fallback"


def leading_team_win_probability(
    period: int,
    lead: int,
    seconds_remaining: int,
) -> tuple[float, str]:
    """
    Hybrid leading team win probability.

    Returns:
        (probability, source) where source in {"empirical", "skellam_fallback", "trivial"}
    """
    if lead <= 0:
        return 0.0, "trivial"
    if seconds_remaining <= 0:
        return 1.0, "trivial"

    p_emp = nhl_empirical_wp.leading_team_win_probability_empirical(
        period, lead, seconds_remaining
    )
    if p_emp is not None:
        return p_emp, "empirical"

    p_skel = nhl_skellam.leading_team_win_probability(lead, seconds_remaining)
    return p_skel, "skellam_fallback"
