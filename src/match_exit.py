"""Match-aware exit system — 4-layer exit logic using match timing, score, and profit history.

Spec: docs/superpowers/specs/2026-03-22-match-aware-exit-system-design.md
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def parse_match_score(
    score_str: str | None,
    number_of_games: int,
    direction: str,
) -> dict:
    """Parse match_score into structured data, direction-aware.

    Args:
        score_str: Raw score string from Gamma API (e.g. "2-1|Bo3", "1-0")
        number_of_games: BO format (1, 3, 5). 0 = unknown, treated as BO3.
        direction: "BUY_YES" or "BUY_NO" — determines which side is "ours"

    Returns:
        dict with keys: available, our_maps, opp_maps, map_diff,
                        is_already_lost, is_already_won
    """
    empty = {"available": False}

    if not score_str or not isinstance(score_str, str):
        return empty

    try:
        # Split format suffix: "2-1|Bo3" → "2-1", "Bo3"
        parts = score_str.split("|")
        scores = parts[0].strip().split("-")
        if len(scores) != 2:
            return empty

        first_score = int(scores[0].strip())
        second_score = int(scores[1].strip())
    except (ValueError, IndexError):
        return empty

    # Direction-aware: BUY_YES = we want first team to win
    #                  BUY_NO  = we want first team to lose (second team wins)
    if direction == "BUY_NO":
        our_maps = second_score
        opp_maps = first_score
    else:
        our_maps = first_score
        opp_maps = second_score

    bo = number_of_games if number_of_games > 0 else 3
    wins_needed = (bo // 2) + 1

    return {
        "available": True,
        "our_maps": our_maps,
        "opp_maps": opp_maps,
        "map_diff": our_maps - opp_maps,
        "is_already_lost": opp_maps >= wins_needed,
        "is_already_won": our_maps >= wins_needed,
    }
