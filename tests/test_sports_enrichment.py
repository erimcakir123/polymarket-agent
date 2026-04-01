"""Tests for ESPN data enrichment methods in SportsDataClient."""
from unittest.mock import patch, MagicMock
from src.sports_data import SportsDataClient


def _make_client() -> SportsDataClient:
    """Create SportsDataClient with rate limit disabled."""
    client = SportsDataClient()
    client._last_call = 0.0
    return client


class TestGetTeamInjuries:
    def test_returns_injury_list(self):
        client = _make_client()
        mock_response = {
            "injuries": [
                {
                    "athlete": {
                        "displayName": "Stephen Curry",
                        "position": {"abbreviation": "SG"},
                    },
                    "status": "Doubtful",
                    "type": {"description": "Knee"},
                    "detail": "Left knee soreness",
                }
            ]
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_team_injuries("basketball", "nba", "10")
        assert len(result) == 1
        assert result[0]["player"] == "Stephen Curry"
        assert result[0]["status"] == "Doubtful"
        assert result[0]["detail"] == "Left knee soreness"
        assert result[0]["position"] == "SG"

    def test_skips_unsupported_sports(self):
        client = _make_client()
        result = client.get_team_injuries("tennis", "atp", "123")
        assert result == []
        result = client.get_team_injuries("mma", "ufc", "456")
        assert result == []

    def test_returns_empty_on_api_error(self):
        client = _make_client()
        with patch.object(client, "_get", return_value=None):
            result = client.get_team_injuries("basketball", "nba", "10")
        assert result == []

    def test_returns_empty_on_no_injuries(self):
        client = _make_client()
        with patch.object(client, "_get", return_value={"injuries": []}):
            result = client.get_team_injuries("basketball", "nba", "10")
        assert result == []
