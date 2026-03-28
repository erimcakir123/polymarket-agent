"""Centralized API usage tracker -- writes to logs/api_usage.json."""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

USAGE_FILE = Path("logs/api_usage.json")

_lock = Lock()


def _load() -> dict:
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save(data: dict) -> None:
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = USAGE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(USAGE_FILE)
    except OSError as e:
        logger.warning("Failed to save api_usage: %s", e)


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _current_hour() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")


def record_call(api_name: str, calls: int = 1) -> None:
    """Record API call(s). Thread-safe."""
    with _lock:
        data = _load()
        month = _current_month()
        hour = _current_hour()

        if api_name not in data:
            data[api_name] = {}

        entry = data[api_name]

        # Reset if month changed
        if entry.get("month") != month:
            entry["month"] = month
            entry["monthly_calls"] = 0

        # Reset if hour changed (for hourly-limited APIs like PandaScore)
        if entry.get("hour") != hour:
            entry["hour"] = hour
            entry["hourly_calls"] = 0

        entry["monthly_calls"] = entry.get("monthly_calls", 0) + calls
        entry["hourly_calls"] = entry.get("hourly_calls", 0) + calls
        entry["total_calls"] = entry.get("total_calls", 0) + calls
        entry["last_call"] = datetime.now(timezone.utc).isoformat()

        _save(data)


def get_usage() -> dict:
    """Get current usage for all APIs."""
    with _lock:
        data = _load()
        month = _current_month()
        hour = _current_hour()

        # Define API limits
        limits = {
            "claude": {"monthly_limit": None, "label": "Claude AI"},
            "pandascore": {"monthly_limit": None, "hourly_limit": 1000, "label": "PandaScore"},
            "odds_api": {"monthly_limit": 500, "label": "The Odds API"},
            "espn": {"monthly_limit": None, "label": "ESPN"},
            "vlr": {"monthly_limit": None, "label": "VLR.gg"},
            "hltv": {"monthly_limit": None, "label": "HLTV"},
            "sportsgameodds": {"monthly_limit": 2500, "label": "SportsGameOdds"},
        }

        result = {}
        for api_name, info in limits.items():
            entry = data.get(api_name, {})
            # Reset stale months
            m_calls = entry.get("monthly_calls", 0) if entry.get("month") == month else 0
            h_calls = entry.get("hourly_calls", 0) if entry.get("hour") == hour else 0

            result[api_name] = {
                "label": info["label"],
                "monthly_calls": m_calls,
                "monthly_limit": info.get("monthly_limit"),
                "hourly_calls": h_calls,
                "hourly_limit": info.get("hourly_limit"),
                "total_calls": entry.get("total_calls", 0),
                "last_call": entry.get("last_call"),
            }

        return result
