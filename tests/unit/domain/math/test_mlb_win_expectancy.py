import pytest
from src.domain.math.mlb_win_expectancy import (
    encode_base_state,
    lookup_win_expectancy,
)


def test_empty_bases_encodes_zero():
    assert encode_base_state(False, False, False) == 0


def test_first_only_encodes_one():
    assert encode_base_state(True, False, False) == 1


def test_bases_loaded_encodes_seven():
    assert encode_base_state(True, True, True) == 7


def test_all_combinations_unique():
    """All 8 base states produce unique encodings 0-7."""
    seen = set()
    for f in (False, True):
        for s in (False, True):
            for t in (False, True):
                seen.add(encode_base_state(f, s, t))
    assert seen == set(range(8))


def test_top_1_tied_home_advantage():
    """Top 1, tied → home WE > 0.5 (home batting advantage)."""
    we = lookup_win_expectancy(inning=1, outs=0, base_state=0, run_diff=0, is_home=True)
    assert we > 0.5


def test_m1_territory_inning_7_deficit_5_almost_dead():
    """Inning 7, deficit 5 (M1 trigger) → trailing team WE near zero."""
    we_trailing = lookup_win_expectancy(inning=7, outs=0, base_state=0, run_diff=+5, is_home=False)
    assert we_trailing < 0.05


def test_m2_territory_inning_8_deficit_3_dead():
    we = lookup_win_expectancy(inning=8, outs=0, base_state=0, run_diff=+3, is_home=False)
    assert we < 0.10


def test_m3_territory_inning_9_deficit_1_low_but_alive():
    """9th inning down 1 → still alive but low."""
    we = lookup_win_expectancy(inning=9, outs=0, base_state=0, run_diff=+1, is_home=False)
    assert 0.05 < we < 0.20


def test_out_of_table_fallback_returns_neutral():
    """Unknown state → 0.5 fallback (HOLD-safe, not PREDICTIVE_DEAD-safe)."""
    we = lookup_win_expectancy(inning=99, outs=99, base_state=99, run_diff=99, is_home=True)
    assert we == 0.5


def test_clutch_bases_loaded_bot_9():
    """Bottom 9, bases loaded, down 1, 0 outs → home WE > 0.5."""
    we = lookup_win_expectancy(inning=9, outs=0, base_state=7, run_diff=-1, is_home=True)
    assert we > 0.5


def test_we_complement_for_away_team():
    """WE for home + WE for away should sum to 1.0."""
    home = lookup_win_expectancy(8, 0, 0, +2, is_home=True)
    away = lookup_win_expectancy(8, 0, 0, +2, is_home=False)
    assert home + away == pytest.approx(1.0, abs=0.001)
