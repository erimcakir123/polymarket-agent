import math
from src.domain.mlb_submarket.rate_shrinker import marcel_weighted_rates


def test_marcel_weights_three_seasons():
    current = {"hr_rate": 0.04, "pa": 600}
    prev = {"hr_rate": 0.03, "pa": 600}
    prev_prev = {"hr_rate": 0.02, "pa": 600}
    result = marcel_weighted_rates(current, prev, prev_prev)
    # weighted hr_rate = (0.04*5*600 + 0.03*4*600 + 0.02*3*600) / (5*600 + 4*600 + 3*600)
    #                  = (120 + 72 + 36) / 7200 = 228 / 7200 ≈ 0.031667
    assert math.isclose(result["hr_rate"], 0.0316667, abs_tol=1e-4)
    assert result["pa"] == 7200


def test_marcel_missing_prev_seasons_falls_back_to_current():
    current = {"hr_rate": 0.04, "pa": 600}
    result = marcel_weighted_rates(current, {}, {})
    assert result == current


def test_marcel_missing_prev_prev_uses_2_seasons():
    current = {"hr_rate": 0.04, "pa": 600}
    prev = {"hr_rate": 0.03, "pa": 600}
    result = marcel_weighted_rates(current, prev, {})
    # weighted hr_rate = (0.04*5*600 + 0.03*4*600) / (5*600 + 4*600)
    #                  = (120 + 72) / 5400 = 192/5400 ≈ 0.035556
    assert math.isclose(result["hr_rate"], 0.0355556, abs_tol=1e-4)
    assert result["pa"] == 5400


def test_marcel_handles_multiple_rate_keys():
    current = {"hr_rate": 0.04, "k_rate": 0.20, "pa": 600}
    prev = {"hr_rate": 0.03, "k_rate": 0.18, "pa": 600}
    result = marcel_weighted_rates(current, prev, {})
    assert math.isclose(result["hr_rate"], 0.0355556, abs_tol=1e-4)
    # k_rate = (0.20*5*600 + 0.18*4*600) / 5400 = (600+432)/5400 = 0.1911
    assert math.isclose(result["k_rate"], 0.1911111, abs_tol=1e-4)


def test_marcel_empty_all_returns_current():
    # All three empty (or no PA) → return current (which is also empty)
    result = marcel_weighted_rates({}, {}, {})
    assert result == {}
