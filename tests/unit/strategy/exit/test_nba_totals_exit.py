"""NBA totals exit — 4-katman pipeline (SPEC-J Group 3B).

Pipeline sırası:
  1. STRUCTURAL_DAMAGE (Q4 + bid/entry < 0.30 + total_dead)
  2. TOTALS_MATH_DEAD  (Q4 + Poisson 1.218 multiplier)
  3. PREDICTIVE_DEAD   (Q4 + EV bazlı)
  4. EMPIRICAL_DEAD    (Q4 + side-aware gap)
"""
from __future__ import annotations

import pytest

from src.models.enums import ExitReason, TotalSide
from src.strategy.exit import nba_totals_exit


# ── helpers ────────────────────────────────────────────────────────────────


def _score_info(
    *,
    available: bool = True,
    period: int = 4,
    clock: int = 30,
    home: int = 100,
    away: int = 100,
) -> dict:
    return {
        "available": available,
        "period_number": period,
        "clock_seconds": clock,
        "home_score": home,
        "away_score": away,
    }


# ── 0. score_info eksik / Q1-Q3 hold / invalid side ───────────────────────


def test_returns_none_when_score_unavailable() -> None:
    result = nba_totals_exit.check(
        score_info=_score_info(available=False),
        target_total=215.5,
        side=TotalSide.OVER.value,
        bid_price=0.30,
        entry_price=0.50,
    )
    assert result is None


def test_returns_none_in_q1_q2_q3() -> None:
    result = nba_totals_exit.check(
        score_info=_score_info(period=2, clock=120, home=40, away=42),
        target_total=215.5,
        side=TotalSide.OVER.value,
        bid_price=0.30,
        entry_price=0.50,
    )
    assert result is None


def test_invalid_side_raises_value_error() -> None:
    # is_total_dead (safe_lead) "over"/"under" dışında ValueError fırlatır.
    with pytest.raises(ValueError, match="side must be"):
        nba_totals_exit.check(
            score_info=_score_info(period=4, clock=30, home=100, away=100),
            target_total=215.5,
            side="middle",
            bid_price=0.30,
            entry_price=0.50,
        )


# ── 1. STRUCTURAL_DAMAGE ──────────────────────────────────────────────────


def test_structural_damage_triggers_when_price_collapsed_and_math_dead() -> None:
    # Q4, clock=30s, OVER, target=220, current=200 → points_needed=20.
    # threshold = 1.218*sqrt(30) ≈ 6.67; 20 > 6.67 → math dead.
    # bid/entry = 0.10/0.50 = 0.20 < 0.30 → struct trigger.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=30, home=100, away=100),
        target_total=220.0,
        side=TotalSide.OVER.value,
        bid_price=0.10,
        entry_price=0.50,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "STRUCTURAL_DAMAGE" in result.detail


def test_structural_damage_does_not_trigger_when_price_healthy() -> None:
    # Q4, clock=400s, OVER, target=215, current=205 → needed=10.
    # math: 1.218*sqrt(400) ≈ 24.36; 10 < 24.36 → math NOT dead.
    # bid/entry=0.40/0.50=0.80 → struct atlanır. predictive disabled.
    # empirical: clock 400 > q4_late_seconds 360 → empirical atlanır.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=105),
        target_total=215.0,
        side=TotalSide.OVER.value,
        bid_price=0.40,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None


# ── 2. TOTALS_MATH_DEAD ───────────────────────────────────────────────────


def test_totals_math_dead_triggers_for_over() -> None:
    # Q4 OVER, clock=30s, needed=20 → math dead. bid/entry healthy.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=30, home=100, away=100),
        target_total=220.0,
        side=TotalSide.OVER.value,
        bid_price=0.40,
        entry_price=0.50,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "TOTALS_MATH_DEAD" in result.detail


def test_totals_math_dead_does_not_trigger_when_within_threshold() -> None:
    # Q4 OVER, clock=400s, target=215, current=200 → needed=15.
    # threshold = 1.218*sqrt(400) ≈ 24.36; 15 < 24.36 → math NOT dead.
    # Empirical: q4_late_seconds=360 < 400 → empirical also skipped.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=100),
        target_total=215.0,
        side=TotalSide.OVER.value,
        bid_price=0.50,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None


# ── 3. PREDICTIVE_DEAD ─────────────────────────────────────────────────────


def test_predictive_dead_triggers_when_bid_exceeds_comeback() -> None:
    # Q4 OVER, clock=400s, needed=15. threshold≈24.36 → math NOT dead.
    # z = 15/(0.5270*sqrt(400)) = 15/10.54 ≈ 1.423; comeback = 0.5*(1-erf(1.006)) ≈ 0.077.
    # 0.077 < 0.20 (not hold). bid+safety = 0.10+0.03 = 0.13 > 0.077 → EXIT.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=100),
        target_total=215.0,
        side=TotalSide.OVER.value,
        bid_price=0.10,
        entry_price=0.50,
    )
    assert result is not None
    assert result.reason == ExitReason.PREDICTIVE_DEAD
    assert "PREDICTIVE_DEAD" in result.detail


def test_predictive_dead_does_not_trigger_when_disabled() -> None:
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=100),
        target_total=215.0,
        side=TotalSide.OVER.value,
        bid_price=0.10,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None


# ── 4. EMPIRICAL_DEAD ─────────────────────────────────────────────────────


def test_empirical_dead_over_triggers_when_points_needed_above_gap() -> None:
    # Q4 OVER, clock=300s (≤360), needed=8 (>7=q4_late_gap). Math: thr=1.218*sqrt(300)
    # ≈21.1; 8 < 21.1 → math NOT dead. predictive disabled. Empirical → trigger.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=300, home=100, away=100),
        target_total=208.0,
        side=TotalSide.OVER.value,
        bid_price=0.50,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "EMPIRICAL_DEAD" in result.detail


def test_empirical_dead_under_triggers_when_excess_above_gap() -> None:
    # Q4 UNDER, clock=300s, target=200, current=210 → -points_diff = 10 > 7 → DEAD.
    # Math: needed=-10; UNDER threshold check uses -points_needed=10; 1.218*sqrt(300)≈21.1
    # 10 < 21.1 → math NOT dead. predictive_disabled. Empirical → trigger.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=300, home=105, away=105),
        target_total=200.0,
        side=TotalSide.UNDER.value,
        bid_price=0.50,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "EMPIRICAL_DEAD" in result.detail


def test_empirical_dead_does_not_trigger_when_gap_below_thresholds() -> None:
    # Q4 OVER, clock=300s (≤360), needed=6 (<7). Final=180? 300>180. Endgame=60? 300>60.
    # → empirical False. Math: 6 < 21.1. predictive disabled.
    result = nba_totals_exit.check(
        score_info=_score_info(period=4, clock=300, home=100, away=100),
        target_total=206.0,
        side=TotalSide.OVER.value,
        bid_price=0.50,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None
