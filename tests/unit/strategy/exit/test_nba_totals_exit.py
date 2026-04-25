"""nba_totals_exit.check() unit testleri."""
from __future__ import annotations

from src.strategy.exit.nba_totals_exit import check
from src.models.enums import ExitReason


def _si(
    period_number: int = 4,
    clock_seconds: int = 300,
    our_score: int = 110,
    opp_score: int = 108,
    available: bool = True,
) -> dict:
    return {
        "available": available,
        "period_number": period_number,
        "clock_seconds": clock_seconds,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": opp_score - our_score,
    }


_TM = 1.218


def test_period_3_always_hold():
    result = check(
        score_info=_si(period_number=3, our_score=90, opp_score=85),
        target_total=225.0,
        side="over",
        bid_price=0.45,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is None


def test_unavailable_score_hold():
    result = check(
        score_info={"available": False},
        target_total=220.0,
        side="over",
        bid_price=0.40,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is None


def test_over_math_dead():
    """Over bet, total ulaşılamayacak → TOTALS_MATH_DEAD."""
    # our=90, opp=95 → current_total=185, target=220, points_needed=35
    # 1.218 * sqrt(240) = 18.87 → 35 > 18.87 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=240, our_score=90, opp_score=95),
        target_total=220.0,
        side="over",
        bid_price=0.20,
        entry_price=0.55,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "TOTALS_MATH_DEAD" in result.detail
    assert result.sell_pct == 1.0
    assert result.partial is False


def test_under_math_dead():
    """Under bet, total aşıldı → TOTALS_MATH_DEAD."""
    # our=115, opp=115 → current=230, target=220
    # points_needed=220-230=-10 → -(-10)=10 > 1.218*sqrt(60)=9.44 → dead
    # bid/entry ratio=0.90 → no structural damage (ratio above 0.30 threshold)
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, our_score=115, opp_score=115),
        target_total=220.0,
        side="under",
        bid_price=0.50,
        entry_price=0.55,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "TOTALS_MATH_DEAD" in result.detail


def test_over_empirical_dead_q4_late():
    """Over, Q4 360s, points_needed=20 → EMPIRICAL_DEAD."""
    # our=100, opp=100 → current=200, target=220, points_needed=20
    # math threshold at 360s: 1.218 * sqrt(360) = 23.1 → 20 < 23.1 → math NOT dead
    # empirical: clock=360 ≤ q4_late_seconds=360 and points_needed=20 ≥ q4_late_gap=20 → DEAD
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=100, opp_score=100),
        target_total=220.0,
        side="over",
        bid_price=0.20,
        entry_price=0.55,
        totals_multiplier=_TM,
        q4_late_gap=20,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_under_empirical_dead_q4_late():
    """Under, Q4 360s, current-target=20 → EMPIRICAL_DEAD."""
    # current=240, target=220 → excess=20 ≥ q4_late_gap=20
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=120, opp_score=120),
        target_total=220.0,
        side="under",
        bid_price=0.15,
        entry_price=0.55,
        totals_multiplier=_TM,
        q4_late_gap=20,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_ot_over_windfall():
    """OT + side=over → OT_OVER_WINDFALL (partial, sell 75%)."""
    result = check(
        score_info=_si(period_number=5, clock_seconds=250, our_score=110, opp_score=110),
        target_total=215.0,
        side="over",
        bid_price=0.80,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "OT_OVER_WINDFALL" in result.detail
    assert result.partial is True
    assert result.sell_pct == 0.75


def test_ot_under_dead():
    """OT + side=under → OT_UNDER_DEAD (full exit)."""
    result = check(
        score_info=_si(period_number=5, clock_seconds=250, our_score=108, opp_score=108),
        target_total=210.0,
        side="under",
        bid_price=0.10,
        entry_price=0.55,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "OT_UNDER_DEAD" in result.detail
    assert result.partial is False
    assert result.sell_pct == 1.0


def test_structural_damage_over():
    """Fiyat çöküşü + math dead → STRUCTURAL_DAMAGE."""
    # entry=0.60, bid=0.17 → ratio=0.28 < 0.30
    # current=180, target=225, points_needed=45, 240s → 45 > 18.87 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=240, our_score=90, opp_score=90),
        target_total=225.0,
        side="over",
        bid_price=0.17,
        entry_price=0.60,
        totals_multiplier=_TM,
    )
    assert result is not None
    assert "STRUCTURAL" in result.detail


def test_alive_over_reachable():
    """Over, Q4, points_needed küçük → None."""
    # current=210, target=215, points_needed=5, 360s → 5 < 23.1 → alive
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=105, opp_score=105),
        target_total=215.0,
        side="over",
        bid_price=0.60,
        entry_price=0.50,
        totals_multiplier=_TM,
    )
    assert result is None
