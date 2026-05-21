from src.domain.mlb_submarket.handedness_adjust import platoon_multiplier


def test_lvl_k_increase() -> None:
    # Left batter vs Left pitcher: K rate up ~15%
    assert platoon_multiplier("L", "L", "K") == 1.15


def test_lvr_hr_increase() -> None:
    # Left batter vs Right pitcher: classic platoon advantage, HR up
    assert platoon_multiplier("L", "R", "HR") == 1.08


def test_switch_batter_uses_opposite() -> None:
    # Switch batter facing Right pitcher → bats Left → uses LvR
    assert platoon_multiplier("S", "R", "HR") == platoon_multiplier("L", "R", "HR")
    # Switch batter facing Left pitcher → bats Right → uses RvL
    assert platoon_multiplier("S", "L", "HR") == platoon_multiplier("R", "L", "HR")


def test_unknown_outcome_returns_one() -> None:
    assert platoon_multiplier("R", "R", "UNKNOWN_OUTCOME") == 1.0


def test_unknown_hand_returns_one() -> None:
    assert platoon_multiplier("X", "R", "K") == 1.0
    assert platoon_multiplier("R", "X", "K") == 1.0
