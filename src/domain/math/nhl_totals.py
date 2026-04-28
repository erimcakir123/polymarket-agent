"""NHL totals (over/under) probability via Poisson distribution.

Total goals = home + away ~ Poisson(λ_total × t) where λ_total = λ_home + λ_away.
NHL avg: 6.142 / 3600 = 0.001706 total goals per second.

P(over X.5) = P(future_goals > X - current_total + 0.5)
            = P(Poisson(λ × t) >= ceil(X + 0.5 - current_total))
            = 1 - poisson.cdf(ceil(X + 0.5 - current_total) - 1, λ × t)
"""
from __future__ import annotations

import math

from scipy.stats import poisson

LAMBDA_TOTAL_PER_SECOND: float = 6.142 / 3600.0  # ≈ 0.001706


def poisson_p_over(
    current_total: int,
    target_total: float,
    seconds_remaining: int,
    lambda_total: float = LAMBDA_TOTAL_PER_SECOND,
) -> float:
    """P(final_total > target_total) given current state.

    Args:
      current_total: anlık toplam gol
      target_total: bahis line (örn 5.5)
      seconds_remaining: regulation kalan saniye

    Returns:
      Over olasılığı [0, 1].
    """
    if current_total > target_total:
        return 1.0

    if seconds_remaining <= 0:
        return 1.0 if current_total > target_total else 0.0

    mu = lambda_total * seconds_remaining
    goals_needed = math.ceil(target_total + 0.5 - current_total)
    p = 1.0 - poisson.cdf(goals_needed - 1, mu)
    return float(max(0.0, min(1.0, p)))
