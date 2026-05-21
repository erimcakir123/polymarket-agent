"""Handedness (L/R) platoon split multipliers.

SPEC-R Plan 2 T4. Values derived from lifetime MLB splits (~2010-2020).
Switch hitters use opposite-of-pitcher convention.
"""
from __future__ import annotations

_PLATOON_MULTIPLIERS: dict[tuple[str, str], dict[str, float]] = {
    ("L", "L"): {"K": 1.15, "BB": 0.92, "HR": 0.92, "1B": 0.95, "2B": 0.95, "3B": 0.95, "HBP": 1.00, "OUT_IN_PLAY": 1.05},
    ("L", "R"): {"K": 0.92, "BB": 1.08, "HR": 1.08, "1B": 1.05, "2B": 1.05, "3B": 1.05, "HBP": 1.00, "OUT_IN_PLAY": 0.95},
    ("R", "R"): {"K": 1.05, "BB": 0.96, "HR": 0.97, "1B": 0.98, "2B": 0.98, "3B": 0.98, "HBP": 1.00, "OUT_IN_PLAY": 1.02},
    ("R", "L"): {"K": 0.90, "BB": 1.10, "HR": 1.12, "1B": 1.06, "2B": 1.06, "3B": 1.06, "HBP": 1.00, "OUT_IN_PLAY": 0.94},
}


def platoon_multiplier(batter_hand: str, pitcher_hand: str, outcome: str) -> float:
    """Lookup platoon multiplier for outcome given handedness.

    Switch hitters (S) bat opposite of pitcher (vs L→R, vs R→L).
    Unknown hand or outcome returns 1.0 (no adjustment).
    """
    # Resolve switch hitter
    if batter_hand == "S":
        batter_hand = "L" if pitcher_hand == "R" else "R" if pitcher_hand == "L" else "X"
    table = _PLATOON_MULTIPLIERS.get((batter_hand, pitcher_hand))
    if table is None:
        return 1.0
    return table.get(outcome, 1.0)
