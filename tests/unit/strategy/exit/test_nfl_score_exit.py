"""nfl_score_exit.py birim testleri — N1 + N2."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit import nfl_score_exit


def _score(deficit: int = 0, available: bool = True) -> dict:
    return {"available": available, "deficit": deficit}


def test_n1_triggers_at_q3_end_with_21_deficit() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=21), elapsed_pct=0.76, sport_tag="nfl")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.detail


def test_n1_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=25), elapsed_pct=0.74, sport_tag="nfl")
    assert r is None


def test_n1_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=20), elapsed_pct=0.80, sport_tag="nfl")
    assert r is None


def test_n2_triggers_at_final_minutes_with_11_deficit() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=11), elapsed_pct=0.93, sport_tag="nfl")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.detail


def test_n2_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=15), elapsed_pct=0.91, sport_tag="nfl")
    assert r is None


def test_n2_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=10), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None


def test_deficit_zero_returns_none() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=0), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None


def test_overtime_with_large_deficit_triggers_n2() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=14), elapsed_pct=1.05, sport_tag="nfl")
    assert r is not None
    assert "N2" in r.detail


def test_score_info_unavailable_returns_none() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=25, available=False), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None
