"""cricket_score_builder.py unit tests (SPEC-011)."""
from __future__ import annotations

from src.infrastructure.apis.cricket_client import CricketMatchScore
from src.orchestration.cricket_score_builder import (
    build_cricket_score_info,
    find_cricket_match,
)


def _make_match(
    teams=None, match_type="t20", innings=None,
    match_started=True, match_ended=False,
):
    return CricketMatchScore(
        match_id="m1",
        name=" vs ".join(teams or ["Team A", "Team B"]),
        match_type=match_type,
        teams=teams or ["Team A", "Team B"],
        status="In progress",
        match_started=match_started,
        match_ended=match_ended,
        venue="",
        date_time_gmt="2026-04-19T13:00:00",
        innings=innings or [],
    )


def _make_position(question, direction="BUY_YES"):
    class _Pos:
        pass
    p = _Pos()
    p.question = question
    p.slug = "cricipl-test-2026-04-19"
    p.direction = direction
    p.event_id = "evt-1"
    return p


# ── find_cricket_match ─────────────────────────────────────────

def test_find_cricket_match_by_team_pair():
    pos = _make_position("Kolkata Knight Riders vs Rajasthan Royals")
    matches = [
        _make_match(teams=["Some Other", "Teams"]),
        _make_match(teams=["Kolkata Knight Riders", "Rajasthan Royals"]),
    ]
    match = find_cricket_match(pos, matches)
    assert match is not None
    assert match.teams == ["Kolkata Knight Riders", "Rajasthan Royals"]


def test_find_cricket_match_swapped_teams():
    pos = _make_position("Kolkata Knight Riders vs Rajasthan Royals")
    matches = [_make_match(teams=["Rajasthan Royals", "Kolkata Knight Riders"])]
    match = find_cricket_match(pos, matches)
    assert match is not None


def test_find_cricket_match_no_match():
    pos = _make_position("Mumbai Indians vs Chennai Super Kings")
    matches = [_make_match(teams=["Delhi Capitals", "Punjab Kings"])]
    match = find_cricket_match(pos, matches)
    assert match is None


# ── build_cricket_score_info ───────────────────────────────────

def test_build_score_info_not_started():
    pos = _make_position("Team A vs Team B")
    match = _make_match(match_started=False, innings=[])
    info = build_cricket_score_info(pos, match)
    assert info == {"available": False}


def test_build_score_info_innings_1():
    pos = _make_position("Team A vs Team B")
    match = _make_match(innings=[
        {"runs": 90, "wickets": 3, "overs": 12.0, "team": "Team A", "inning_num": 1},
    ])
    info = build_cricket_score_info(pos, match)
    assert info["available"] is True
    assert info["innings"] == 1


def test_build_score_info_innings_2_chase_buy_yes_we_bat():
    pos = _make_position("Team A vs Team B", direction="BUY_YES")
    match = _make_match(
        teams=["Team A", "Team B"],
        match_type="t20",
        innings=[
            {"runs": 180, "wickets": 5, "overs": 20.0, "team": "Team A", "inning_num": 1},
            {"runs": 95, "wickets": 4, "overs": 12.3, "team": "Team B", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["available"] is True
    assert info["innings"] == 2
    assert info["target"] == 181
    assert info["our_chasing"] is False
    assert info["runs_remaining"] == 86
    assert info["wickets_lost"] == 4


def test_build_score_info_innings_2_chase_buy_yes_we_chase():
    pos = _make_position("Team A vs Team B", direction="BUY_YES")
    match = _make_match(
        teams=["Team A", "Team B"],
        match_type="t20",
        innings=[
            {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team B", "inning_num": 1},
            {"runs": 80, "wickets": 5, "overs": 12.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["innings"] == 2
    assert info["target"] == 151
    assert info["our_chasing"] is True
    assert info["runs_remaining"] == 71


def test_build_score_info_buy_no_direction_inverted():
    pos = _make_position("Team A vs Team B", direction="BUY_NO")
    match = _make_match(
        teams=["Team A", "Team B"],
        match_type="t20",
        innings=[
            {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team A", "inning_num": 1},
            {"runs": 60, "wickets": 4, "overs": 10.0, "team": "Team B", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["our_chasing"] is True


def test_build_score_info_t20_max_balls():
    pos = _make_position("Team A vs Team B")
    match = _make_match(
        match_type="t20",
        innings=[
            {"runs": 150, "wickets": 6, "overs": 20.0, "team": "Team B", "inning_num": 1},
            {"runs": 80, "wickets": 5, "overs": 10.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["balls_remaining"] == 60


def test_build_score_info_odi_max_balls():
    pos = _make_position("Team A vs Team B")
    match = _make_match(
        match_type="odi",
        innings=[
            {"runs": 300, "wickets": 8, "overs": 50.0, "team": "Team B", "inning_num": 1},
            {"runs": 120, "wickets": 4, "overs": 25.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["balls_remaining"] == 150


def test_build_score_info_rrr_calculation():
    pos = _make_position("Team A vs Team B")
    match = _make_match(
        match_type="t20",
        innings=[
            {"runs": 200, "wickets": 5, "overs": 20.0, "team": "Team B", "inning_num": 1},
            {"runs": 100, "wickets": 4, "overs": 15.0, "team": "Team A", "inning_num": 2},
        ],
    )
    info = build_cricket_score_info(pos, match)
    assert info["runs_remaining"] == 101
    assert info["balls_remaining"] == 30
    assert abs(info["required_run_rate"] - 20.2) < 0.1
