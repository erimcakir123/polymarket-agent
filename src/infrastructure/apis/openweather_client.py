"""OpenWeatherMap 5-day/3-hour forecast API wrapper.

Free tier: 1000 calls/day. Cache layer (1h per stadium) implemented in
mlb_edge_enricher to stay within budget.

Returns WeatherSnapshot or None on failure (gracefully degrades).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
_REQUEST_TIMEOUT_SEC = 10
_KELVIN_TO_F_OFFSET = -273.15
_KELVIN_TO_F_FACTOR = 9.0 / 5.0
_F_OFFSET = 32.0
_MS_TO_MPH = 2.237


@dataclass(frozen=True)
class WeatherSnapshot:
    rain_chance: float
    wind_speed_mph: float
    wind_direction_deg: float
    temperature_f: float
    rain_volume_mm: float


class OpenWeatherClient:
    def __init__(self) -> None:
        self.api_key = os.environ["OPENWEATHER_API_KEY"]

    def get_forecast(
        self,
        lat: float,
        lon: float,
        hours_ahead: int,
    ) -> WeatherSnapshot | None:
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "standard"}
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=_REQUEST_TIMEOUT_SEC)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenWeather request failed (lat=%s lon=%s): %s", lat, lon, exc)
            return None

        if resp.status_code != 200:
            logger.warning("OpenWeather non-200 (%s): %s", resp.status_code, resp.text[:200])
            return None

        try:
            data = resp.json()
            slot_index = max(0, min(hours_ahead // 3, len(data["list"]) - 1))
            slot = data["list"][slot_index]

            rain_chance = float(slot.get("pop", 0.0))
            rain_vol = float(slot.get("rain", {}).get("3h", 0.0))
            wind = slot.get("wind", {})
            wind_speed_ms = float(wind.get("speed", 0.0))
            wind_deg = float(wind.get("deg", 0.0))
            temp_k = float(slot["main"]["temp"])
            temp_f = (temp_k + _KELVIN_TO_F_OFFSET) * _KELVIN_TO_F_FACTOR + _F_OFFSET

            return WeatherSnapshot(
                rain_chance=rain_chance,
                wind_speed_mph=wind_speed_ms * _MS_TO_MPH,
                wind_direction_deg=wind_deg,
                temperature_f=temp_f,
                rain_volume_mm=rain_vol,
            )
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            logger.warning("OpenWeather parse failed: %s", exc)
            return None
