"""Source health state machine — fallback ve recovery."""
from __future__ import annotations
from pathlib import Path
import pytest

from src.infrastructure.data.basketball.data_source_health import (
    HealthTracker, FALLBACK_THRESHOLD,
)


def test_initial_status_is_active(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    assert tr.is_active("nba_api") is True
    assert tr.consecutive_fails("nba_api") == 0


def test_record_failure_increments_counter(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    tr.record_failure("nba_api", at_utc="2024-11-01T00:00:00Z")
    assert tr.consecutive_fails("nba_api") == 1
    assert tr.is_active("nba_api") is True  # threshold altında


def test_threshold_failures_deactivate_source(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    for i in range(FALLBACK_THRESHOLD):
        tr.record_failure("nba_api", at_utc=f"2024-11-01T0{i}:00:00Z")
    assert tr.is_active("nba_api") is False


def test_success_resets_fail_counter(tmp_path: Path):
    tr = HealthTracker(tmp_path / "h.json")
    tr.record_failure("nba_api", at_utc="2024-11-01T00:00:00Z")
    tr.record_failure("nba_api", at_utc="2024-11-01T01:00:00Z")
    tr.record_success("nba_api", at_utc="2024-11-01T02:00:00Z")
    assert tr.consecutive_fails("nba_api") == 0
    assert tr.is_active("nba_api") is True


def test_state_persists_across_instances(tmp_path: Path):
    p = tmp_path / "h.json"
    tr1 = HealthTracker(p)
    tr1.record_failure("nba_api", at_utc="2024-11-01T00:00:00Z")
    tr2 = HealthTracker(p)
    assert tr2.consecutive_fails("nba_api") == 1
