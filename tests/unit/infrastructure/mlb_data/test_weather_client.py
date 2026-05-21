"""Tests for WeatherClient — Open-Meteo raw conditions.

SPEC-R Plan 3 T3. TDD: tests written before implementation.
"""
import pytest
import requests
from unittest.mock import patch, MagicMock

from src.infrastructure.mlb_data.weather_client import WeatherClient, WeatherError


def _mock_response(status: int, json_data: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data or {}
    return r


def _sample_forecast() -> dict:
    return {
        "hourly": {
            "time": ["2026-05-21T18:00", "2026-05-21T19:00", "2026-05-21T20:00"],
            "temperature_2m": [20.0, 25.0, 22.0],          # 25°C = 77°F
            "relative_humidity_2m": [50, 55, 60],
            "wind_speed_10m": [16.0934, 8.0467, 10.0],     # 16.0934 km/h ≈ 10 mph
            "wind_direction_10m": [180.0, 90.0, 0.0],
        }
    }


def test_get_conditions_exact_match() -> None:
    with patch("src.infrastructure.mlb_data.weather_client.requests.get") as m:
        m.return_value = _mock_response(200, _sample_forecast())
        c = WeatherClient().get_conditions(40.0, -73.0, "2026-05-21T19:00")
    assert abs(c["temp_f"] - 77.0) < 0.5    # 25°C ≈ 77°F
    assert c["humidity_pct"] == 55
    assert abs(c["wind_mph"] - 5.0) < 0.1   # 8.0467 km/h ≈ 5 mph
    assert c["wind_dir_deg"] == 90.0


def test_get_conditions_celsius_to_fahrenheit() -> None:
    with patch("src.infrastructure.mlb_data.weather_client.requests.get") as m:
        m.return_value = _mock_response(200, _sample_forecast())
        c = WeatherClient().get_conditions(40.0, -73.0, "2026-05-21T18:00")
    assert abs(c["temp_f"] - 68.0) < 0.5   # 20°C = 68°F


def test_get_conditions_kmh_to_mph() -> None:
    with patch("src.infrastructure.mlb_data.weather_client.requests.get") as m:
        m.return_value = _mock_response(200, _sample_forecast())
        c = WeatherClient().get_conditions(40.0, -73.0, "2026-05-21T18:00")
    assert abs(c["wind_mph"] - 10.0) < 0.1   # 16.0934 km/h ≈ 10 mph


def test_time_outside_forecast_raises() -> None:
    with patch("src.infrastructure.mlb_data.weather_client.requests.get") as m:
        m.return_value = _mock_response(200, _sample_forecast())
        with pytest.raises(ValueError):
            WeatherClient().get_conditions(40.0, -73.0, "2026-05-22T19:00")


def test_http_error_raises() -> None:
    with patch("src.infrastructure.mlb_data.weather_client.requests.get") as m:
        m.return_value = _mock_response(500)
        with pytest.raises(WeatherError):
            WeatherClient().get_conditions(40.0, -73.0, "2026-05-21T19:00")


def test_timeout_raises() -> None:
    with patch("src.infrastructure.mlb_data.weather_client.requests.get") as m:
        m.side_effect = requests.Timeout()
        with pytest.raises(WeatherError):
            WeatherClient().get_conditions(40.0, -73.0, "2026-05-21T19:00")
