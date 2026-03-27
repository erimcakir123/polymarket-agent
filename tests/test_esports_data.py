"""Tests for PandaScore esports data client."""
from unittest.mock import MagicMock, patch

import requests as req_lib

from src.esports_data import EsportsDataClient


def test_pandascore_retries_on_500():
    """PandaScore should retry once on 500 error before giving up."""
    client = EsportsDataClient.__new__(EsportsDataClient)
    client.api_key = "test-key"
    client._cache = {}
    client._cache_ttl = 1800
    client._last_call = 0.0
    client._session = req_lib.Session()

    mock_resp_500 = MagicMock()
    mock_resp_500.raise_for_status.side_effect = req_lib.exceptions.HTTPError("500 Server Error")
    mock_resp_500.status_code = 500

    mock_resp_ok = MagicMock()
    mock_resp_ok.raise_for_status = MagicMock()
    mock_resp_ok.json.return_value = [{"id": 1, "name": "Test Match"}]
    mock_resp_ok.status_code = 200

    with patch.object(client._session, "get", side_effect=[mock_resp_500, mock_resp_ok]) as mock_get:
        with patch("time.sleep"):
            result = client._get("/matches", {})
    assert result is not None
    assert mock_get.call_count == 2


def test_pandascore_fails_after_retry():
    """PandaScore should return None after both attempts fail."""
    client = EsportsDataClient.__new__(EsportsDataClient)
    client.api_key = "test-key"
    client._cache = {}
    client._cache_ttl = 1800
    client._last_call = 0.0
    client._session = req_lib.Session()

    mock_resp_500 = MagicMock()
    mock_resp_500.raise_for_status.side_effect = req_lib.exceptions.HTTPError("500 Server Error")
    mock_resp_500.status_code = 500

    with patch.object(client._session, "get", return_value=mock_resp_500) as mock_get:
        with patch("time.sleep"):
            result = client._get("/matches", {})
    assert result is None
    assert mock_get.call_count == 2
