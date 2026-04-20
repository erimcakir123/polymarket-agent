"""ESPN scoreboard client testleri (SPEC-005 Task 1 + SPEC-014)."""
from __future__ import annotations

import pytest

from src.infrastructure.apis.espn_client import ESPNMatchScore, _parse_competition, _parse_scoreboard

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_HOCKEY_RESPONSE: dict = {
    "events": [{
        "name": "NHL Game",
        "groupings": [{
            "competitions": [{
                "id": "12345",
                "status": {
                    "period": 3,
                    "type": {
                        "description": "Final",
                        "completed": True,
                        "state": "post",
                    },
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "winner": True,
                        "athlete": {"displayName": "New York Rangers"},
                        "linescores": [
                            {"value": 2.0},
                            {"value": 1.0},
                            {"value": 1.0},
                        ],
                    },
                    {
                        "homeAway": "away",
                        "winner": False,
                        "athlete": {"displayName": "Tampa Bay Lightning"},
                        "linescores": [
                            {"value": 0.0},
                            {"value": 1.0},
                            {"value": 0.0},
                        ],
                    },
                ],
                "notes": [{"text": "Rangers 4, Lightning 1"}],
            }],
        }],
    }],
}

_TENNIS_RESPONSE: dict = {
    "events": [{
        "name": "BMW Open",
        "groupings": [{
            "competitions": [{
                "id": "99999",
                "status": {
                    "period": 3,
                    "type": {
                        "description": "Final",
                        "completed": True,
                        "state": "post",
                    },
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "winner": True,
                        "athlete": {"displayName": "Karolina Muchova"},
                        "linescores": [
                            {"value": 6.0},
                            {"value": 5.0},
                            {"value": 6.0},
                        ],
                    },
                    {
                        "homeAway": "away",
                        "winner": False,
                        "athlete": {"displayName": "Coco Gauff"},
                        "linescores": [
                            {"value": 3.0},
                            {"value": 7.0},
                            {"value": 3.0},
                        ],
                    },
                ],
                "notes": [],
            }],
        }],
    }],
}

_LIVE_RESPONSE: dict = {
    "events": [{
        "name": "Live Match",
        "groupings": [{
            "competitions": [{
                "id": "77777",
                "status": {
                    "period": 2,
                    "type": {
                        "description": "In Progress",
                        "completed": False,
                        "state": "in",
                    },
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "winner": False,
                        "athlete": {"displayName": "Home Team"},
                        "linescores": [{"value": 1.0}],
                    },
                    {
                        "homeAway": "away",
                        "winner": False,
                        "athlete": {"displayName": "Away Team"},
                        "linescores": [{"value": 2.0}],
                    },
                ],
                "notes": [],
            }],
        }],
    }],
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_hockey_final_score_sums_periods() -> None:
    """Rangers 4-1 Lightning: sum of 3 periods each."""
    result = _parse_scoreboard(_HOCKEY_RESPONSE)

    assert len(result) == 1
    match = result[0]
    assert match.event_id == "12345"
    assert match.home_name == "New York Rangers"
    assert match.away_name == "Tampa Bay Lightning"
    assert match.home_score == 4  # 2+1+1
    assert match.away_score == 1  # 0+1+0
    assert match.period == "Final"
    assert match.is_completed is True
    assert match.is_live is False
    assert match.linescores == [[2, 0], [1, 1], [1, 0]]


def test_parse_tennis_set_scores_counts_sets_won() -> None:
    """Muchova bt Gauff 6-3 5-7 6-3 → Muchova wins 2 sets, Gauff 1."""
    result = _parse_scoreboard(_TENNIS_RESPONSE)

    assert len(result) == 1
    match = result[0]
    assert match.event_id == "99999"
    assert match.home_name == "Karolina Muchova"
    assert match.away_name == "Coco Gauff"
    # Tennis: home wins sets 1 (6>3) and 3 (6>3), away wins set 2 (7>5)
    assert match.home_score == 2
    assert match.away_score == 1
    assert match.linescores == [[6, 3], [5, 7], [6, 3]]
    assert match.is_completed is True


def test_parse_live_match_is_live_true_not_completed() -> None:
    """In-progress match: is_live=True, is_completed=False."""
    result = _parse_scoreboard(_LIVE_RESPONSE)

    assert len(result) == 1
    match = result[0]
    assert match.event_id == "77777"
    assert match.is_live is True
    assert match.is_completed is False
    assert match.period == "In Progress"


def test_parse_empty_response_returns_empty_list() -> None:
    """Empty dict and events:[] both return []."""
    assert _parse_scoreboard({}) == []
    assert _parse_scoreboard({"events": []}) == []


# ---------------------------------------------------------------------------
# SPEC-014: MLB inning from status.period
# ---------------------------------------------------------------------------


def test_parse_competition_extracts_mlb_inning() -> None:
    """MLB event: status.period int -> ESPNMatchScore.inning."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Yankees"}, "score": "3",
             "athlete": {"displayName": "Yankees"}, "linescores": [{"value": 3.0}]},
            {"homeAway": "away", "team": {"displayName": "Red Sox"}, "score": "2",
             "athlete": {"displayName": "Red Sox"}, "linescores": [{"value": 2.0}]},
        ],
        "status": {
            "period": 7,
            "type": {"description": "Top 7th", "state": "in", "completed": False},
        },
        "startDate": "2026-04-20T18:00:00Z",
    }
    ms = _parse_competition(comp, sport="baseball")
    assert ms is not None
    assert ms.inning == 7


def test_parse_competition_mlb_inning_none_pregame() -> None:
    """Pregame: status.period 0 -> inning None."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Yankees"}, "score": "0",
             "athlete": {"displayName": "Yankees"}, "linescores": []},
            {"homeAway": "away", "team": {"displayName": "Red Sox"}, "score": "0",
             "athlete": {"displayName": "Red Sox"}, "linescores": []},
        ],
        "status": {
            "period": 0,
            "type": {"description": "Scheduled", "state": "pre", "completed": False},
        },
        "startDate": "2026-04-20T18:00:00Z",
    }
    ms = _parse_competition(comp, sport="baseball")
    assert ms is not None
    assert ms.inning is None


def test_parse_competition_non_baseball_no_inning() -> None:
    """Non-baseball: status.period int mevcut ama inning None olmali."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Rangers"}, "score": "2",
             "athlete": {"displayName": "Rangers"}, "linescores": [{"value": 1.0}, {"value": 1.0}]},
            {"homeAway": "away", "team": {"displayName": "Bruins"}, "score": "1",
             "athlete": {"displayName": "Bruins"}, "linescores": [{"value": 1.0}, {"value": 0.0}]},
        ],
        "status": {
            "period": 2,
            "type": {"description": "2nd Period", "state": "in", "completed": False},
        },
        "startDate": "2026-04-20T19:00:00Z",
    }
    ms = _parse_competition(comp, sport="hockey")
    assert ms is not None
    assert ms.inning is None


# ---------------------------------------------------------------------------
# SPEC-015: Soccer minute + regulation_state
# ---------------------------------------------------------------------------


def test_parse_competition_extracts_soccer_minute() -> None:
    """SPEC-015: status.displayClock '67'' -> ESPNMatchScore.minute=67."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Arsenal"}, "score": "1",
             "athlete": {"displayName": "Arsenal"}},
            {"homeAway": "away", "team": {"displayName": "Chelsea"}, "score": "0",
             "athlete": {"displayName": "Chelsea"}},
        ],
        "status": {
            "period": 2,
            "displayClock": "67'",
            "type": {"description": "2nd Half", "state": "in", "completed": False},
        },
        "startDate": "2026-04-20T15:00:00Z",
    }
    ms = _parse_competition(comp, sport="soccer")
    assert ms is not None
    assert ms.minute == 67
    assert ms.regulation_state == "in"


def test_parse_competition_soccer_stoppage_time() -> None:
    """displayClock '45+2'' -> minute=45 (base, ignore stoppage)."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "X"}, "score": "0",
             "athlete": {"displayName": "X"}},
            {"homeAway": "away", "team": {"displayName": "Y"}, "score": "0",
             "athlete": {"displayName": "Y"}},
        ],
        "status": {
            "period": 1,
            "displayClock": "45+2'",
            "type": {"description": "1st Half", "state": "in"},
        },
        "startDate": "2026-04-20T15:00:00Z",
    }
    ms = _parse_competition(comp, sport="soccer")
    assert ms is not None
    assert ms.minute == 45


def test_parse_competition_soccer_full_time_stoppage() -> None:
    """displayClock '90'+13'' -> minute=90."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "X"}, "score": "1",
             "athlete": {"displayName": "X"}},
            {"homeAway": "away", "team": {"displayName": "Y"}, "score": "1",
             "athlete": {"displayName": "Y"}},
        ],
        "status": {
            "period": 2,
            "displayClock": "90'+13'",
            "type": {"description": "2nd Half", "state": "in"},
        },
        "startDate": "2026-04-20T15:00:00Z",
    }
    ms = _parse_competition(comp, sport="soccer")
    assert ms is not None
    assert ms.minute == 90


def test_parse_competition_soccer_pregame() -> None:
    """state='pre' -> minute=None, regulation_state='pre'."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "X"}, "score": "0",
             "athlete": {"displayName": "X"}},
            {"homeAway": "away", "team": {"displayName": "Y"}, "score": "0",
             "athlete": {"displayName": "Y"}},
        ],
        "status": {
            "period": 0,
            "displayClock": "0'",
            "type": {"description": "Scheduled", "state": "pre"},
        },
        "startDate": "2026-04-20T15:00:00Z",
    }
    ms = _parse_competition(comp, sport="soccer")
    assert ms is not None
    assert ms.minute is None
    assert ms.regulation_state == "pre"


def test_parse_competition_non_soccer_no_minute() -> None:
    """Non-soccer (baseball): minute default None, inning still parsed."""
    comp = {
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "X"}, "score": "2",
             "athlete": {"displayName": "X"}, "linescores": [{"value": 2.0}]},
            {"homeAway": "away", "team": {"displayName": "Y"}, "score": "1",
             "athlete": {"displayName": "Y"}, "linescores": [{"value": 1.0}]},
        ],
        "status": {
            "period": 7,
            "type": {"description": "Top 7th", "state": "in"},
        },
        "startDate": "2026-04-20T18:00:00Z",
    }
    ms = _parse_competition(comp, sport="baseball")
    assert ms is not None
    assert ms.minute is None  # non-soccer
    assert ms.inning == 7  # baseball still works


def test_parse_no_competitors_skips_competition() -> None:
    """Competition with <2 competitors is skipped."""
    response = {
        "events": [{
            "name": "Bad Event",
            "groupings": [{
                "competitions": [{
                    "id": "00000",
                    "status": {
                        "period": 1,
                        "type": {
                            "description": "Final",
                            "completed": True,
                            "state": "post",
                        },
                    },
                    "competitors": [
                        {
                            "homeAway": "home",
                            "winner": True,
                            "athlete": {"displayName": "Solo Team"},
                            "linescores": [],
                        },
                    ],
                    "notes": [],
                }],
            }],
        }],
    }
    assert _parse_scoreboard(response) == []
