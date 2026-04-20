"""nfl_score_exit.py birim testleri — N1 + N2 + N3 (SPEC-A4)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit import nfl_score_exit


def _score(
    deficit: int = 0,
    available: bool = True,
    period: int | None = None,
    clock_seconds: int | None = None,
) -> dict:
    info: dict = {"available": available, "deficit": deficit}
    if period is not None:
        info["period_number"] = period
    if clock_seconds is not None:
        info["clock_seconds"] = clock_seconds
    return info


# ── N1: Q3 sonu + 17+ deficit ──

def test_n1_triggers_at_q3_end_with_17_deficit() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=17), elapsed_pct=0.76, sport_tag="nfl")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.detail


def test_n1_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=25), elapsed_pct=0.74, sport_tag="nfl")
    assert r is None


def test_n1_does_not_trigger_when_deficit_16() -> None:
    """SPEC-A4: 16 puan artık fire etmez (eski 21'den 17'ye indi)."""
    r = nfl_score_exit.check(score_info=_score(deficit=16), elapsed_pct=0.80, sport_tag="nfl")
    assert r is None


# ── N2: son 5dk + 9+ deficit ──

def test_n2_triggers_at_final_minutes_with_9_deficit() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=9), elapsed_pct=0.93, sport_tag="nfl")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.detail


def test_n2_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=15), elapsed_pct=0.91, sport_tag="nfl")
    assert r is None


def test_n2_does_not_trigger_when_deficit_8() -> None:
    """SPEC-A4: 8 puan N2 eşiğini (9) geçmez."""
    r = nfl_score_exit.check(score_info=_score(deficit=8), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None


# ── N3: period==4 + clock≤150 + 4+ deficit (SPEC-A4 yeni tier) ──

def test_n3_triggers_at_q4_final_150s_with_4_deficit() -> None:
    r = nfl_score_exit.check(
        score_info=_score(deficit=4, period=4, clock_seconds=120),
        elapsed_pct=0.95,
        sport_tag="nfl",
    )
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N3" in r.detail


def test_n3_does_not_trigger_with_deficit_3() -> None:
    r = nfl_score_exit.check(
        score_info=_score(deficit=3, period=4, clock_seconds=120),
        elapsed_pct=0.95,
        sport_tag="nfl",
    )
    assert r is None


def test_n3_does_not_trigger_when_clock_above_150() -> None:
    r = nfl_score_exit.check(
        score_info=_score(deficit=4, period=4, clock_seconds=151),
        elapsed_pct=0.93,
        sport_tag="nfl",
    )
    assert r is None  # def=4 < N2 eşiği (9), N3 clock geçti


def test_n3_priority_before_n2() -> None:
    """Hem N2 hem N3 eşiği geçilmişse N3 detail görülmeli."""
    r = nfl_score_exit.check(
        score_info=_score(deficit=12, period=4, clock_seconds=90),
        elapsed_pct=0.95,
        sport_tag="nfl",
    )
    assert r is not None
    assert "N3" in r.detail


# ── Geriye dönük uyumluluk ──

def test_n1_works_without_period_and_clock() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=21), elapsed_pct=0.80, sport_tag="nfl")
    assert r is not None
    assert "N1" in r.detail


def test_n3_skipped_when_clock_missing() -> None:
    r = nfl_score_exit.check(
        score_info={"available": True, "deficit": 4, "period_number": 4},
        elapsed_pct=0.95,
        sport_tag="nfl",
    )
    assert r is None  # N3 skip, def=4 < N2 eşiği


# ── Temel sınır durumları ──

def test_deficit_zero_returns_none() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=0), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None


def test_overtime_with_large_deficit_triggers_n2() -> None:
    """Elapsed>1.0 (OT) hala N2 fire eder — period+clock refactor SPEC-A5'te."""
    r = nfl_score_exit.check(score_info=_score(deficit=14), elapsed_pct=1.05, sport_tag="nfl")
    assert r is not None
    assert "N2" in r.detail


def test_score_info_unavailable_returns_none() -> None:
    r = nfl_score_exit.check(
        score_info=_score(deficit=25, available=False),
        elapsed_pct=0.95,
        sport_tag="nfl",
    )
    assert r is None
