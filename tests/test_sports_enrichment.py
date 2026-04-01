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


class TestGetStandingsContext:
    def test_returns_standings_dict(self):
        client = _make_client()
        mock_response = {
            "children": [{
                "standings": {
                    "entries": [{
                        "team": {"id": "13", "displayName": "Los Angeles Lakers",
                                 "abbreviation": "LAL"},
                        "stats": [
                            {"abbreviation": "W", "value": 38},
                            {"abbreviation": "L", "value": 29},
                            {"abbreviation": "PCT", "value": 0.567},
                            {"abbreviation": "STRK", "displayValue": "W3"},
                            {"abbreviation": "L10", "displayValue": "7-3"},
                            {"abbreviation": "GB", "value": 5.0},
                            {"abbreviation": "HOME", "displayValue": "22-10"},
                            {"abbreviation": "AWAY", "displayValue": "16-19"},
                        ],
                    }]
                }
            }]
        }
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is not None
        assert result["wins"] == 38
        assert result["losses"] == 29
        assert result["home_record"] == "22-10"
        assert result["away_record"] == "16-19"
        assert result["streak"] == "W3"

    def test_returns_none_on_api_error(self):
        client = _make_client()
        with patch.object(client, "_get", return_value=None):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is None

    def test_returns_none_when_team_not_found(self):
        client = _make_client()
        mock_response = {"children": [{"standings": {"entries": [{
            "team": {"id": "999", "displayName": "Other", "abbreviation": "OTH"},
            "stats": [],
        }]}}]}
        with patch.object(client, "_get", return_value=mock_response):
            result = client.get_standings_context("basketball", "nba", "13")
        assert result is None

    def test_uses_correct_url_path(self):
        """Must use /apis/v2/ not /apis/site/v2/."""
        client = _make_client()
        with patch.object(client, "_get", return_value=None) as mock_get:
            client.get_standings_context("basketball", "nba", "13")
            call_url = mock_get.call_args[0][0]
            assert "/apis/v2/sports/" in call_url
            assert "/standings" in call_url
