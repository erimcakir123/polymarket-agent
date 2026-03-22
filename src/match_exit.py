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


# Game-specific duration estimates (minutes)
# Key: (game_prefix, number_of_games) → duration in minutes
_DURATION_TABLE: dict[tuple[str, int], int] = {
    ("cs2", 1): 40,   ("cs2", 3): 130,  ("cs2", 5): 200,
    ("val", 1): 50,    ("val", 3): 140,  ("val", 5): 220,
    ("lol", 1): 35,    ("lol", 3): 100,  ("lol", 5): 160,
    ("dota2", 1): 45,  ("dota2", 3): 130, ("dota2", 5): 210,
}

# Sport detection from slug prefix
_SPORT_DURATION: dict[str, int] = {
    "epl": 95, "laliga": 95, "ucl": 95, "seriea": 95, "bundesliga": 95, "ligue1": 95,
    "nba": 150,
    "cbb": 120,
    "mlb": 180,
    "nhl": 150,
}

# Generic esports fallback (when game is unknown but BO format exists)
_GENERIC_ESPORTS: dict[int, int] = {1: 40, 3: 120, 5: 180}


def get_game_duration(slug: str, number_of_games: int) -> int:
    """Return estimated match duration in minutes.

    Uses game-specific lookup from slug prefix + BO format.
    Falls back to sport-specific, then generic esports, then 90 min default.
    """
    slug_lower = slug.lower()

    # Try game-specific esports lookup
    for prefix in ("cs2", "val", "lol", "dota2"):
        if slug_lower.startswith(f"{prefix}-"):
            bo = number_of_games if number_of_games > 0 else 3
            return _DURATION_TABLE.get((prefix, bo), _DURATION_TABLE.get((prefix, 3), 120))

    # Try sport-specific lookup
    for prefix, duration in _SPORT_DURATION.items():
        if slug_lower.startswith(f"{prefix}-"):
            return duration

    # If BO format is specified, assume generic esports
    if number_of_games in (1, 3, 5):
        return _GENERIC_ESPORTS[number_of_games]

    # Absolute fallback
    return 90
