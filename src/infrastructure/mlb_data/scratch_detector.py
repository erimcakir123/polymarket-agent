"""Lineup scratch detector.

SPEC-R Plan 3 T5. Compares current vs previous lineup, returns position-aligned
diff. Caller typically polls T-60, T-30, T-15 and reacts to non-empty diffs.
"""
from __future__ import annotations

from typing import Protocol


class _StatsApiLike(Protocol):
    def get_lineup(self, game_pk: int) -> dict[str, list[int]]: ...


class ScratchDetector:
    def __init__(self, statsapi: _StatsApiLike) -> None:
        self._statsapi = statsapi

    def get_current_lineup(self, game_pk: int) -> dict[str, list[int]]:
        return self._statsapi.get_lineup(game_pk)

    @staticmethod
    def diff(
        previous: dict[str, list[int]],
        current: dict[str, list[int]],
    ) -> dict[str, list[tuple[int, int]]]:
        """Returns {'home': [(out_id, in_id), ...], 'away': [...]}.

        Each tuple = (previous batter swapped OUT, new batter swapped IN).
        Position-aligned (compare batting order index by index).
        """
        result: dict[str, list[tuple[int, int]]] = {}
        for side in ("home", "away"):
            prev_lineup = previous.get(side, [])
            curr_lineup = current.get(side, [])
            if len(prev_lineup) != len(curr_lineup):
                raise ValueError(
                    f"Lineup length mismatch for {side}: "
                    f"prev={len(prev_lineup)}, curr={len(curr_lineup)}"
                )
            swaps = [
                (p, c) for p, c in zip(prev_lineup, curr_lineup)
                if p != c
            ]
            result[side] = swaps
        return result
