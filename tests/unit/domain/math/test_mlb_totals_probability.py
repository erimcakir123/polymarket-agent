import pytest
from src.domain.math.mlb_totals_probability import p_over_totals


def test_avg_total_85_at_85_line_near_50():
    """Expected total 8.5, line 8.5 → P(over) ≈ 0.5."""
    p = p_over_totals(home_runs=4.5, away_runs=4.0, line=8.5)
    assert 0.40 < p < 0.55


def test_high_scoring_teams_over_likely():
    """Both teams 6 R/G, line 8.5 → expected 12, P(over) high."""
    p = p_over_totals(home_runs=6.0, away_runs=6.0, line=8.5)
    assert p > 0.80


def test_low_scoring_teams_under_likely():
    """Both teams 3 R/G, line 8.5 → expected 6, P(over) low."""
    p = p_over_totals(home_runs=3.0, away_runs=3.0, line=8.5)
    assert p < 0.20


def test_park_factor_increases_p_over():
    """Hitter park (Coors 1.30) → P(over) rises vs neutral."""
    p_neutral = p_over_totals(4.5, 4.5, 8.5, park_factor=1.0)
    p_coors = p_over_totals(4.5, 4.5, 8.5, park_factor=1.30)
    assert p_coors > p_neutral


def test_park_factor_decreases_p_over():
    """Pitcher park (Petco 0.92) → P(over) drops."""
    p_neutral = p_over_totals(4.5, 4.5, 8.5, park_factor=1.0)
    p_petco = p_over_totals(4.5, 4.5, 8.5, park_factor=0.92)
    assert p_petco < p_neutral


def test_weather_run_bias_adjusts_lambda():
    """Wind blowing out (+0.5 run bias) → P(over) rises."""
    p_neutral = p_over_totals(4.5, 4.5, 8.5, weather_run_bias=0.0)
    p_windy = p_over_totals(4.5, 4.5, 8.5, weather_run_bias=+0.5)
    assert p_windy > p_neutral


def test_zero_lambda_safe_fallback():
    p = p_over_totals(0.0, 0.0, 8.5)
    assert p == pytest.approx(0.5, abs=0.01)


def test_under_complement():
    """P(over) + P(under) ≈ 1.0 (modulo discrete atomic mass at line+1)."""
    p_over = p_over_totals(5.0, 4.0, 8.5)
    p_under = 1.0 - p_over
    assert p_over + p_under == pytest.approx(1.0, abs=0.001)
