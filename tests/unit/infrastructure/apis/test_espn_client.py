"""ESPN scoreboard client testleri (SPEC-005 Task 1)."""
from __future__ import annotations

import pytest

from src.infrastructure.apis.espn_client import ESPNMatchScore, _parse_scoreboard

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
