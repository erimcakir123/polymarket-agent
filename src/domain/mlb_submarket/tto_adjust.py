"""Times Through Order (TTO) penalty for pitcher rates.

SPEC-R Plan 2 T7. Pitcher familiarity hurts effectiveness on later passes.
Source: Mitchel Lichtman, "Times Through the Order Penalty", THT.

1TT = baseline (1.0). 2TT moderate degradation. 3TT+ steep degradation.
4+ TTO clipped to 3TT (extreme tail, rare in modern bullpen usage).
"""
from __future__ import annotations

_TTO_MULTIPLIERS: dict[int, dict[str, float]] = {
    1: {},  # baseline (all 1.0)
    2: {"K": 0.98, "HR": 1.05, "1B": 1.02, "BB": 1.02, "OUT_IN_PLAY": 0.99},
    3: {"K": 0.92, "HR": 1.12, "1B": 1.05, "BB": 1.04, "OUT_IN_PLAY": 0.97},
}


def tto_multiplier(times_through: int, outcome: str) -> float:
    """Lookup TTO penalty multiplier.

    Args:
        times_through: 1, 2, 3, or higher. Values >3 clipped to 3.
            Non-positive returns 1.0.
        outcome: PA outcome key.

    Returns:
        Multiplier. 1.0 if 1TT, no outcome match, or non-positive TTO.
    """
    if times_through < 1:
        return 1.0
    tto_key = min(times_through, 3)
    table = _TTO_MULTIPLIERS.get(tto_key, {})
    return table.get(outcome, 1.0)
