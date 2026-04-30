"""MLB Totals probability via Poisson-sum.

Total runs T = home_runs + away_runs ~ Poisson(lam_home + lam_away).
P(T > line) = sf(floor(line), lam_total).

Adjustments:
- park_factor: multiplies expected lambda (1.0 = neutral)
- weather_run_bias: additive run shift on total (e.g. wind blowing out)
"""
from __future__ import annotations

from scipy.stats import poisson

_LAMBDA_FLOOR: float = 1.0  # min total lambda safety floor


def p_over_totals(
    home_runs: float,
    away_runs: float,
    line: float,
    park_factor: float = 1.0,
    weather_run_bias: float = 0.0,
) -> float:
    """Probability total runs > line.

    Args:
        home_runs: home team expected runs (lambda)
        away_runs: away team expected runs (lambda)
        line: totals line, e.g. 8.5
        park_factor: 1.0 neutral; >1 hitter park; <1 pitcher park
        weather_run_bias: additive (wind blowing out → +; in → -)

    Returns:
        P(T > line) in [0.0, 1.0].
    """
    if home_runs <= 0 and away_runs <= 0:
        return 0.5

    lam_total = (home_runs + away_runs) * park_factor + weather_run_bias
    lam_total = max(lam_total, _LAMBDA_FLOOR)

    threshold = int(line)
    return float(poisson.sf(threshold, lam_total))
