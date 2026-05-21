"""Tango Run Expectancy Matrix (MLB 2010-2015 average).

SPEC-R Plan 2 T11. Source: Tom Tango, *The Book* (2007), updated tables
on InsideTheBook. Values are expected runs scored from given state to
end of inning.

Encoded matching base_out_states.encode():
    state_idx = outs * 8 + runner_bits
"""
from __future__ import annotations

RE_MATRIX: dict[int, float] = {
    # 0 outs
    0: 0.481,   # ---
    1: 0.859,   # 1--
    2: 1.100,   # -2-
    3: 1.437,   # 12-
    4: 1.350,   # --3
    5: 1.784,   # 1-3
    6: 1.964,   # -23
    7: 2.282,   # 123
    # 1 out
    8: 0.254,   # ---
    9: 0.509,   # 1--
    10: 0.664,  # -2-
    11: 0.884,  # 12-
    12: 0.950,  # --3
    13: 1.130,  # 1-3
    14: 1.376,  # -23
    15: 1.541,  # 123
    # 2 outs
    16: 0.098,  # ---
    17: 0.224,  # 1--
    18: 0.319,  # -2-
    19: 0.429,  # 12-
    20: 0.353,  # --3
    21: 0.478,  # 1-3
    22: 0.580,  # -23
    23: 0.752,  # 123
}


def expected_runs(state_idx: int) -> float:
    """Lookup expected runs from given state."""
    if state_idx not in RE_MATRIX:
        raise ValueError(f"state_idx not in RE_MATRIX: {state_idx}")
    return RE_MATRIX[state_idx]
