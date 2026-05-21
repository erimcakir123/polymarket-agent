"""Tests for markov.py state transition function (SPEC-R Plan 2 T12)."""
import pytest

from src.domain.mlb_submarket.base_out_states import INNING_ENDED, encode
from src.domain.mlb_submarket.markov import transition


def test_strikeout_empty_bases() -> None:
    state = encode(0, (False, False, False))
    new_state, runs = transition(state, "K")
    assert new_state == encode(1, (False, False, False))
    assert runs == 0


def test_strikeout_two_outs_ends_inning() -> None:
    state = encode(2, (True, True, False))
    new_state, runs = transition(state, "K")
    assert new_state == INNING_ENDED
    assert runs == 0


def test_homer_bases_empty() -> None:
    state = encode(0, (False, False, False))
    new_state, runs = transition(state, "HR")
    assert new_state == encode(0, (False, False, False))
    assert runs == 1


def test_homer_bases_loaded() -> None:
    state = encode(1, (True, True, True))
    new_state, runs = transition(state, "HR")
    assert new_state == encode(1, (False, False, False))
    assert runs == 4


def test_single_runners_advance() -> None:
    # 1 out, runner on 3B. Single → batter on 1B, runner scores.
    state = encode(1, (False, False, True))
    new_state, runs = transition(state, "1B")
    assert new_state == encode(1, (True, False, False))
    assert runs == 1


def test_single_runner_on_2nd_scores() -> None:
    # 0 out, runner on 2B. Single → batter on 1B, runner from 2B scores.
    state = encode(0, (False, True, False))
    new_state, runs = transition(state, "1B")
    assert new_state == encode(0, (True, False, False))
    assert runs == 1


def test_single_runner_on_1b_to_2b() -> None:
    state = encode(0, (True, False, False))
    new_state, runs = transition(state, "1B")
    # batter → 1B, prior 1B runner → 2B
    assert new_state == encode(0, (True, True, False))
    assert runs == 0


def test_double_bases_loaded_clears_all() -> None:
    state = encode(0, (True, True, True))
    new_state, runs = transition(state, "2B")
    # batter on 2B, 1B runner → 3B, 2B+3B runners score
    assert new_state == encode(0, (False, True, True))
    assert runs == 2


def test_triple_bases_loaded_scores_all_three() -> None:
    state = encode(0, (True, True, True))
    new_state, runs = transition(state, "3B")
    assert new_state == encode(0, (False, False, True))
    assert runs == 3


def test_walk_bases_empty() -> None:
    state = encode(0, (False, False, False))
    new_state, runs = transition(state, "BB")
    assert new_state == encode(0, (True, False, False))
    assert runs == 0


def test_walk_bases_loaded_forces_in_run() -> None:
    state = encode(1, (True, True, True))
    new_state, runs = transition(state, "BB")
    assert new_state == encode(1, (True, True, True))
    assert runs == 1


def test_walk_with_1b_and_3b_no_force_from_3b() -> None:
    # 1B and 3B occupied (no 2B). Walk → batter to 1B, 1B runner to 2B,
    # nobody forced from 3B (2B was empty before push).
    state = encode(0, (True, False, True))
    new_state, runs = transition(state, "BB")
    # BB cascade: batter→1B, prior 1B→2B, no force from 3B since 2B was empty
    assert new_state == encode(0, (True, True, True))
    assert runs == 0


def test_dp_with_runner_on_1b_double_out() -> None:
    state = encode(0, (True, False, False))
    new_state, runs = transition(state, "OUT_IN_PLAY", force_dp=True)
    # DP: batter out + 1B runner out → outs += 2, 1B clears
    assert new_state == encode(2, (False, False, False))
    assert runs == 0


def test_dp_at_1_out_ends_inning() -> None:
    state = encode(1, (True, False, False))
    new_state, runs = transition(state, "OUT_IN_PLAY", force_dp=True)
    # 1 out + DP (2 more outs) = 3 outs → inning ends
    assert new_state == INNING_ENDED
    assert runs == 0


def test_sac_fly_runner_on_3b_scores() -> None:
    state = encode(1, (False, False, True))
    new_state, runs = transition(state, "OUT_IN_PLAY", force_sac_fly=True)
    # SAC FLY: batter out, 3B runner scores
    assert new_state == encode(2, (False, False, False))
    assert runs == 1


def test_unknown_outcome_raises() -> None:
    state = encode(0, (False, False, False))
    with pytest.raises(ValueError):
        transition(state, "INVALID_OUTCOME")


def test_hbp_same_as_walk_bases_empty() -> None:
    """HBP behaves like BB — batter to 1B."""
    state = encode(0, (False, False, False))
    new_state, runs = transition(state, "HBP")
    assert new_state == encode(0, (True, False, False))
    assert runs == 0


def test_out_in_play_no_special_just_increments_outs() -> None:
    state = encode(0, (True, True, False))
    new_state, runs = transition(state, "OUT_IN_PLAY")
    assert new_state == encode(1, (True, True, False))
    assert runs == 0


def test_out_in_play_two_outs_ends_inning() -> None:
    state = encode(2, (False, True, False))
    new_state, runs = transition(state, "OUT_IN_PLAY")
    assert new_state == INNING_ENDED
    assert runs == 0
