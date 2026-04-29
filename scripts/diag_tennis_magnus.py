"""Quick sanity check: run Magnus prediction on one known match.

Usage: python -m scripts.diag_tennis_magnus
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.math.tennis_magnus import MatchState, p_match_bo3, p_match_from_state


def main() -> None:
    print("=== Magnus chain sanity check ===")

    # Sinner vs Cobolli, Madrid clay
    # NOTE: the constants below (career serve % and surface factor) are
    # ILLUSTRATIVE sample inputs for this one-off diagnostic. They are not
    # production thresholds and intentionally hardcoded so this script can be
    # re-run without external data dependencies.
    p_sinner_clay = 0.689 * 0.92  # career 68.9% adjusted for clay
    p_cobolli_clay = 0.642 * 0.92  # career 64.2% adjusted

    pre_match = p_match_bo3(p_sinner_clay, p_cobolli_clay)
    print(f"Pre-match P(Sinner wins) = {pre_match:.3f}")

    # After Sinner wins set 1
    state = MatchState(sets_won_a=1, sets_won_b=0, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_after_set1 = p_match_from_state(p_sinner_clay, p_cobolli_clay, state)
    print(f"After Sinner wins set 1: P(Sinner wins) = {p_after_set1:.3f}")

    # After Sinner loses set 1
    state = MatchState(sets_won_a=0, sets_won_b=1, games_a=0, games_b=0, server_is_a=True, format="BO3")
    p_after_loss = p_match_from_state(p_sinner_clay, p_cobolli_clay, state)
    print(f"After Sinner loses set 1: P(Sinner wins) = {p_after_loss:.3f}")

    # Mid set 2, Sinner down 0-2 set, 1-3 in current
    state = MatchState(sets_won_a=0, sets_won_b=2, games_a=1, games_b=3, server_is_a=True, format="BO3")
    p_dead = p_match_from_state(p_sinner_clay, p_cobolli_clay, state)
    print(f"Sinner down 0-2 sets + 1-3 game: P(Sinner wins) = {p_dead:.3f}")


if __name__ == "__main__":
    main()
