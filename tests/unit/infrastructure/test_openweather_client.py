import os
from unittest.mock import patch, MagicMock
import pytest

from src.infrastructure.apis.openweather_client import (
    OpenWeatherClient,
    WeatherSnapshot,
)


@pytest.fixture
def client():
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test_key"}):
        return OpenWeatherClient()


def test_get_forecast_returns_snapshot(client):
    fake_response = {
        "list": [
            {
                "dt": 1730000000,
                "main": {"temp": 295.0},
                "wind": {"speed": 5.0, "deg": 180},
                "rain": {"3h": 0.5},
                "pop": 0.3,
            },
        ],
    }
    mock_resp = MagicMock(status_code=200, json=lambda: fake_response)
    with patch("requests.get", return_value=mock_resp):
        snap = client.get_forecast(lat=40.0, lon=-73.9, hours_ahead=3)
    assert snap is not None
    assert snap.rain_chance == pytest.approx(0.30, abs=0.01)
    assert snap.wind_speed_mph > 0
    assert snap.temperature_f > 60


def test_no_rain_in_response_returns_zero(client):
    fake_response = {
        "list": [{
            "dt": 1730000000,
            "main": {"temp": 290.0}, "wind": {"speed": 3.0, "deg": 90},
            "pop": 0.0,
        }],
    }
    mock_resp = MagicMock(status_code=200, json=lambda: fake_response)
    with patch("requests.get", return_value=mock_resp):
        snap = client.get_forecast(40.0, -73.9, 3)
    assert snap.rain_chance == 0.0


def test_api_failure_returns_none(client):
    with patch("requests.get", side_effect=Exception("connection error")):
        snap = client.get_forecast(40.0, -73.9, 3)
    assert snap is None


def test_non_200_returns_none(client):
    mock_resp = MagicMock(status_code=500, text="error")
    with patch("requests.get", return_value=mock_resp):
        snap = client.get_forecast(40.0, -73.9, 3)
    assert snap is None


def test_missing_api_key_returns_none_forecast():
    """Missing env var → client instantiates, get_forecast returns None gracefully."""
    with patch.dict(os.environ, {}, clear=True):
        client = OpenWeatherClient()
        assert client.api_key is None
        result = client.get_forecast(40.0, -73.9, 3)
        assert result is None
