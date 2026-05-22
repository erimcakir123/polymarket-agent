"""ESPNClient.fetch_tennis_matches_today: 3-aşamalı tennis fetch + athlete cache."""
from __future__ import annotations
from unittest.mock import MagicMock

from src.infrastructure.apis.espn_client import ESPNClient


def _resp(payload: dict, status: int = 200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = payload
    return m


def _scoreboard_payload(events):
    return {"events": events}


def _competitions_payload(items):
    return {"count": len(items), "items": items}


def _competition_detail(comp_id: str, date_iso: str, p1_ref: str, p2_ref: str):
    return {
        "id": comp_id,
        "date": date_iso,
        "competitors": [
            {"athlete": {"$ref": p1_ref}, "homeAway": None},
            {"athlete": {"$ref": p2_ref}, "homeAway": None},
        ],
        "status": {"type": {"description": "Scheduled", "completed": False, "state": "pre"}},
    }


def _athlete_payload(name: str):
    return {"displayName": name, "fullName": name, "id": name.replace(" ", "")}


def test_fetch_tennis_matches_today_returns_match_list_for_active_tournament():
    http_get = MagicMock(side_effect=[
        _resp(_scoreboard_payload([
            {"id": "172-2026", "name": "Roland Garros", "endDate": "2026-06-08T03:59Z"}
        ])),
        _resp(_competitions_payload([
            {"$ref": "https://x/competitions/178427"}
        ])),
        _resp(_competition_detail(
            "178427", "2026-05-23T08:05Z",
            "https://x/athletes/3897", "https://x/athletes/2567",
        )),
        _resp(_athlete_payload("Jesper de Jong")),
        _resp(_athlete_payload("Sun Fajing")),
    ])
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert len(out) == 1
    m = out[0]
    assert m.event_id == "178427"
    assert m.home_name == "Jesper de Jong"
    assert m.away_name == "Sun Fajing"
    assert m.commence_time == "2026-05-23T08:05Z"


def test_fetch_tennis_matches_today_caches_athlete_lookups():
    http_get = MagicMock(side_effect=[
        _resp(_scoreboard_payload([{"id": "T1", "endDate": "2026-06-01T00:00Z"}])),
        _resp(_competitions_payload([
            {"$ref": "https://x/comp/1"},
            {"$ref": "https://x/comp/2"},
        ])),
        _resp(_competition_detail("1", "2026-05-23T10:00Z",
                                   "https://x/athletes/A", "https://x/athletes/B")),
        _resp(_competition_detail("2", "2026-05-23T12:00Z",
                                   "https://x/athletes/A", "https://x/athletes/C")),
        _resp(_athlete_payload("Player A")),
        _resp(_athlete_payload("Player B")),
        _resp(_athlete_payload("Player C")),
    ])
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert len(out) == 2
    # 1 scoreboard + 1 competitions + 2 competition detail + 3 unique athletes = 7
    assert http_get.call_count == 7


def test_fetch_tennis_matches_today_no_active_tournaments_returns_empty():
    http_get = MagicMock(return_value=_resp(_scoreboard_payload([])))
    client = ESPNClient(http_get=http_get)
    assert client.fetch_tennis_matches_today("atp", "20260523") == []
    assert http_get.call_count == 1


def test_fetch_tennis_matches_today_athlete_lookup_failure_skips_match():
    http_get = MagicMock(side_effect=[
        _resp(_scoreboard_payload([{"id": "T1", "endDate": "2026-06-01T00:00Z"}])),
        _resp(_competitions_payload([{"$ref": "https://x/comp/1"}])),
        _resp(_competition_detail("1", "2026-05-23T10:00Z",
                                   "https://x/athletes/A", "https://x/athletes/B")),
        _resp({}, status=500),
        _resp(_athlete_payload("Player B")),
    ])
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert out == []


def test_fetch_tennis_matches_today_scoreboard_fail_returns_empty():
    http_get = MagicMock(return_value=_resp({}, status=500))
    client = ESPNClient(http_get=http_get)
    assert client.fetch_tennis_matches_today("atp", "20260523") == []


def test_fetch_tennis_matches_today_ended_tournaments_filtered():
    http_get = MagicMock(return_value=_resp(_scoreboard_payload([
        {"id": "OLD", "endDate": "2026-05-20T00:00Z"},
    ])))
    client = ESPNClient(http_get=http_get)
    out = client.fetch_tennis_matches_today("atp", "20260523")
    assert out == []
    assert http_get.call_count == 1
