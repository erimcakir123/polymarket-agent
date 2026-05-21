from src.domain.mlb_submarket.transition_matrix import RE_MATRIX, expected_runs


def test_re_matrix_has_24_entries() -> None:
    assert len(RE_MATRIX) == 24


def test_all_values_positive() -> None:
    for v in RE_MATRIX.values():
        assert v >= 0


def test_initial_state_value() -> None:
    # (0 out, bases empty) well-known ≈ 0.48
    assert abs(RE_MATRIX[0] - 0.481) < 0.01


def test_bases_loaded_0_outs_highest_re() -> None:
    # (0 out, bases loaded) should be the highest RE in the matrix
    assert RE_MATRIX[7] == max(RE_MATRIX.values())


def test_2_out_bases_empty_lowest_re() -> None:
    # (2 out, bases empty) should be very low
    assert RE_MATRIX[16] == min(RE_MATRIX.values())


def test_more_runners_higher_re_at_same_outs() -> None:
    # At 0 outs: bases empty (0) < runner on 1B (1) < bases loaded (7)
    assert RE_MATRIX[0] < RE_MATRIX[1] < RE_MATRIX[7]


def test_more_outs_lower_re_at_same_runners() -> None:
    # bases empty: 0 outs (0) > 1 out (8) > 2 outs (16)
    assert RE_MATRIX[0] > RE_MATRIX[8] > RE_MATRIX[16]


def test_expected_runs_lookup() -> None:
    assert expected_runs(0) == RE_MATRIX[0]
    assert expected_runs(7) == RE_MATRIX[7]
