"""nba_score_exit.py birim testleri — N1 + N2."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit import nba_score_exit


def _score(deficit: int = 0, available: bool = True) -> dict:
    return {"available": available, "deficit": deficit}


def test_n1_triggers_at_q3_end_with_20_deficit() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=20), elapsed_pct=0.76, sport_tag="nba")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.detail


def test_n1_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=25), elapsed_pct=0.74, sport_tag="nba")
    assert r is None


def test_n1_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=19), elapsed_pct=0.80, sport_tag="nba")
    assert r is None


def test_n2_triggers_at_final_minutes_with_10_deficit() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=10), elapsed_pct=0.93, sport_tag="nba")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.detail


def test_n2_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=15), elapsed_pct=0.91, sport_tag="nba")
    assert r is None


def test_n2_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=9), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_deficit_zero_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=0), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_deficit_negative_means_we_are_ahead_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=-8), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_score_info_unavailable_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=25, available=False), elapsed_pct=0.95, sport_tag="nba")
    assert r is None
