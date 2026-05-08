"""ESPN scoreboard client testleri (SPEC-B Task 1)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.apis.espn_client import ESPNClient, ESPNMatchScore


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def test_espn_client_initializes_with_default_timeout() -> None:
    client = ESPNClient()
    assert client._timeout > 0


def test_fetch_scoreboard_nhl_basic() -> None:
    response = {
        "events": [{
            "id": "401688123",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Maple Leafs", "id": "21"},
                     "score": "3"},
                    {"homeAway": "away", "team": {"displayName": "Bruins", "id": "1"},
                     "score": "2"},
                ],
                "status": {"period": 3, "displayClock": "0:00",
                           "type": {"name": "STATUS_FINAL", "completed": True, "state": "post"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl", date="20260508")
    assert len(scores) == 1
    s = scores[0]
    assert s.event_id == "401688123"
    assert s.home_name == "Maple Leafs"
    assert s.away_name == "Bruins"
    assert s.home_score == 3
    assert s.away_score == 2
    assert s.is_completed is True
    assert s.is_live is False


def test_fetch_scoreboard_in_progress_is_live() -> None:
    response = {
        "events": [{
            "id": "abc",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "A", "id": "1"}, "score": "1"},
                    {"homeAway": "away", "team": {"displayName": "B", "id": "2"}, "score": "0"},
                ],
                "status": {"period": 2, "displayClock": "5:30",
                           "type": {"name": "STATUS_IN_PROGRESS", "completed": False, "state": "in"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores[0].is_live is True
    assert scores[0].is_completed is False


def test_mlb_parses_inning_and_half() -> None:
    response = {
        "events": [{
            "id": "mlb1",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Yankees", "id": "10"}, "score": "5"},
                    {"homeAway": "away", "team": {"displayName": "Red Sox", "id": "2"}, "score": "3"},
                ],
                "status": {"period": 7, "displayClock": "Top 7th",
                           "shortDetail": "Top 7th",
                           "type": {"name": "STATUS_IN_PROGRESS", "completed": False, "state": "in"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("baseball", "mlb")
    assert scores[0].inning == 7
    assert scores[0].inning_half == "top"


def test_nba_parses_period_number_and_clock() -> None:
    response = {
        "events": [{
            "id": "nba1",
            "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Lakers", "id": "13"}, "score": "85"},
                    {"homeAway": "away", "team": {"displayName": "Celtics", "id": "2"}, "score": "78"},
                ],
                "status": {"period": 3, "displayClock": "5:30",
                           "type": {"name": "STATUS_IN_PROGRESS", "completed": False, "state": "in"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("basketball", "nba")
    assert scores[0].period_number == 3
    assert scores[0].clock_seconds == 5 * 60 + 30


def test_fetch_scoreboard_http_error_returns_empty_list() -> None:
    http_get = MagicMock(return_value=_mock_response({}, status_code=503))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores == []


def test_fetch_scoreboard_timeout_returns_empty_list() -> None:
    import httpx
    http_get = MagicMock(side_effect=httpx.TimeoutException("timeout"))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores == []


def test_fetch_scoreboard_invalid_json_returns_empty_list() -> None:
    http_get = MagicMock(return_value=_mock_response({}, status_code=200))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores == []


def test_score_field_missing_treated_as_none() -> None:
    response = {
        "events": [{
            "id": "x", "date": "2026-05-08T23:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "A", "id": "1"}},
                    {"homeAway": "away", "team": {"displayName": "B", "id": "2"}},
                ],
                "status": {"period": 0,
                           "type": {"name": "STATUS_SCHEDULED", "completed": False, "state": "pre"}},
            }],
        }],
    }
    http_get = MagicMock(return_value=_mock_response(response))
    client = ESPNClient(http_get=http_get)
    scores = client.fetch_scoreboard("hockey", "nhl")
    assert scores[0].home_score is None
    assert scores[0].away_score is None
