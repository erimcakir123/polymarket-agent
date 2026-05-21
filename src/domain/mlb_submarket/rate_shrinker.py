"""Empirical Bayes Beta shrinkage + Marcel projection weighting.

SPEC-R Plan 2 T3. Sources:
- Beta-Binomial conjugate: David Robinson, varianceexplained.org
- Marcel weighting: Tom Tango, baseball-reference (5/4/3 ratio for 3 prior seasons)
"""
from __future__ import annotations


def shrink_beta(
    observed_x: int,
    observed_n: int,
    prior_alpha: float,
    prior_beta: float,
) -> float:
    """Beta posterior mean = (alpha + x) / (alpha + beta + n).

    Args:
        observed_x: successes observed
        observed_n: total trials observed (n >= x)
        prior_alpha: Beta prior alpha (success pseudocount)
        prior_beta: Beta prior beta (failure pseudocount)

    Returns:
        Posterior mean (shrunk rate).
    """
    if observed_n < 0:
        raise ValueError(f"n must be >= 0, got {observed_n}")
    if observed_x > observed_n:
        raise ValueError(f"x ({observed_x}) cannot exceed n ({observed_n})")
    return (prior_alpha + observed_x) / (prior_alpha + prior_beta + observed_n)


def marcel_weight(
    observed_seasons: list[tuple[float, int]],
    weights: tuple[float, ...] = (5.0, 4.0, 3.0),
) -> float:
    """Marcel projection: weighted average of (rate, n) pairs.

    Default weights (5, 4, 3) correspond to current year, year-1, year-2.

    Args:
        observed_seasons: list of (rate, sample_size) tuples, most recent first.
        weights: weight per season position (default Marcel 5/4/3).

    Returns:
        Weighted rate estimate.
    """
    if len(observed_seasons) > len(weights):
        raise ValueError(
            f"observed_seasons ({len(observed_seasons)}) exceeds weights length ({len(weights)})"
        )
    numerator = 0.0
    denominator = 0.0
    for (rate, n), w in zip(observed_seasons, weights):
        numerator += w * rate * n
        denominator += w * n
    if denominator == 0:
        return 0.0
    return numerator / denominator
