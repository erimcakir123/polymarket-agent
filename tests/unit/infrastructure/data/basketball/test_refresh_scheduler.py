# tests/unit/infrastructure/data/basketball/test_refresh_scheduler.py
"""Refresh scheduler — match-window aware interval kararı."""
from __future__ import annotations
from datetime import datetime, timedelta
import pytest

from src.infrastructure.data.basketball.refresh_scheduler import (
    decide_refresh_interval, RefreshIntervalSec,
)


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s)


def test_active_game_uses_short_interval():
    now = _t("2024-11-01T20:30:00")
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": None}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.LIVE


def test_post_game_window_uses_short_interval():
    now = _t("2024-11-01T23:00:00")
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": "2024-11-01T22:30:00"}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.POST_GAME


def test_post_game_window_expired_uses_idle_interval():
    now = _t("2024-11-02T00:00:00")
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": "2024-11-01T22:30:00"}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.IDLE


def test_no_games_today_uses_idle_interval():
    now = _t("2024-11-01T15:00:00")
    interval = decide_refresh_interval(now=now, games_today=[])
    assert interval == RefreshIntervalSec.IDLE


def test_game_upcoming_within_2h_uses_short_interval():
    now = _t("2024-11-01T18:30:00")  # 1.5h önce
    games_today = [{"start_utc": "2024-11-01T20:00:00", "end_utc": None}]
    interval = decide_refresh_interval(now=now, games_today=games_today)
    assert interval == RefreshIntervalSec.PRE_GAME
