import pytest
from src.domain.mlb_submarket.weather_adjust import weather_hr_multiplier


def test_baseline_returns_near_one() -> None:
    # 0 wind, 60°F, 50% humidity = baseline
    assert abs(weather_hr_multiplier(0, 60, 50) - 1.0) < 0.01


def test_strong_cf_wind_increases_hr() -> None:
    # Strong wind out to CF (positive value) → HR up
    assert weather_hr_multiplier(15, 80, 30) > 1.0


def test_wind_in_decreases_hr() -> None:
    # Negative wind (toward home) → HR down
    assert weather_hr_multiplier(-10, 50, 80) < 1.0


def test_extreme_wind_clipped() -> None:
    # 50 mph wind should be clipped to max ~1.5
    assert weather_hr_multiplier(50, 90, 20) <= 1.5


def test_extreme_cold_clipped() -> None:
    # Very cold + wind in → clipped to min ~0.5
    assert weather_hr_multiplier(-30, 30, 90) >= 0.5
