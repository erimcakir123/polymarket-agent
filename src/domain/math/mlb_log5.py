"""Bill James log5: head-to-head win probability from individual winpcts.

Equivalent to Bradley-Terry model.
Empirically validated on 200,000+ MLB games (SABR analysis).

Formula:
    P(A beats B) = (p_a - p_a * p_b) / (p_a + p_b - 2 * p_a * p_b)

Inputs clamped to [0.01, 0.99] to prevent division by zero in degenerate cases.
"""
from __future__ import annotations

_LOG5_MIN_CLAMP: float = 0.01
_LOG5_MAX_CLAMP: float = 0.99


def log5(p_a: float, p_b: float) -> float:
    """log5: P(A beats B) given each team's overall win probability.

    Args:
        p_a: team A's season winpct
        p_b: team B's season winpct

    Returns:
        P(A beats B) in [0.0, 1.0].
    """
    p_a = max(_LOG5_MIN_CLAMP, min(_LOG5_MAX_CLAMP, p_a))
    p_b = max(_LOG5_MIN_CLAMP, min(_LOG5_MAX_CLAMP, p_b))

    if abs(p_a - p_b) < 1e-9:
        return 0.5

    numerator = p_a - p_a * p_b
    denominator = p_a + p_b - 2 * p_a * p_b
    return numerator / denominator
