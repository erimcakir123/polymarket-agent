"""3-segment leverage-aware bullpen selection.

SPEC-R Plan 2 T14. Maps game state (inning, score_diff) → pitcher rates.
- Innings 1-5: starter
- Innings 6-7: middle
- Inning 8: setup (if close), middle (if blowout)
- Inning 9: closer (if save situation: home leads 1-3), setup (close non-save),
  middle (blowout)
- Extra innings (10+): setup (close), middle (blowout)
"""
from __future__ import annotations

_BLOWOUT_THRESHOLD = 4   # |score_diff| >= 4 = blowout
_SAVE_MIN_LEAD = 1
_SAVE_MAX_LEAD = 3


def select_pitcher(
    inning: int,
    score_diff: int,
    starter_rates: dict[str, float],
    bullpen: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Return pitcher rates for given game state."""
    abs_diff = abs(score_diff)
    is_blowout = abs_diff >= _BLOWOUT_THRESHOLD

    if inning <= 5:
        return starter_rates
    if inning <= 7:
        return bullpen["middle"]
    # inning 8
    if inning == 8:
        return bullpen["middle"] if is_blowout else bullpen["setup"]
    # inning 9
    if inning == 9:
        if is_blowout:
            return bullpen["middle"]
        is_save_situation = _SAVE_MIN_LEAD <= score_diff <= _SAVE_MAX_LEAD
        if is_save_situation:
            return bullpen["closer"]
        return bullpen["setup"]
    # extra innings
    if is_blowout:
        return bullpen["middle"]
    return bullpen["setup"]
