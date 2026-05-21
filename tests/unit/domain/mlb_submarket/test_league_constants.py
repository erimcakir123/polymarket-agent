from src.domain.mlb_submarket.league_constants import LEAGUE_PA_RATES


def test_league_pa_rates_sum_to_one() -> None:
    assert abs(sum(LEAGUE_PA_RATES.values()) - 1.0) < 1e-3


def test_league_pa_rates_all_positive() -> None:
    for rate in LEAGUE_PA_RATES.values():
        assert rate > 0


def test_league_pa_rates_keys_complete() -> None:
    expected = {"K", "BB", "HBP", "HR", "1B", "2B", "3B", "OUT_IN_PLAY"}
    assert set(LEAGUE_PA_RATES.keys()) == expected
