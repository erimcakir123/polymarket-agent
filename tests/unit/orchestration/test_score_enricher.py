"""Score enricher testleri (SPEC-004 Adım 4)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.infrastructure.apis.score_client import MatchScore
from src.models.position import Position
from src.orchestration.score_enricher import (
    ScoreEnricher,
    _build_score_info,
    _find_match,
    _is_within_match_window,
    _team_match,
)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pos(
    cid: str = "c1",
    question: str = "Rangers vs. Lightning",
    direction: str = "BUY_NO",
    sport_tag: str = "nhl",
    hours_ago: float = 1.0,
) -> Position:
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return Position(
        condition_id=cid, token_id="t", direction=direction,
        entry_price=0.61, size_usdc=50, shares=80,
        current_price=0.50, anchor_probability=0.40,
        confidence="A", sport_tag=sport_tag,
        question=question, match_start_iso=_iso(start),
    )


def _ms(
    home: str = "New York Rangers",
    away: str = "Tampa Bay Lightning",
    h_score: int | None = 3,
    a_score: int | None = 1,
) -> MatchScore:
    return MatchScore(
        event_id="e1", home_team=home, away_team=away,
        home_score=h_score, away_score=a_score,
        period="2nd", is_completed=False, last_updated="",
    )


# ── team matching ──

def test_team_match_exact() -> None:
    assert _team_match("Rangers", "Rangers")


def test_team_match_substring() -> None:
    assert _team_match("Rangers", "New York Rangers")


def test_team_match_last_word() -> None:
    assert _team_match("New York Rangers", "NY Rangers")


def test_team_match_no_match() -> None:
    assert not _team_match("Sharks", "New York Rangers")


# ── match window ──

def test_within_match_window() -> None:
    pos = _pos(hours_ago=2.0)
    assert _is_within_match_window(pos, window_hours=4.0)


def test_outside_match_window() -> None:
    pos = _pos(hours_ago=6.0)
    assert not _is_within_match_window(pos, window_hours=4.0)


# ── find_match ──

def test_find_match_by_team_name() -> None:
    pos = _pos(question="Rangers vs. Lightning")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning")
    result = _find_match(pos, [ms])
    assert result is not None
    assert result.event_id == "e1"


def test_find_match_no_match() -> None:
    pos = _pos(question="Sharks vs. Jets")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning")
    assert _find_match(pos, [ms]) is None


# ── build_score_info ──

def test_build_score_info_buy_no_behind() -> None:
    pos = _pos(direction="BUY_NO", question="Rangers vs. Lightning")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning", h_score=3, a_score=1)
    # BUY_NO: YES side = Rangers (home), NO side = Lightning (away) = bizim taraf
    # Rangers (YES) = home = 3, Lightning (NO) = away = 1
    # Bizim taraf = NO side = Lightning = 1, Rakip = Rangers = 3
    info = _build_score_info(pos, ms)
    assert info["available"]
    assert info["our_score"] == 1
    assert info["opp_score"] == 3
    assert info["deficit"] == 2  # gerideyiz


def test_build_score_info_buy_yes_ahead() -> None:
    pos = _pos(direction="BUY_YES", question="Rangers vs. Lightning")
    ms = _ms(home="New York Rangers", away="Tampa Bay Lightning", h_score=3, a_score=1)
    info = _build_score_info(pos, ms)
    assert info["our_score"] == 3
    assert info["opp_score"] == 1
    assert info["deficit"] == -2  # öndeyiz


def test_build_score_info_no_score_yet() -> None:
    pos = _pos(direction="BUY_NO")
    ms = _ms(h_score=None, a_score=None)
    info = _build_score_info(pos, ms)
    assert not info["available"]


# ── ScoreEnricher polling ──

class _FakeClient:
    def __init__(self, data: list[dict] | None = None) -> None:
        self.call_count = 0
        self._data = data

    def get_scores(self, sport_key: str, days_from: int = 1) -> list[dict] | None:
        self.call_count += 1
        return self._data


def test_enricher_polls_only_when_due() -> None:
    client = _FakeClient([])
    enricher = ScoreEnricher(client, poll_interval_sec=120, match_window_hours=4.0)
    pos = _pos(hours_ago=1.0)
    positions = {"c1": pos}

    enricher.get_scores_if_due(positions)
    assert client.call_count == 1

    # 120 sn geçmeden tekrar çağır — API çağrılmamalı
    enricher.get_scores_if_due(positions)
    assert client.call_count == 1  # cache'den döner


def test_enricher_no_live_positions_no_call() -> None:
    client = _FakeClient([])
    enricher = ScoreEnricher(client, poll_interval_sec=120, match_window_hours=4.0)
    pos = _pos(hours_ago=10.0)  # pencere dışı
    positions = {"c1": pos}

    enricher.get_scores_if_due(positions)
    assert client.call_count == 0  # API hiç çağrılmadı
