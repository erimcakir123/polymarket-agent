"""Tests for NHL match clock parser."""
from __future__ import annotations

import pytest
from src.domain.sports.nhl_match_clock import (
    parse_nhl_status,
    NHLClock,
    REGULATION_TOTAL_SECONDS,
    REGULATION_PERIOD_SECONDS,
)


def _status(period: int, display_clock: str, state: str, detail: str) -> dict:
    """Build ESPN status payload mock."""
    return {
        "period": period,
        "displayClock": display_clock,
        "type": {"state": state, "detail": detail},
    }


class TestPreGame:
    def test_pre_game_no_period(self):
        c = parse_nhl_status(_status(0, "20:00", "pre", "Scheduled"))
        assert c.is_pre
        assert not c.is_live
        assert not c.is_final
        assert c.seconds_remaining_in_regulation == REGULATION_TOTAL_SECONDS

    def test_empty_status_returns_safe_default(self):
        c = parse_nhl_status({})
        assert c.is_pre
        assert c.period == 0

    def test_none_safe(self):
        c = parse_nhl_status(None)
        assert c.is_pre


class TestLiveRegulation:
    def test_p1_full_clock(self):
        c = parse_nhl_status(_status(1, "20:00", "in", "1st Period"))
        assert c.is_live
        assert c.period == 1
        assert c.seconds_remaining_in_period == 1200
        assert c.seconds_remaining_in_regulation == REGULATION_TOTAL_SECONDS

    def test_p1_mid(self):
        c = parse_nhl_status(_status(1, "10:35", "in", "1st Period"))
        assert c.period == 1
        assert c.seconds_remaining_in_period == 635
        # elapsed: 1200 - 635 = 565s in P1; remaining: 3600 - 565 = 3035
        assert c.seconds_remaining_in_regulation == 3035

    def test_p2_start(self):
        c = parse_nhl_status(_status(2, "20:00", "in", "2nd Period"))
        assert c.period == 2
        assert c.seconds_remaining_in_regulation == 2400

    def test_p2_mid(self):
        c = parse_nhl_status(_status(2, "10:00", "in", "2nd Period"))
        # elapsed: P1(1200) + 600 = 1800; remaining: 3600 - 1800 = 1800
        assert c.seconds_remaining_in_regulation == 1800

    def test_p3_last_60s(self):
        c = parse_nhl_status(_status(3, "1:00", "in", "3rd Period"))
        assert c.period == 3
        assert c.seconds_remaining_in_period == 60
        # elapsed in P3: 1200-60=1140; total: 2400+1140=3540; remaining: 60
        assert c.seconds_remaining_in_regulation == 60

    def test_p3_end_of_regulation(self):
        c = parse_nhl_status(_status(3, "0:00", "in", "3rd Period"))
        assert c.seconds_remaining_in_regulation == 0

    def test_not_overtime_in_regulation(self):
        c = parse_nhl_status(_status(2, "5:00", "in", "2nd Period"))
        assert not c.is_overtime
        assert not c.is_shootout


class TestOvertime:
    def test_live_ot_period_4(self):
        c = parse_nhl_status(_status(4, "3:30", "in", "OT"))
        assert c.is_overtime
        assert c.is_live
        assert c.period == 4
        assert c.seconds_remaining_in_regulation == 0

    def test_live_ot_detail_overtime_word(self):
        c = parse_nhl_status(_status(4, "1:23", "in", "Overtime"))
        assert c.is_overtime

    def test_final_ot(self):
        c = parse_nhl_status(_status(4, "0:00", "post", "Final/OT"))
        assert c.is_final
        assert c.ended_in_ot
        assert not c.ended_in_so
        assert c.is_overtime
        assert c.period == 4

    def test_ot_not_shootout(self):
        c = parse_nhl_status(_status(4, "2:00", "in", "OT"))
        assert not c.is_shootout


class TestShootout:
    def test_live_so_period_5(self):
        c = parse_nhl_status(_status(5, "0:00", "in", "Shootout"))
        assert c.is_shootout
        assert c.is_live
        assert c.period == 5

    def test_final_so(self):
        c = parse_nhl_status(_status(5, "0:00", "post", "Final/SO"))
        assert c.is_final
        assert c.ended_in_so
        assert not c.ended_in_ot
        assert c.is_shootout
        assert c.period == 5

    def test_so_not_overtime(self):
        c = parse_nhl_status(_status(5, "0:00", "post", "Final/SO"))
        assert not c.ended_in_ot


class TestFinal:
    def test_regulation_final(self):
        c = parse_nhl_status(_status(3, "0:00", "post", "Final"))
        assert c.is_final
        assert not c.ended_in_ot
        assert not c.ended_in_so
        assert c.period == 3

    def test_final_promotes_period_if_ot_mismatch(self):
        # Edge case: ESPN sometimes reports period=3 with detail Final/OT
        c = parse_nhl_status(_status(3, "0:00", "post", "Final/OT"))
        assert c.ended_in_ot
        assert c.period == 4

    def test_final_promotes_period_if_so_mismatch(self):
        c = parse_nhl_status(_status(3, "0:00", "post", "Final/SO"))
        assert c.ended_in_so
        assert c.period == 5

    def test_final_not_live(self):
        c = parse_nhl_status(_status(3, "0:00", "post", "Final"))
        assert not c.is_live

    def test_final_regulation_remaining_zero(self):
        c = parse_nhl_status(_status(3, "0:00", "post", "Final"))
        assert c.seconds_remaining_in_regulation == 0


class TestClockParsing:
    def test_zero_clock(self):
        c = parse_nhl_status(_status(3, "0:00", "in", "3rd Period"))
        assert c.seconds_remaining_in_period == 0

    def test_malformed_clock_safe(self):
        c = parse_nhl_status(_status(2, "garbage", "in", "2nd Period"))
        assert c.seconds_remaining_in_period == 0

    def test_missing_clock_safe(self):
        c = parse_nhl_status({"period": 2, "type": {"state": "in", "detail": "2nd Period"}})
        assert c.seconds_remaining_in_period == 0

    def test_clock_30_seconds(self):
        c = parse_nhl_status(_status(3, "0:30", "in", "3rd Period"))
        assert c.seconds_remaining_in_period == 30

    def test_full_period_clock_1200s(self):
        c = parse_nhl_status(_status(1, "20:00", "in", "1st Period"))
        assert c.seconds_remaining_in_period == 1200


class TestRawPreservation:
    def test_raw_state_and_detail_preserved(self):
        c = parse_nhl_status(_status(2, "12:34", "in", "2nd Period"))
        assert c.raw_state == "in"
        assert c.raw_detail == "2nd Period"

    def test_raw_detail_post_final_ot(self):
        c = parse_nhl_status(_status(4, "0:00", "post", "Final/OT"))
        assert c.raw_detail == "Final/OT"
        assert c.raw_state == "post"
