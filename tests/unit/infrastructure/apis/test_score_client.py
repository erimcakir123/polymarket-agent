"""Score client testleri (SPEC-004 Adım 2)."""
from __future__ import annotations

from src.infrastructure.apis.score_client import MatchScore, _parse_scores, fetch_scores


def _raw_event(
    event_id: str = "e1",
    home: str = "Rangers",
    away: str = "Lightning",
    h_score: str | None = "3",
    a_score: str | None = "1",
    completed: bool = False,
) -> dict:
    scores = None
    if h_score is not None or a_score is not None:
        scores = [
            {"name": home, "score": h_score},
            {"name": away, "score": a_score},
        ]
    return {
        "id": event_id,
        "home_team": home,
        "away_team": away,
        "scores": scores,
        "completed": completed,
        "last_update": "2026-04-17T01:00:00Z",
    }


def test_parse_scores_valid_response() -> None:
    raw = [_raw_event()]
    result = _parse_scores(raw)
    assert len(result) == 1
    m = result[0]
    assert m.event_id == "e1"
    assert m.home_team == "Rangers"
    assert m.away_team == "Lightning"
    assert m.home_score == 3
    assert m.away_score == 1
    assert m.is_completed is False


def test_parse_scores_no_scores_yet() -> None:
    raw = [_raw_event(h_score=None, a_score=None)]
    result = _parse_scores(raw)
    assert result[0].home_score is None
    assert result[0].away_score is None


def test_parse_scores_completed() -> None:
    raw = [_raw_event(completed=True)]
    result = _parse_scores(raw)
    assert result[0].is_completed is True


def test_parse_scores_empty_response() -> None:
    assert _parse_scores([]) == []


class _FakeOddsClient:
    def __init__(self, data: list[dict] | None) -> None:
        self._data = data

    def get_scores(self, sport_key: str, days_from: int = 1) -> list[dict] | None:
        return self._data


def test_fetch_scores_returns_parsed() -> None:
    client = _FakeOddsClient([_raw_event()])
    result = fetch_scores(client, "icehockey_nhl")  # type: ignore[arg-type]
    assert len(result) == 1
    assert isinstance(result[0], MatchScore)


def test_fetch_scores_api_error_returns_empty() -> None:
    client = _FakeOddsClient(None)
    result = fetch_scores(client, "icehockey_nhl")  # type: ignore[arg-type]
    assert result == []
