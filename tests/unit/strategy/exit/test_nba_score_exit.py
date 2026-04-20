"""nba_score_exit.py birim testleri — N1 + N2 + N3 (SPEC-A4)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit import nba_score_exit


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


# ── N1: Q3 sonu + 18+ deficit ──

def test_n1_triggers_at_q3_end_with_18_deficit() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=18), elapsed_pct=0.76, sport_tag="nba")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.detail


def test_n1_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=25), elapsed_pct=0.74, sport_tag="nba")
    assert r is None


def test_n1_does_not_trigger_when_deficit_17() -> None:
    """SPEC-A4: 17 puan artık fire etmez (eski eşik 20'den 18'e indi, regime change payı)."""
    r = nba_score_exit.check(score_info=_score(deficit=17), elapsed_pct=0.80, sport_tag="nba")
    assert r is None


# ── N2: son 4dk + 8+ deficit ──

def test_n2_triggers_at_final_minutes_with_8_deficit() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=8), elapsed_pct=0.93, sport_tag="nba")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.detail


def test_n2_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=15), elapsed_pct=0.91, sport_tag="nba")
    assert r is None


def test_n2_does_not_trigger_when_deficit_7() -> None:
    """SPEC-A4: 7 puan N2 eşiğini (8) geçmez."""
    r = nba_score_exit.check(score_info=_score(deficit=7), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


# ── N3: period==4 + clock≤120 + 5+ deficit (SPEC-A4 yeni tier) ──

def test_n3_triggers_at_q4_final_2min_with_5_deficit() -> None:
    r = nba_score_exit.check(
        score_info=_score(deficit=5, period=4, clock_seconds=90),
        elapsed_pct=0.95,
        sport_tag="nba",
    )
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N3" in r.detail


def test_n3_does_not_trigger_with_deficit_4() -> None:
    r = nba_score_exit.check(
        score_info=_score(deficit=4, period=4, clock_seconds=90),
        elapsed_pct=0.95,
        sport_tag="nba",
    )
    assert r is None


def test_n3_does_not_trigger_when_clock_above_120() -> None:
    """Clock 121+ olduğunda N3 fire etmez, ama N2 (elapsed≥0.92 + def≥8) fire edebilir."""
    r = nba_score_exit.check(
        score_info=_score(deficit=5, period=4, clock_seconds=121),
        elapsed_pct=0.93,
        sport_tag="nba",
    )
    assert r is None  # def=5 < N2 eşiği (8)


def test_n3_does_not_trigger_in_q3() -> None:
    r = nba_score_exit.check(
        score_info=_score(deficit=5, period=3, clock_seconds=60),
        elapsed_pct=0.74,
        sport_tag="nba",
    )
    assert r is None


def test_n3_priority_before_n2() -> None:
    """Hem N2 hem N3 eşiği geçilmişse N3 detail görülmeli (daha spesifik)."""
    r = nba_score_exit.check(
        score_info=_score(deficit=10, period=4, clock_seconds=60),
        elapsed_pct=0.95,
        sport_tag="nba",
    )
    assert r is not None
    assert "N3" in r.detail


# ── Geriye dönük uyumluluk: clock_seconds/period yoksa N1/N2 hala çalışmalı ──

def test_n1_works_without_period_and_clock() -> None:
    """Clock parse başarısızsa score_info'da period/clock yok — N1/N2 eski davranış."""
    r = nba_score_exit.check(score_info=_score(deficit=20), elapsed_pct=0.80, sport_tag="nba")
    assert r is not None
    assert "N1" in r.detail


def test_n3_skipped_when_clock_missing() -> None:
    """clock_seconds eksikse N3 fire etmez (fail-safe)."""
    r = nba_score_exit.check(
        score_info={"available": True, "deficit": 5, "period_number": 4},
        elapsed_pct=0.95,
        sport_tag="nba",
    )
    assert r is None  # N3 skip (clock yok), def=5 < N2 eşiği


# ── Temel sınır durumları ──

def test_deficit_zero_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=0), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_deficit_negative_means_we_are_ahead_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=-8), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_score_info_unavailable_returns_none() -> None:
    r = nba_score_exit.check(
        score_info=_score(deficit=25, available=False),
        elapsed_pct=0.95,
        sport_tag="nba",
    )
    assert r is None
