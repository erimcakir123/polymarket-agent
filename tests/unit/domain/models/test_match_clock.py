"""MatchClock domain modeli için unit testler."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from src.domain.models.match_clock import MatchClock, build_match_clock


@dataclass
class _FakeScore:
    """ESPNMatchScore duck-type (sadece test için)."""
    is_completed: bool = False
    is_live: bool = True
    period_number: int | None = None
    clock_seconds: int | None = None
    minute: int | None = None
    inning: int | None = None
    inning_half: str | None = None
    sets_won_home: int | None = None
    sets_won_away: int | None = None
    current_set: int | None = None
    games_home: int | None = None
    games_away: int | None = None


_BASE_CFG_NBA = {"espn_sport": "basketball", "match_duration_hours": 2.5}
_BASE_CFG_NHL = {"espn_sport": "hockey", "match_duration_hours": 2.5}
_BASE_CFG_MLB = {"espn_sport": "baseball", "match_duration_hours": 3.0}
_BASE_CFG_SOC = {"espn_sport": "soccer", "match_duration_hours": 2.0}
_BASE_CFG_TEN = {"espn_sport": "tennis", "match_duration_hours": 2.5}


def test_build_match_clock_none_score_none_start_returns_zero_pct():
    clock = build_match_clock(
        espn_score=None,
        match_start_iso=None,
        sport_tag="nba",
        sport_config=_BASE_CFG_NBA,
    )
    assert clock.elapsed_pct == 0.0
    assert clock.period_number is None
    assert clock.clock_seconds is None
    assert clock.match_minute is None
    assert clock.inning is None
    assert clock.sets_won_us is None
    assert not clock.is_finished
    assert not clock.is_overtime


def test_build_match_clock_nba_q4_not_overtime():
    score = _FakeScore(period_number=4, clock_seconds=130)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="nba",
        sport_config=_BASE_CFG_NBA,
    )
    assert clock.period_number == 4
    assert clock.clock_seconds == 130
    assert clock.regulation_periods == 4
    assert not clock.is_overtime


def test_build_match_clock_nba_ot_is_overtime():
    score = _FakeScore(period_number=5, clock_seconds=60)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="nba",
        sport_config=_BASE_CFG_NBA,
    )
    assert clock.period_number == 5
    assert clock.is_overtime
    assert clock.regulation_periods == 4


def test_build_match_clock_nhl_ot_is_overtime():
    score = _FakeScore(period_number=4, clock_seconds=45)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="nhl",
        sport_config=_BASE_CFG_NHL,
    )
    assert clock.period_number == 4
    assert clock.regulation_periods == 3
    assert clock.is_overtime


def test_build_match_clock_mlb_extra_innings_is_overtime():
    score = _FakeScore(inning=10, inning_half="top")
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="mlb",
        sport_config=_BASE_CFG_MLB,
    )
    assert clock.inning == 10
    assert clock.inning_half == "top"
    assert clock.regulation_periods == 9
    assert clock.is_overtime


def test_build_match_clock_soccer_extra_time_is_overtime():
    score = _FakeScore(minute=93)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="soccer",
        sport_config=_BASE_CFG_SOC,
    )
    assert clock.match_minute == 93
    assert clock.regulation_periods == 2
    assert clock.is_overtime


def test_build_match_clock_soccer_normal_not_overtime():
    score = _FakeScore(minute=67)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="soccer",
        sport_config=_BASE_CFG_SOC,
    )
    assert clock.match_minute == 67
    assert not clock.is_overtime


def test_build_match_clock_tennis_sets():
    score = _FakeScore(
        sets_won_home=1,
        sets_won_away=0,
        current_set=2,
        games_home=3,
        games_away=2,
    )
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="tennis",
        sport_config=_BASE_CFG_TEN,
    )
    assert clock.sets_won_us == 1
    assert clock.sets_won_them == 0
    assert clock.current_set == 2
    assert clock.games_us == 3
    assert clock.games_them == 2
    assert not clock.is_overtime


def test_build_match_clock_unknown_sport_fallback_only_elapsed_pct():
    score = _FakeScore(period_number=2)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="unknown",
        sport_config={"espn_sport": "unknownsport", "match_duration_hours": 2.0},
    )
    assert clock.elapsed_pct == 0.0
    assert clock.period_number is None
    assert clock.match_minute is None


def test_build_match_clock_elapsed_pct_from_wall_clock():
    """Wall-clock elapsed_pct hesaplanır — start + 1 saat, duration 2 saat → ~0.5."""
    from datetime import datetime, timedelta, timezone
    start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    clock = build_match_clock(
        espn_score=None,
        match_start_iso=start,
        sport_tag="nba",
        sport_config={"espn_sport": "basketball", "match_duration_hours": 2.0},
    )
    assert 0.4 < clock.elapsed_pct < 0.6


def test_build_match_clock_is_finished_propagated():
    score = _FakeScore(is_completed=True, is_live=False, period_number=4, clock_seconds=0)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="nba",
        sport_config=_BASE_CFG_NBA,
    )
    assert clock.is_finished
    assert not clock.is_pregame


def test_build_match_clock_pregame_when_not_live_not_finished():
    score = _FakeScore(is_completed=False, is_live=False, period_number=None)
    clock = build_match_clock(
        espn_score=score,
        match_start_iso=None,
        sport_tag="nba",
        sport_config=_BASE_CFG_NBA,
    )
    assert clock.is_pregame
    assert not clock.is_finished
