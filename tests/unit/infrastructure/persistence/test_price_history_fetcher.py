"""price_history_fetcher — CLOB history endpoint normalize + filtre testleri."""
from __future__ import annotations

from typing import Any

from src.infrastructure.persistence.price_history_fetcher import fetch_price_history


class _FakeResp:
    def __init__(self, status: int, data: dict[str, Any]):
        self.status_code = status
        self._data = data

    def json(self) -> dict[str, Any]:
        return self._data


def _fake_http(resp: _FakeResp):
    def _call(url: str, params: dict, timeout: int) -> _FakeResp:  # noqa: ARG001
        return resp
    return _call


def test_fetch_returns_normalized_points_sorted():
    raw = {"history": [
        {"t": 1779350400, "p": 0.41},  # 2026-05-21T08:00:00Z
        {"t": 1779346800, "p": 0.40},  # 2026-05-21T07:00:00Z (earlier)
    ]}
    points = fetch_price_history(
        token_id="abc",
        http_get=_fake_http(_FakeResp(200, raw)),
    )
    assert len(points) == 2
    # Sorted ASC
    assert points[0]["timestamp_iso"] < points[1]["timestamp_iso"]
    assert points[0]["price"] == 0.40
    assert points[1]["price"] == 0.41


def test_fetch_filters_before_start_iso():
    raw = {"history": [
        {"t": 1779346800, "p": 0.40},  # earlier
        {"t": 1779350400, "p": 0.41},  # later
    ]}
    points = fetch_price_history(
        token_id="abc",
        start_iso="2026-05-21T07:30:00+00:00",
        http_get=_fake_http(_FakeResp(200, raw)),
    )
    assert len(points) == 1
    assert points[0]["price"] == 0.41


def test_fetch_returns_empty_on_non_200():
    points = fetch_price_history(
        token_id="abc",
        http_get=_fake_http(_FakeResp(500, {})),
    )
    assert points == []


def test_fetch_returns_empty_on_exception():
    def _raise(url, params, timeout):  # noqa: ARG001
        import requests
        raise requests.ConnectionError("boom")
    points = fetch_price_history(token_id="abc", http_get=_raise)
    assert points == []


def test_fetch_skips_malformed_points():
    raw = {"history": [
        {"t": "not-int", "p": 0.50},
        {"t": 1779350400, "p": "nope"},
        {"t": 1779350400, "p": 0.41},
    ]}
    points = fetch_price_history(
        token_id="abc",
        http_get=_fake_http(_FakeResp(200, raw)),
    )
    assert len(points) == 1
    assert points[0]["price"] == 0.41
