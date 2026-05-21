from src.domain.mlb_submarket.tto_adjust import tto_multiplier


def test_first_tto_no_change() -> None:
    for outcome in ("K", "BB", "HR", "1B", "OUT_IN_PLAY"):
        assert tto_multiplier(1, outcome) == 1.0


def test_third_tto_k_drops() -> None:
    assert tto_multiplier(3, "K") == 0.92


def test_third_tto_hr_rises() -> None:
    assert tto_multiplier(3, "HR") == 1.12


def test_clip_at_4_tto() -> None:
    # 4+ TTO uses 3TT multipliers (or capped)
    assert tto_multiplier(5, "K") == tto_multiplier(3, "K")
    assert tto_multiplier(10, "HR") == tto_multiplier(3, "HR")


def test_unknown_outcome_returns_one() -> None:
    assert tto_multiplier(3, "UNKNOWN") == 1.0


def test_zero_or_negative_tto_returns_one() -> None:
    assert tto_multiplier(0, "K") == 1.0
    assert tto_multiplier(-1, "K") == 1.0
