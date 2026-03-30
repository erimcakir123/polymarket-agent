"""Tests for _hours_to_start with match_start_iso priority."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from src.entry_gate import _hours_to_start


def test_match_start_iso_used_when_present():
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    market = SimpleNamespace(
        match_start_iso=future.isoformat(),
        end_date_iso=(future + timedelta(hours=24)).isoformat(),
    )
    hours = _hours_to_start(market)
    assert 1.9 < hours < 2.1


def test_falls_back_to_end_date_iso():
    future = datetime.now(timezone.utc) + timedelta(hours=5)
    market = SimpleNamespace(match_start_iso="", end_date_iso=future.isoformat())
    hours = _hours_to_start(market)
    assert 4.9 < hours < 5.1


def test_returns_99_when_both_empty():
    market = SimpleNamespace(match_start_iso="", end_date_iso="")
    assert _hours_to_start(market) == 99.0


def test_negative_hours_for_past_match():
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    market = SimpleNamespace(match_start_iso=past.isoformat(), end_date_iso="")
    hours = _hours_to_start(market)
    assert -3.1 < hours < -2.9


def test_z_suffix_handled():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_str = future.strftime("%Y-%m-%dT%H:%M:%SZ")
    market = SimpleNamespace(match_start_iso=iso_str, end_date_iso="")
    hours = _hours_to_start(market)
    assert 0.9 < hours < 1.1
