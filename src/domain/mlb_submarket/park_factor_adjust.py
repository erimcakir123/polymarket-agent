"""Component-level park factors (HR, 1B, 2B, 3B separate).

SPEC-R Plan 2 T5. CRITICAL: never apply BOTH total park factor AND component
factor — that double-counts. This module returns component-only factors.

Source: Baseball Savant park factors (statcast.org). Values are 100=neutral
scaled to multipliers (1.18 means +18% above league average).
"""
from __future__ import annotations

# Subset of MLB parks (extend in Plan 4 with full 30-park table)
PARK_FACTORS: dict[str, dict[str, float]] = {
    "COORS": {"HR": 1.18, "1B": 1.05, "2B": 1.10, "3B": 1.30},
    "PETCO": {"HR": 0.92, "1B": 0.97, "2B": 0.95, "3B": 0.85},
    "FENWAY": {"HR": 1.00, "1B": 1.03, "2B": 1.20, "3B": 0.90},  # Green Monster bumps 2B
    "YANKEE": {"HR": 1.10, "1B": 1.00, "2B": 1.00, "3B": 0.90},
    "DODGER": {"HR": 0.98, "1B": 1.00, "2B": 1.00, "3B": 1.00},  # near-neutral
}


def park_multiplier(park_id: str, outcome: str) -> float:
    """Lookup component park factor.

    Args:
        park_id: park identifier (e.g., "COORS", "PETCO").
        outcome: PA outcome ("HR", "1B", "2B", "3B").

    Returns:
        Multiplier >= 0. Unknown park or outcome -> 1.0 (no adjustment).
    """
    table = PARK_FACTORS.get(park_id)
    if table is None:
        return 1.0
    return table.get(outcome, 1.0)
