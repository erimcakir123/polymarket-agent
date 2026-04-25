"""Unit tests — EspnScheduleClient (TDD §Task-2 NBA B2B Detection).

GERÇEK HTTP ÇAĞRISI YAPILMAZ: http_get parametresine mock callable enjekte edilir.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from src.infrastructure.apis.espn_schedule_client import EspnScheduleClient, GameEvent


# ── Mock helper ─────────────────────────────────────────────────────────────


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


# ── Tests: get_team_schedule ─────────────────────────────────────────────────


class TestGetTeamSchedule:
    def test_get_team_schedule_parse_basic(self) -> None:
        """1 maç — tüm GameEvent alanları doğru parse edilmeli."""
        payload = _make_payload(_make_event())
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        result = client.get_team_schedule("1", 2026)

        assert len(result) == 1
        ev = result[0]
        assert isinstance(ev, GameEvent)
        assert ev.game_id == "401234567"
        assert ev.date == datetime(2026, 4, 20, 0, 0, 0, tzinfo=timezone.utc)
        assert ev.home_team_id == "1"
        assert ev.away_team_id == "2"
        assert ev.status == "final"

    def test_get_team_schedule_multiple_games(self) -> None:
        """3 maç — tamamı parse edilip döner."""
        payload = _make_payload(
            _make_event(game_id="1", date_str="2026-04-10T00:00:00Z"),
            _make_event(game_id="2", date_str="2026-04-12T00:00:00Z"),
            _make_event(game_id="3", date_str="2026-04-14T00:00:00Z"),
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        result = client.get_team_schedule("1", 2026)

        assert len(result) == 3
        ids = {ev.game_id for ev in result}
        assert ids == {"1", "2", "3"}

    def test_get_team_schedule_http_error_returns_empty(self) -> None:
        """HTTP hata → boş liste döner, exception raise edilmez."""

        def _bad_http(*args, **kwargs):
            raise httpx.HTTPError("connection failed")

        client = EspnScheduleClient(http_get=_bad_http)
        result = client.get_team_schedule("1", 2026)
        assert result == []

    def test_get_team_schedule_cache_hit(self) -> None:
        """TTL dolmadan aynı team+season ikinci çağrısı HTTP yapmaz."""
        call_count = 0
        payload = _make_payload(_make_event())

        class _CountingResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return payload

        def _counting_http(*args, **kwargs) -> _CountingResp:
            nonlocal call_count
            call_count += 1
            return _CountingResp()

        client = EspnScheduleClient(http_get=_counting_http, cache_ttl_sec=60)
        client.get_team_schedule("1", 2026)
        client.get_team_schedule("1", 2026)

        assert call_count == 1

    def test_get_team_schedule_different_seasons_separate_cache(self) -> None:
        """Farklı sezonlar farklı cache key → her biri ayrı HTTP çağrısı yapar."""
        call_count = 0
        payload = _make_payload(_make_event())

        class _CountingResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return payload

        def _counting_http(*args, **kwargs) -> _CountingResp:
            nonlocal call_count
            call_count += 1
            return _CountingResp()

        client = EspnScheduleClient(http_get=_counting_http, cache_ttl_sec=60)
        client.get_team_schedule("1", 2025)
        client.get_team_schedule("1", 2026)

        assert call_count == 2


# ── Tests: days_since_last_game ──────────────────────────────────────────────


class TestDaysSinceLastGame:
    def test_days_since_last_game_one_day(self) -> None:
        """Dünkü final maç → 1 döner."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-24T20:00:00Z", status_desc="Final")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        result = client.days_since_last_game("1", ref, 2026)
        assert result == 1

    def test_days_since_last_game_two_days(self) -> None:
        """İki gün önceki final maç → 2 döner."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-23T20:00:00Z", status_desc="Final")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        result = client.days_since_last_game("1", ref, 2026)
        assert result == 2

    def test_days_since_last_game_none_when_no_prior_game(self) -> None:
        """Sadece gelecekteki maçlar var → None döner."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-27T20:00:00Z", status_desc="Scheduled")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        result = client.days_since_last_game("1", ref, 2026)
        assert result is None

    def test_days_since_last_game_ignores_non_final(self) -> None:
        """Reference date'ten önceki scheduled maçlar → final sayılmaz → None döner."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-24T20:00:00Z", status_desc="Scheduled")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        result = client.days_since_last_game("1", ref, 2026)
        assert result is None


# ── Tests: is_back_to_back ───────────────────────────────────────────────────


class TestIsBackToBack:
    def test_is_back_to_back_true(self) -> None:
        """Dünkü final maç → back-to-back True."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-24T20:00:00Z", status_desc="Final")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        assert client.is_back_to_back("1", ref, 2026) is True

    def test_is_back_to_back_false(self) -> None:
        """İki gün önceki maç → back-to-back False."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-23T20:00:00Z", status_desc="Final")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        assert client.is_back_to_back("1", ref, 2026) is False

    def test_is_back_to_back_false_when_no_prior(self) -> None:
        """Önceki maç yoksa (None) → back-to-back False."""
        ref = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        payload = _make_payload(
            _make_event(date_str="2026-04-27T20:00:00Z", status_desc="Scheduled")
        )
        client = EspnScheduleClient(http_get=_make_mock_http(payload))

        assert client.is_back_to_back("1", ref, 2026) is False
