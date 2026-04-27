"""Unit tests — EspnHockeyScheduleClient (NHL B2B detection).

GERÇEK HTTP ÇAĞRISI YAPILMAZ: http_get parametresine mock callable enjekte edilir.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from src.infrastructure.apis.espn_hockey_schedule_client import (
    EspnHockeyScheduleClient,
    GameEvent,
)


# ── Mock helper ──────────────────────────────────────────────────────────────

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


# ── Fixture builders ─────────────────────────────────────────────────────────

def _make_event(
    game_id: str = "401234567",
    date_str: str = "2026-04-20T00:00:00Z",
    home_id: str = "1",
    away_id: str = "2",
    status_desc: str = "Final",
) -> dict:
    return {
        "id": game_id,
        "date": date_str,
        "competitions": [
            {
                "competitors": [
                    {"homeAway": "home", "team": {"id": home_id}},
                    {"homeAway": "away", "team": {"id": away_id}},
                ],
                "status": {"type": {"description": status_desc}},
            }
        ],
    }


def _make_payload(*events: dict) -> dict:
    return {"events": list(events)}


# ── Tests: get_team_schedule ──────────────────────────────────────────────────

class TestGetTeamSchedule:
    def test_parse_basic_event(self) -> None:
        payload = _make_payload(_make_event())
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))

        result = client.get_team_schedule("1", 2026)

        assert len(result) == 1
        ev = result[0]
        assert isinstance(ev, GameEvent)
        assert ev.game_id == "401234567"
        assert ev.home_team_id == "1"
        assert ev.away_team_id == "2"
        assert ev.status == "final"
        assert ev.date.tzinfo is not None

    def test_empty_events_list_returns_empty(self) -> None:
        client = EspnHockeyScheduleClient(http_get=_make_mock_http({"events": []}))
        assert client.get_team_schedule("1", 2026) == []

    def test_missing_events_key_returns_empty(self) -> None:
        client = EspnHockeyScheduleClient(http_get=_make_mock_http({}))
        assert client.get_team_schedule("1", 2026) == []

    def test_http_error_returns_empty(self) -> None:
        client = EspnHockeyScheduleClient(
            http_get=_make_mock_http({}, status_code=500)
        )
        assert client.get_team_schedule("1", 2026) == []

    def test_malformed_event_skipped(self) -> None:
        payload = {"events": [{"id": "bad-event"}]}  # missing required fields
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        assert client.get_team_schedule("1", 2026) == []

    def test_multiple_events_parsed(self) -> None:
        payload = _make_payload(
            _make_event(game_id="1", date_str="2026-04-18T00:00:00Z"),
            _make_event(game_id="2", date_str="2026-04-20T00:00:00Z"),
            _make_event(game_id="3", date_str="2026-04-22T00:00:00Z"),
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        result = client.get_team_schedule("1", 2026)
        assert len(result) == 3
        assert {ev.game_id for ev in result} == {"1", "2", "3"}

    def test_season_none_defaults_to_resolved(self) -> None:
        """season=None は内部 _resolve_season で解決される — crash しない."""
        payload = _make_payload(_make_event())
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        result = client.get_team_schedule("1")  # season omitted
        assert len(result) == 1


# ── Tests: cache ──────────────────────────────────────────────────────────────

class TestCache:
    def test_cache_hit_avoids_second_http_call(self) -> None:
        call_count = 0

        def _counting_http(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            class _R:
                def raise_for_status(self) -> None: pass
                def json(self): return _make_payload(_make_event())

            return _R()

        client = EspnHockeyScheduleClient(http_get=_counting_http, cache_ttl_sec=60)
        client.get_team_schedule("1", 2026)
        client.get_team_schedule("1", 2026)
        assert call_count == 1

    def test_cache_miss_after_ttl_expired(self) -> None:
        call_count = 0

        def _counting_http(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            class _R:
                def raise_for_status(self) -> None: pass
                def json(self): return _make_payload(_make_event())

            return _R()

        client = EspnHockeyScheduleClient(http_get=_counting_http, cache_ttl_sec=0)
        client.get_team_schedule("1", 2026)
        client.get_team_schedule("1", 2026)
        assert call_count == 2

    def test_different_teams_cached_separately(self) -> None:
        call_count = 0

        def _counting_http(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            class _R:
                def raise_for_status(self) -> None: pass
                def json(self): return _make_payload(_make_event())

            return _R()

        client = EspnHockeyScheduleClient(http_get=_counting_http, cache_ttl_sec=60)
        client.get_team_schedule("1", 2026)
        client.get_team_schedule("2", 2026)
        assert call_count == 2


# ── Tests: days_since_last_game ───────────────────────────────────────────────

class TestDaysSinceLastGame:
    def test_one_day_ago_returns_one(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-24T20:00:00Z", status_desc="Final")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        ref = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        assert client.days_since_last_game("1", ref, 2026) == 1

    def test_two_days_ago_returns_two(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-23T20:00:00Z", status_desc="Final")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        ref = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        assert client.days_since_last_game("1", ref, 2026) == 2

    def test_no_prior_finals_returns_none(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-26T20:00:00Z", status_desc="Scheduled")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        ref = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        assert client.days_since_last_game("1", ref, 2026) is None

    def test_future_game_ignored(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-26T20:00:00Z", status_desc="Final")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        ref = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        assert client.days_since_last_game("1", ref, 2026) is None

    def test_most_recent_game_selected(self) -> None:
        payload = _make_payload(
            _make_event(game_id="old", date_str="2026-04-20T20:00:00Z", status_desc="Final"),
            _make_event(game_id="recent", date_str="2026-04-24T20:00:00Z", status_desc="Final"),
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        ref = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        assert client.days_since_last_game("1", ref, 2026) == 1

    def test_naive_reference_date_treated_as_utc(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-24T20:00:00Z", status_desc="Final")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        ref = datetime(2026, 4, 25, 12, 0)  # no tzinfo
        assert client.days_since_last_game("1", ref, 2026) == 1


# ── Tests: is_back_to_back ────────────────────────────────────────────────────

class TestIsBackToBack:
    def test_true_when_played_yesterday(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-24T20:00:00Z", status_desc="Final")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        game_date = datetime(2026, 4, 25, 19, 0, tzinfo=timezone.utc)
        assert client.is_back_to_back(team_id="1", game_date=game_date) is True

    def test_false_when_two_days_ago(self) -> None:
        payload = _make_payload(
            _make_event(date_str="2026-04-23T20:00:00Z", status_desc="Final")
        )
        client = EspnHockeyScheduleClient(http_get=_make_mock_http(payload))
        game_date = datetime(2026, 4, 25, 19, 0, tzinfo=timezone.utc)
        assert client.is_back_to_back(team_id="1", game_date=game_date) is False

    def test_false_when_no_prior_games(self) -> None:
        client = EspnHockeyScheduleClient(http_get=_make_mock_http({"events": []}))
        game_date = datetime(2026, 4, 25, 19, 0, tzinfo=timezone.utc)
        assert client.is_back_to_back(team_id="1", game_date=game_date) is False

    def test_keyword_args_accepted(self) -> None:
        """NHLEdgeEnricher calls is_back_to_back(team_id=..., game_date=...)."""
        client = EspnHockeyScheduleClient(http_get=_make_mock_http({"events": []}))
        game_date = datetime(2026, 4, 25, 19, 0, tzinfo=timezone.utc)
        result = client.is_back_to_back(team_id="1", game_date=game_date)
        assert result is False


# ── Tests: _resolve_season ────────────────────────────────────────────────────

class TestResolveSeason:
    def test_october_returns_next_year(self) -> None:
        d = datetime(2025, 10, 1, tzinfo=timezone.utc)
        assert EspnHockeyScheduleClient._resolve_season(d) == 2026

    def test_april_returns_same_year(self) -> None:
        d = datetime(2026, 4, 25, tzinfo=timezone.utc)
        assert EspnHockeyScheduleClient._resolve_season(d) == 2026

    def test_september_returns_same_year(self) -> None:
        d = datetime(2025, 9, 30, tzinfo=timezone.utc)
        assert EspnHockeyScheduleClient._resolve_season(d) == 2025

    def test_november_returns_next_year(self) -> None:
        d = datetime(2025, 11, 15, tzinfo=timezone.utc)
        assert EspnHockeyScheduleClient._resolve_season(d) == 2026
