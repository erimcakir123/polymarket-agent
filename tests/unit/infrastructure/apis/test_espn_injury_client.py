"""Unit tests — EspnInjuryClient (TDD §Task-1 NBA Injury).

GERÇEK HTTP ÇAĞRISI YAPILMAZ: http_get parametresine mock callable enjekte edilir.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import httpx
import pytest

from src.infrastructure.apis.espn_injury_client import EspnInjuryClient, InjuryEvent


# ── Test fixture helper ──────────────────────────────────────────────────────

def _make_mock_http(json_data: dict, status_code: int = 200):
    """HTTP GET callable döner; gerçek ağ bağlantısı yok."""

    class _MockResp:
        def raise_for_status(self) -> None:
            if status_code >= 400:
                raise httpx.HTTPStatusError(
                    "err", request=None, response=None  # type: ignore[arg-type]
                )

        def json(self) -> dict:
            return json_data

    def _get(*args, **kwargs) -> _MockResp:
        return _MockResp()

    return _get


def _make_injury_block(
    team_id: str = "1",
    athlete_name: str = "Trae Young",
    status: str = "Out",
    is_starter: bool = True,
    date_str: str = "2026-04-25T18:00:00Z",
) -> dict:
    return {
        "team": {"id": team_id, "displayName": "Test Team"},
        "injuries": [
            {
                "athlete": {
                    "displayName": athlete_name,
                    "status": {
                        "type": {"description": status},
                        "starter": is_starter,
                    },
                },
                "date": date_str,
                "longComment": "Ankle",
            }
        ],
    }


# ── Tests ────────────────────────────────────────────────────────────────────

class TestFetchNbaInjuriesBasic:
    def test_fetch_nba_injuries_parse_basic(self) -> None:
        """Happy path: 1 takım, 1 'Out' oyuncu — InjuryEvent alanları doğru."""
        payload = {"injuries": [_make_injury_block()]}
        client = EspnInjuryClient(http_get=_make_mock_http(payload))

        result = client.fetch_nba_injuries()

        assert "1" in result
        events = result["1"]
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, InjuryEvent)
        assert ev.athlete_name == "Trae Young"
        assert ev.status == "Out"
        assert ev.team_id == "1"
        assert ev.is_starter is True
        assert ev.reported_at == datetime(2026, 4, 25, 18, 0, 0, tzinfo=timezone.utc)

    def test_fetch_nba_injuries_multiple_teams(self) -> None:
        """2 takım, farklı sayıda injury — dict key'leri doğru."""
        payload = {
            "injuries": [
                _make_injury_block(team_id="1", athlete_name="Player A"),
                {
                    "team": {"id": "2", "displayName": "Team B"},
                    "injuries": [
                        {
                            "athlete": {
                                "displayName": "Player B",
                                "status": {
                                    "type": {"description": "Questionable"},
                                    "starter": False,
                                },
                            },
                            "date": "2026-04-25T10:00:00Z",
                        },
                        {
                            "athlete": {
                                "displayName": "Player C",
                                "status": {
                                    "type": {"description": "Doubtful"},
                                    "starter": True,
                                },
                            },
                            "date": "2026-04-25T11:00:00Z",
                        },
                    ],
                },
            ]
        }
        client = EspnInjuryClient(http_get=_make_mock_http(payload))
        result = client.fetch_nba_injuries()

        assert set(result.keys()) == {"1", "2"}
        assert len(result["1"]) == 1
        assert len(result["2"]) == 2

    def test_fetch_nba_injuries_unknown_status_skipped(self) -> None:
        """'Probable' gibi bilinmeyen status → sonuca dahil edilmez."""
        payload = {"injuries": [_make_injury_block(status="Probable")]}
        client = EspnInjuryClient(http_get=_make_mock_http(payload))
        result = client.fetch_nba_injuries()
        assert result == {}

    def test_fetch_nba_injuries_missing_starter_defaults_false(self) -> None:
        """'starter' anahtarı yoksa is_starter=False varsayılır."""
        block = {
            "team": {"id": "5"},
            "injuries": [
                {
                    "athlete": {
                        "displayName": "No Starter Key",
                        "status": {"type": {"description": "Out"}},
                        # 'starter' alanı yok
                    },
                    "date": "2026-04-25T08:00:00Z",
                }
            ],
        }
        client = EspnInjuryClient(http_get=_make_mock_http({"injuries": [block]}))
        result = client.fetch_nba_injuries()
        assert result["5"][0].is_starter is False

    def test_fetch_nba_injuries_http_error_returns_empty(self) -> None:
        """HTTP 500 → boş dict döner, exception raise edilmez."""

        def _bad_http(*args, **kwargs):
            raise httpx.HTTPError("connection failed")

        client = EspnInjuryClient(http_get=_bad_http)
        result = client.fetch_nba_injuries()
        assert result == {}


class TestCache:
    def test_cache_hit_returns_without_http_call(self) -> None:
        """TTL süresi dolmadan ikinci çağrı HTTP yapmaz."""
        call_count = 0
        payload = {"injuries": [_make_injury_block()]}

        class _CountingResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return payload

        def _counting_http(*args, **kwargs) -> _CountingResp:
            nonlocal call_count
            call_count += 1
            return _CountingResp()

        client = EspnInjuryClient(http_get=_counting_http, cache_ttl_sec=60)
        client.fetch_nba_injuries()
        client.fetch_nba_injuries()

        assert call_count == 1


class TestGetRecentInjuries:
    def _payload_with_date(self, date_str: str) -> dict:
        return {"injuries": [_make_injury_block(date_str=date_str)]}

    def test_get_recent_injuries_within_window(self) -> None:
        """1 saat önceki injury, hours=2 → sonuca girer."""
        one_hour_ago = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        date_str = one_hour_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        client = EspnInjuryClient(
            http_get=_make_mock_http(self._payload_with_date(date_str))
        )
        result = client.get_recent_injuries(hours=2)
        assert "1" in result
        assert len(result["1"]) == 1

    def test_get_recent_injuries_outside_window(self) -> None:
        """3 saat önceki injury, hours=2 → sonuca girmez."""
        three_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=3)
        date_str = three_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        client = EspnInjuryClient(
            http_get=_make_mock_http(self._payload_with_date(date_str))
        )
        result = client.get_recent_injuries(hours=2)
        assert result == {}

    def test_get_recent_injuries_empty_when_no_injuries(self) -> None:
        """ESPN boş liste döndürünce get_recent_injuries da boş döner."""
        client = EspnInjuryClient(http_get=_make_mock_http({"injuries": []}))
        result = client.get_recent_injuries(hours=2)
        assert result == {}
