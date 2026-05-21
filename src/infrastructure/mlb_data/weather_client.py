"""Open-Meteo weather client (free, no API key).

SPEC-R Plan 3 T3. Returns raw conditions; CF projection deferred to Plan 4
engine (needs ballpark orientation lookup).
Infrastructure layer — I/O allowed, no domain imports.
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_KMH_TO_MPH = 0.621371


class WeatherError(Exception):
    """Raised when Open-Meteo request fails."""


class WeatherClient:
    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    def get_conditions(self, lat: float, lon: float, time_iso: str) -> dict[str, float]:
        """Fetch weather conditions for a location at a specific UTC hour.

        Args:
            lat: Latitude of venue.
            lon: Longitude of venue.
            time_iso: Target hour in 'YYYY-MM-DDTHH:MM' format (UTC, no seconds).

        Returns:
            Dict with keys:
              wind_mph: float       (converted from km/h)
              wind_dir_deg: float   (0=N, 90=E, 180=S, 270=W)
              temp_f: float         (converted from Celsius)
              humidity_pct: float

        Raises:
            WeatherError: On HTTP error or network failure.
            ValueError: If time_iso is outside the forecast window.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
            "timezone": "UTC",
        }
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=self.timeout)
        except (requests.Timeout, requests.ConnectionError) as e:
            logger.error("Open-Meteo network error for (%.4f, %.4f): %s", lat, lon, e)
            raise WeatherError(f"Open-Meteo network error: {e}") from e

        if resp.status_code != 200:
            logger.error("Open-Meteo HTTP %d for (%.4f, %.4f)", resp.status_code, lat, lon)
            raise WeatherError(f"Open-Meteo HTTP {resp.status_code}")

        logger.info("Open-Meteo (%.4f, %.4f) → 200 OK", lat, lon)
        data = resp.json()
        hourly = data.get("hourly", {})
        times: list[str] = hourly.get("time", [])

        if time_iso not in times:
            raise ValueError(
                f"time_iso {time_iso!r} not in forecast window"
                f" {times[:1]}..{times[-1:]}"
            )

        idx = times.index(time_iso)
        temp_c: float = hourly["temperature_2m"][idx]

        return {
            "wind_mph": hourly["wind_speed_10m"][idx] * _KMH_TO_MPH,
            "wind_dir_deg": float(hourly["wind_direction_10m"][idx]),
            "temp_f": temp_c * 9 / 5 + 32,
            "humidity_pct": float(hourly["relative_humidity_2m"][idx]),
        }
