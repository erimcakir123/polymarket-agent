from src.domain.mlb_submarket.lineup_order import batter_at_pa, times_through_order


def test_batter_first_pa() -> None:
    assert batter_at_pa(0) == 0


def test_batter_ninth_pa_returns_to_top() -> None:
    assert batter_at_pa(9) == 0


def test_batter_pa_14_index_5() -> None:
    # PA 14 (0-indexed → 14th batter is index 14 % 9 = 5)
    assert batter_at_pa(14) == 5


def test_tto_first_at_pa_5() -> None:
    assert times_through_order(5) == 1


def test_tto_second_at_pa_14() -> None:
    assert times_through_order(14) == 2


def test_tto_third_at_pa_22() -> None:
    assert times_through_order(22) == 3


def test_tto_fourth_at_pa_30() -> None:
    assert times_through_order(30) == 4


def test_tto_boundary_pa_9() -> None:
    # PA 9 = start of 2nd time through
    assert times_through_order(9) == 2


def test_tto_negative_returns_one() -> None:
    assert times_through_order(-1) == 1
