"""Lineup rotation + Times Through Order (TTO).

SPEC-R Plan 2 T13. Standard 9-batter MLB lineup. TTO categorizes pitcher's
familiarity round.
"""
from __future__ import annotations

LINEUP_SIZE = 9


def batter_at_pa(total_pa_so_far: int) -> int:
    """Return lineup index (0-8) of batter at given PA count."""
    return total_pa_so_far % LINEUP_SIZE


def times_through_order(total_pa_so_far: int) -> int:
    """Return TTO category: 1, 2, 3, or 4+ (clipped at 4).

    PA 0-8 → 1TT, PA 9-17 → 2TT, PA 18-26 → 3TT, PA 27+ → 4TT.
    """
    if total_pa_so_far < 0:
        return 1
    tto = (total_pa_so_far // LINEUP_SIZE) + 1
    return min(tto, 4)
