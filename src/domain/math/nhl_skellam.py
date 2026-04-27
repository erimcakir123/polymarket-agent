"""
NHL trailing/leading team win probability via Skellam distribution.

Theoretical fallback for empirical lookup (src/domain/math/nhl_empirical_wp.py).
Used when empirical bucket has insufficient samples (<30 games).

References:
- Buttrey, S. E., A. R. Washburn, W. L. Price (2011)
  "Estimating NHL Scoring Rates", J. Quant. Anal. Sports
- Hockey Analytics "Poisson Toolbox" (2006)

Constants (validated against MoneyPuck 2022-25 empirical table):
- NHL_REGULATION_LAMBDA_PER_SEC = 6.142 / 2 / 3600 = 0.000853 goals/sec
- NHL_OT_3V3_LAMBDA_PER_SEC     = 0.001400 goals/sec (~1.65x reg, OT scoring rate)

Assumptions (v1):
- Symmetric lambda (both teams equal) — talent NOT modeled
- Constant lambda throughout regulation (NOT score-state-aware)
- 5v5 default
- OT uses separate 3v3 lambda
- Empty Net dynamics not modeled (empirical layer compensates)
"""
from __future__ import annotations

from scipy.stats import skellam

NHL_REGULATION_LAMBDA_PER_SEC: float = 0.000853
NHL_OT_3V3_LAMBDA_PER_SEC: float = 0.001400
NHL_OT_DURATION_SEC: int = 300


def trailing_team_win_probability(
    deficit: int,
    seconds_remaining: int,
    lambda_per_sec: float = NHL_REGULATION_LAMBDA_PER_SEC,
) -> float:
    """
    Trailing team ML win probability (theoretical Skellam).

    Win paths:
    - Regulation comeback:  K >= deficit + 1
    - Tie + OT/SO 50/50:    K == deficit

    K = (trailing goals) - (leading goals) ~ Skellam(mu, mu)
    where mu = lambda_per_sec * seconds_remaining.
    """
    if deficit <= 0:
        return 1.0
    if seconds_remaining <= 0:
        return 0.0
    mu = lambda_per_sec * seconds_remaining
    p_win_reg = float(skellam.sf(deficit, mu, mu))
    p_tie_reg = float(skellam.pmf(deficit, mu, mu))
    return p_win_reg + 0.5 * p_tie_reg


def leading_team_win_probability(
    lead: int,
    seconds_remaining: int,
    lambda_per_sec: float = NHL_REGULATION_LAMBDA_PER_SEC,
) -> float:
    """Leading team win probability (theoretical Skellam)."""
    if lead <= 0:
        return 0.0
    if seconds_remaining <= 0:
        return 1.0
    mu = lambda_per_sec * seconds_remaining
    p_trail_win_reg = float(skellam.sf(lead, mu, mu))
    p_tie_reg = float(skellam.pmf(lead, mu, mu))
    return 1.0 - p_trail_win_reg - 0.5 * p_tie_reg


def comeback_probability_to_tie(
    deficit: int,
    seconds_remaining: int,
    lambda_per_sec: float = NHL_REGULATION_LAMBDA_PER_SEC,
) -> float:
    """Probability that trailing team achieves at least a tie."""
    if deficit <= 0:
        return 1.0
    if seconds_remaining <= 0:
        return 0.0
    mu = lambda_per_sec * seconds_remaining
    return float(skellam.sf(deficit - 1, mu, mu))


def ot_3v3_coin_flip_probability() -> float:
    """OT/SO 50/50 approximation (v2: talent-aware)."""
    return 0.5
