"""Tests for StatsApiClient — MLB Stats API wrapper.

SPEC-R Plan 3 T1. TDD: tests written before implementation.
"""
import pytest
import requests
from unittest.mock import patch, MagicMock

from src.infrastructure.mlb_data.statsapi_client import StatsApiClient, StatsApiError


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def test_schedule_returns_games_list() -> None:
    fake = {"dates": [{"games": [
        {"gamePk": 12345, "teams": {"home": {"team": {"id": 1}}, "away": {"team": {"id": 2}}},
         "status": {"abstractGameState": "Preview"}},
    ]}]}
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        client = StatsApiClient()
        games = client.get_schedule("2026-05-21")
    assert len(games) == 1
    assert games[0]["gamePk"] == 12345


def test_schedule_empty_dates_returns_empty() -> None:
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, {"dates": []})
        games = StatsApiClient().get_schedule("2026-05-21")
    assert games == []


def test_404_raises() -> None:
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(404)
        with pytest.raises(StatsApiError):
            StatsApiClient().get_schedule("2026-05-21")


def test_429_retries_then_succeeds() -> None:
    responses = [_mock_response(429), _mock_response(429), _mock_response(200, {"dates": []})]
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m, \
         patch("src.infrastructure.mlb_data.statsapi_client.time.sleep"):
        m.side_effect = responses
        result = StatsApiClient(max_retries=3).get_schedule("2026-05-21")
    assert result == []
    assert m.call_count == 3


def test_persistent_5xx_raises_after_max_retries() -> None:
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m, \
         patch("src.infrastructure.mlb_data.statsapi_client.time.sleep"):
        m.return_value = _mock_response(500)
        with pytest.raises(StatsApiError):
            StatsApiClient(max_retries=2).get_schedule("2026-05-21")


def test_timeout_retries() -> None:
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m, \
         patch("src.infrastructure.mlb_data.statsapi_client.time.sleep"):
        m.side_effect = [requests.Timeout(), _mock_response(200, {"dates": []})]
        result = StatsApiClient(max_retries=2).get_schedule("2026-05-21")
    assert result == []


def test_get_game_feed() -> None:
    fake = {"liveData": {"linescore": {"currentInning": 5}}}
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        feed = StatsApiClient().get_game_feed(12345)
    assert feed["liveData"]["linescore"]["currentInning"] == 5


def test_get_lineup_extracts_batting_order() -> None:
    fake = {
        "liveData": {"boxscore": {"teams": {
            "home": {"battingOrder": [100, 101, 102, 103, 104, 105, 106, 107, 108]},
            "away": {"battingOrder": [200, 201, 202, 203, 204, 205, 206, 207, 208]},
        }}}
    }
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        lineup = StatsApiClient().get_lineup(12345)
    assert lineup["home"] == [100, 101, 102, 103, 104, 105, 106, 107, 108]
    assert lineup["away"][0] == 200


def test_get_lineup_returns_empty_if_not_posted() -> None:
    # boxscore present but battingOrder missing/empty
    fake = {"liveData": {"boxscore": {"teams": {"home": {}, "away": {}}}}}
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        lineup = StatsApiClient().get_lineup(12345)
    assert lineup == {"home": [], "away": []}


def test_get_player_handedness_basic() -> None:
    fake = {"people": [{"id": 12345, "batSide": {"code": "L"}, "pitchHand": {"code": "R"}}]}
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        h = StatsApiClient().get_player_handedness(12345)
    assert h == {"bat_side": "L", "pitch_hand": "R"}


def test_get_player_handedness_switch_batter() -> None:
    fake = {"people": [{"id": 12345, "batSide": {"code": "S"}, "pitchHand": {"code": "R"}}]}
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        h = StatsApiClient().get_player_handedness(12345)
    assert h["bat_side"] == "S"


def test_get_player_handedness_missing_fields_default_R() -> None:
    """Defensive: missing batSide/pitchHand → default 'R'."""
    fake = {"people": [{"id": 12345}]}
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, fake)
        h = StatsApiClient().get_player_handedness(12345)
    assert h == {"bat_side": "R", "pitch_hand": "R"}


def test_get_player_handedness_empty_people_list() -> None:
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(200, {"people": []})
        h = StatsApiClient().get_player_handedness(12345)
    assert h == {"bat_side": "R", "pitch_hand": "R"}


def test_get_player_handedness_404_raises() -> None:
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(404)
        with pytest.raises(StatsApiError):
            StatsApiClient().get_player_handedness(99999)
