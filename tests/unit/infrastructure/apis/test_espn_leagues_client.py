"""PLAN-012: ESPN soccer leagues client tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.infrastructure.apis.espn_leagues_client import fetch_soccer_leagues


def _mock_resp(status_code: int = 200, json_data: dict | None = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    return resp


class TestFetchSoccerLeagues:
    def test_parses_league_slugs_from_items(self):
        items = [
            {"$ref": "http://sports.core.api.espn.com/v2/sports/soccer/leagues/arg.1?lang=en"},
            {"$ref": "http://sports.core.api.espn.com/v2/sports/soccer/leagues/rus.1?lang=en"},
            {"$ref": "http://sports.core.api.espn.com/v2/sports/soccer/leagues/uefa.champions"},
        ]
        http_get = MagicMock(return_value=_mock_resp(200, {"count": 3, "items": items}))
        result = fetch_soccer_leagues(http_get=http_get)
        assert result == ["arg.1", "rus.1", "uefa.champions"]

    def test_network_exception_returns_empty_list(self):
        http_get = MagicMock(side_effect=RuntimeError("connection refused"))
        result = fetch_soccer_leagues(http_get=http_get)
        assert result == []

    def test_http_error_returns_empty_list(self):
        resp = _mock_resp(500)
        resp.raise_for_status.side_effect = RuntimeError("HTTP 500")
        http_get = MagicMock(return_value=resp)
        result = fetch_soccer_leagues(http_get=http_get)
        assert result == []

    def test_malformed_response_returns_empty(self):
        http_get = MagicMock(return_value=_mock_resp(200, {"unexpected": "shape"}))
        assert fetch_soccer_leagues(http_get=http_get) == []

    def test_empty_items_returns_empty(self):
        http_get = MagicMock(return_value=_mock_resp(200, {"count": 0, "items": []}))
        assert fetch_soccer_leagues(http_get=http_get) == []

    def test_items_without_ref_are_skipped(self):
        items = [
            {"$ref": "http://sports.core.api.espn.com/v2/sports/soccer/leagues/arg.1"},
            {"other": "key"},  # no $ref
            {"$ref": "http://sports.core.api.espn.com/v2/sports/soccer/leagues/rus.1"},
        ]
        http_get = MagicMock(return_value=_mock_resp(200, {"items": items}))
        assert fetch_soccer_leagues(http_get=http_get) == ["arg.1", "rus.1"]
