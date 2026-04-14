"""odds_client.py için birim testler."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.infrastructure.apis.odds_client import OddsAPIClient


def _resp(status: int = 200, body: Any = None, headers: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if status < 400:
        r.raise_for_status = MagicMock(return_value=None)
    else:
        r.raise_for_status = MagicMock(side_effect=RuntimeError(f"http {status}"))
    r.headers = headers or {}
    r.json.return_value = body if body is not None else []
    return r


def test_client_requires_api_key() -> None:
    c = OddsAPIClient(api_key="")
    assert c.available is False
    assert c.get_sports() is None


def test_get_sports_success() -> None:
    http = MagicMock(return_value=_resp(200, body=[{"key": "basketball_nba", "active": True}],
                                         headers={"x-requests-used": "100", "x-requests-remaining": "900"}))
    c = OddsAPIClient(api_key="k", http_get=http)
    data = c.get_sports()
    assert data is not None
    assert data[0]["key"] == "basketball_nba"
    # Quota tracking
    assert c._last_used == 100
    assert c._last_remaining == 900


def test_get_odds_caches_second_call() -> None:
    http = MagicMock(return_value=_resp(200, body=[{"id": "e1"}]))
    c = OddsAPIClient(api_key="k", http_get=http)
    c.get_odds("basketball_nba")
    c.get_odds("basketball_nba")  # Cached
    # HTTP yalnız 1 kez çağrıldı
    assert http.call_count == 1


def test_get_odds_different_params_separate_cache() -> None:
    http = MagicMock(return_value=_resp(200, body=[]))
    c = OddsAPIClient(api_key="k", http_get=http)
    c.get_odds("basketball_nba", {"regions": "us"})
    c.get_odds("basketball_nba", {"regions": "eu"})
    assert http.call_count == 2


def test_http_error_returns_none() -> None:
    http = MagicMock(side_effect=RuntimeError("boom"))
    c = OddsAPIClient(api_key="k", http_get=http)
    assert c.get_sports() is None


def test_adaptive_refresh_at_70_quota() -> None:
    c = OddsAPIClient(api_key="k")
    c._last_used = 700
    c._last_remaining = 300
    assert c._current_refresh_sec() == 3 * 3600


def test_adaptive_refresh_at_90_quota() -> None:
    c = OddsAPIClient(api_key="k")
    c._last_used = 900
    c._last_remaining = 100
    assert c._current_refresh_sec() == 4 * 3600


def test_adaptive_refresh_low_quota_base() -> None:
    c = OddsAPIClient(api_key="k")
    c._last_used = 100
    c._last_remaining = 900
    assert c._current_refresh_sec() == 2 * 3600


def test_quota_used_pct() -> None:
    c = OddsAPIClient(api_key="k")
    c._last_used = 250
    c._last_remaining = 750
    assert c.quota_used_pct == 0.25


def test_quota_used_pct_none_when_unknown() -> None:
    c = OddsAPIClient(api_key="k")
    assert c.quota_used_pct is None


def test_auth_error_triggers_backup(monkeypatch) -> None:
    monkeypatch.setenv("ODDS_API_KEY_BACKUP", "backup_key")
    call_count = [0]

    def _http(url: str, params: dict, timeout: int) -> Any:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("401 unauthorized")
        return _resp(200, body=[{"ok": True}])

    c = OddsAPIClient(api_key="bad_key", http_get=_http)
    data = c.get_sports()
    assert data is not None
    assert c._using_backup is True
    assert c.api_key == "backup_key"
