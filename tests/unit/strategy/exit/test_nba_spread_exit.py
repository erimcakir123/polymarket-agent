"""NBA spread exit — 5-katman pipeline (SPEC-J Group 3A).

Pipeline sırası:
  1. OT_DEAD       (period > 4)
  2. STRUCTURAL_DAMAGE (Q4 + bid/entry < 0.30 + spread_dead)
  3. SPREAD_MATH_DEAD  (Q4 + Bill James 0.861)
  4. PREDICTIVE_DEAD   (Q4 + EV bazlı)
  5. EMPIRICAL_DEAD    (Q4 + key numbers)
"""
from __future__ import annotations

from src.models.enums import Direction, ExitReason
from src.strategy.exit import nba_spread_exit


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


# ── 0. score_info eksik / Q1-Q3 hold ──────────────────────────────────────


def test_returns_none_when_score_unavailable() -> None:
    result = nba_spread_exit.check(
        score_info=_score_info(available=False),
        spread_line=-7.5,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.30,
        entry_price=0.50,
    )
    assert result is None


def test_returns_none_in_q1_q2_q3() -> None:
    # Q3, geride bile olsa hold (sadece Q4'te ve OT'de exit pipeline çalışır).
    result = nba_spread_exit.check(
        score_info=_score_info(period=3, clock=120, home=80, away=100),
        spread_line=-7.5,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.10,
        entry_price=0.55,
    )
    assert result is None


# ── 1. OT_DEAD ─────────────────────────────────────────────────────────────


def test_ot_dead_triggers_when_margin_ge_8_in_last_minute() -> None:
    # OT (period=5), clock=30s, ev sahibi 8 sayı geride, BUY_YES home spread.
    # actual_diff = 100 - 108 = -8; margin_to_cover = -7.5 - (-8) = 0.5
    # margin yetersiz; bunu zorlamak için spread_line=0.0 (pickem) + 8 sayı geri.
    result = nba_spread_exit.check(
        score_info=_score_info(period=5, clock=45, home=100, away=108),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.10,
        entry_price=0.50,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "OT_DEAD" in result.detail


def test_ot_dead_does_not_trigger_when_margin_below_8() -> None:
    # OT, 7 sayı geride → margin=7 < 8 → no exit.
    result = nba_spread_exit.check(
        score_info=_score_info(period=5, clock=45, home=100, away=107),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.10,
        entry_price=0.50,
    )
    assert result is None


# ── 2. STRUCTURAL_DAMAGE ──────────────────────────────────────────────────


def test_structural_damage_triggers_when_price_collapsed_and_math_dead() -> None:
    # Q4, clock=30s, 6 sayı geride; bid/entry = 0.10/0.50 = 0.20 < 0.30; math dead.
    # actual_diff = 100 - 106 = -6; margin = 0 - (-6) = 6; sqrt(30)*0.861 ≈ 4.71
    # margin 6 >= 4.71 → spread_dead=True
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=30, home=100, away=106),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.10,
        entry_price=0.50,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "STRUCTURAL_DAMAGE" in result.detail


def test_structural_damage_does_not_trigger_when_price_healthy() -> None:
    # Q4, 6 sayı geride, ama bid/entry 0.40/0.50 = 0.80 → struct check geçer
    # ama math_dead aşağıdaki layer 3 SPREAD_MATH_DEAD'i tetikler. Struct test
    # için math_dead'i de geçirmeliyiz: clock=200, margin=2 → sqrt(200)*0.861=12.2,
    # margin 2 < 12.2 → not dead.
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=200, home=100, away=102),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.40,
        entry_price=0.50,
    )
    assert result is None


# ── 3. SPREAD_MATH_DEAD (Bill James) ──────────────────────────────────────


def test_spread_math_dead_triggers_at_bill_james_threshold() -> None:
    # Q4, clock=30s, 6 sayı geride, fiyat çökmemiş (bid/entry > 0.30).
    # margin=6, sqrt(30)*0.861 ≈ 4.71 → 6 >= 4.71 → math dead.
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=30, home=100, away=106),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.40,
        entry_price=0.50,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "SPREAD_MATH_DEAD" in result.detail


def test_spread_math_dead_does_not_trigger_when_within_threshold() -> None:
    # Q4, clock=400s, 8 sayı geride; sqrt(400)*0.861 ≈ 17.2; margin 8 < 17.2.
    # Empirical layer'a düşmemek için clock=400 > 360 (q4_late_seconds).
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=108),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.40,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None


# ── 4. PREDICTIVE_DEAD ─────────────────────────────────────────────────────


def test_predictive_dead_triggers_when_bid_exceeds_comeback() -> None:
    # Q4, clock=400s (math_dead bypass: sqrt(400)*0.861=17.2; margin 12 < 17.2).
    # actual_diff = 100 - 112 = -12; margin = 12.
    # z = 12/(0.3727*sqrt(400)) ≈ 1.61; comeback ≈ 0.054 < 0.20 (not hold).
    # bid + safety = 0.10 + 0.03 = 0.13 > 0.054 → EXIT.
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=112),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.10,
        entry_price=0.50,  # bid/entry=0.20<0.30 ama math_dead False → struct atlanır
    )
    assert result is not None
    assert result.reason == ExitReason.PREDICTIVE_DEAD
    assert "PREDICTIVE_DEAD" in result.detail


def test_predictive_dead_does_not_trigger_when_disabled() -> None:
    # Aynı koşul, predictive_enabled=False → empirical clock 400s > 360s gate de
    # tetiklemez (q4_late_seconds=360, q4_late_margin=7; 400 > 360).
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=400, home=100, away=112),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.10,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None


# ── 5. EMPIRICAL_DEAD ─────────────────────────────────────────────────────


def test_empirical_dead_triggers_late_window_margin_7() -> None:
    # Q4 late: clock=300s (≤360), margin=7. Math: sqrt(300)*0.861=14.9; margin 7 < 14.9
    # → math_dead False. Predictive disabled. Empirical: 300 ≤ 360 ve 7 ≥ 7 → DEAD.
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=300, home=100, away=107),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.50,
        entry_price=0.50,  # bid/entry=1.0 → struct atlanır
        predictive_enabled=False,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "EMPIRICAL_DEAD" in result.detail


def test_empirical_dead_does_not_trigger_when_margin_below_thresholds() -> None:
    # Q4 late: clock=300s, margin=6 (≤7? hayır, 6<7). Final: 300>180. Endgame: 300>60
    # → empirical False. Math: sqrt(300)*0.861=14.9; 6 < 14.9 → math False.
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=300, home=100, away=106),
        spread_line=0.0,
        direction=Direction.BUY_YES.value,
        spread_side="home",
        bid_price=0.50,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is None


# ── BUY_NO yönü ────────────────────────────────────────────────────────────


def test_buy_no_away_spread_margin_calculation_correct() -> None:
    # BUY_NO away spread → spread_line=-3.5 means we bet AGAINST away covering by 3.5.
    # Pre-rollback formula: BUY_NO → margin_to_cover = -actual_diff - spread_line.
    # Mapper: BUY_NO away → "biz" home → our=home, opp=away.
    # Q4 late, clock=300, home=100, away=110. actual_diff = our - opp = 100-110 = -10.
    # margin = -(-10) - (-3.5) = 10 + 3.5 = 13.5. Math dead (sqrt(300)*0.861=14.9? 13.5<14.9 marginal)
    # Empirical: 300 ≤ 360 ve 13.5 ≥ 7 → EMPIRICAL DEAD.
    result = nba_spread_exit.check(
        score_info=_score_info(period=4, clock=300, home=100, away=110),
        spread_line=-3.5,
        direction=Direction.BUY_NO.value,
        spread_side="away",
        bid_price=0.50,
        entry_price=0.50,
        predictive_enabled=False,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
