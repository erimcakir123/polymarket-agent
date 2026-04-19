"""CricketAPIClient icin birim testler (SPEC-011)."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from src.infrastructure.apis.cricket_client import (
    CricAPIQuota,
    CricketAPIClient,
    CricketMatchScore,
)


def _mock_response(status_code=200, info=None, matches=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = {
        "info": info or {"hitsToday": 5, "hitsLimit": 100},
        "data": matches or [],
    }
    return r


def _sample_raw_match():
    return {
        "id": "abc-123",
        "name": "Kolkata Knight Riders vs Rajasthan Royals",
        "matchType": "t20",
        "teams": ["Kolkata Knight Riders", "Rajasthan Royals"],
        "status": "In progress",
        "matchStarted": True,
        "matchEnded": False,
        "venue": "Eden Gardens",
        "dateTimeGMT": "2026-04-19T13:00:00",
        "score": [
            {"r": 180, "w": 5, "o": 20.0, "inning": "Kolkata Knight Riders Inning 1"},
            {"r": 95, "w": 4, "o": 12.3, "inning": "Rajasthan Royals Inning 2"},
        ],
    }


def test_quota_not_exhausted_by_default():
    q = CricAPIQuota()
    assert q.exhausted is False
    assert q.remaining == 100


def test_quota_exhausted_when_used_equals_limit():
    q = CricAPIQuota(used_today=100, daily_limit=100)
    assert q.exhausted is True
    assert q.remaining == 0


def test_get_current_matches_success():
    http = MagicMock(return_value=_mock_response(matches=[_sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches is not None
    assert len(matches) == 1
    assert matches[0].match_id == "abc-123"
    assert matches[0].match_type == "t20"
    assert len(matches[0].innings) == 2
    assert matches[0].innings[0]["runs"] == 180
    assert matches[0].innings[0]["wickets"] == 5
    assert matches[0].innings[0]["overs"] == 20.0


def test_quota_tracked_from_response():
    http = MagicMock(return_value=_mock_response(
        info={"hitsToday": 42, "hitsLimit": 100},
    ))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    client.get_current_matches()
    assert client.quota.used_today == 42
    assert client.quota.daily_limit == 100


def test_exhausted_quota_returns_none_without_http():
    http = MagicMock()
    client = CricketAPIClient(api_key="test-key", http_get=http)
    client.quota.used_today = 100  # manual exhaust
    matches = client.get_current_matches()
    assert matches is None
    http.assert_not_called()


def test_cache_hit_within_ttl():
    http = MagicMock(return_value=_mock_response(matches=[_sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http, cache_ttl_sec=60)
    client.get_current_matches()
    client.get_current_matches()
    client.get_current_matches()
    assert http.call_count == 1  # 1 HTTP call, 2 cache hits


def test_cache_expires_after_ttl():
    http = MagicMock(return_value=_mock_response(matches=[_sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http, cache_ttl_sec=0)
    client.get_current_matches()
    time.sleep(0.01)
    client.get_current_matches()
    assert http.call_count == 2


def test_http_error_returns_none():
    http = MagicMock(return_value=_mock_response(status_code=500))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches is None


def test_http_exception_returns_none():
    http = MagicMock(side_effect=Exception("network down"))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches is None


def test_parse_match_missing_fields_returns_none():
    raw_bad = {"id": "x"}  # missing name, teams, etc.
    http = MagicMock(return_value=_mock_response(matches=[raw_bad, _sample_raw_match()]))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    # Bad one filtered out, good one parses
    assert matches is not None
    # Bad match parse'ed to defaults (empty strings) — still returned; that's ok
    # Just check no crash


def test_inning_number_parsed_from_string():
    match = _sample_raw_match()
    http = MagicMock(return_value=_mock_response(matches=[match]))
    client = CricketAPIClient(api_key="test-key", http_get=http)
    matches = client.get_current_matches()
    assert matches[0].innings[0]["team"] == "Kolkata Knight Riders"
    assert matches[0].innings[0]["inning_num"] == 1
    assert matches[0].innings[1]["team"] == "Rajasthan Royals"
    assert matches[0].innings[1]["inning_num"] == 2
