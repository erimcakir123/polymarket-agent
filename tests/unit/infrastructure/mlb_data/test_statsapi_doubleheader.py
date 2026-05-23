"""Tests for StatsApiClient.get_schedule DH-related fields (A6).

Verifies that game_type, scheduled_innings, double_header are included in
each game dict, with sensible defaults when the fields are absent.
"""
from unittest.mock import patch, MagicMock

from src.infrastructure.mlb_data.statsapi_client import StatsApiClient


def _mock_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    return resp


def test_get_schedule_includes_doubleheader_fields():
    fake = {
        "dates": [{
            "games": [{
                "gamePk": 222,
                "gameType": "D",
                "scheduledInnings": 7,
                "doubleHeader": "S",
                "status": {"abstractGameState": "Scheduled"},
                "teams": {
                    "home": {"team": {"id": 143}},
                    "away": {"team": {"id": 114}},
                },
            }],
        }],
    }
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(fake)
        client = StatsApiClient()
        games = client.get_schedule("2026-05-22")

    assert len(games) == 1
    g = games[0]
    assert g["gamePk"] == 222
    assert g["game_type"] == "D"
    assert g["scheduled_innings"] == 7
    assert g["double_header"] == "S"


def test_get_schedule_defaults_for_regular_game():
    """gameType/scheduledInnings/doubleHeader yoksa default değerler atanır."""
    fake = {
        "dates": [{
            "games": [{
                "gamePk": 100,
                "status": {"abstractGameState": "Scheduled"},
                "teams": {
                    "home": {"team": {"id": 143}},
                    "away": {"team": {"id": 114}},
                },
                # gameType, scheduledInnings, doubleHeader yok
            }],
        }],
    }
    with patch("src.infrastructure.mlb_data.statsapi_client.requests.get") as m:
        m.return_value = _mock_response(fake)
        client = StatsApiClient()
        games = client.get_schedule("2026-05-22")

    g = games[0]
    assert g["game_type"] == "R"       # default regular
    assert g["scheduled_innings"] == 9  # default 9
    assert g["double_header"] == "N"    # default no
