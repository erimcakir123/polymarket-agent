"""nba_spread_exit.check() unit testleri."""
from __future__ import annotations

import pytest
from src.strategy.exit.nba_spread_exit import check
from src.models.enums import ExitReason


def _si(
    period_number: int = 4,
    clock_seconds: int = 300,
    our_score: int = 95,
    opp_score: int = 100,
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


_M = 0.861


def test_period_3_always_hold():
    """Q1-Q3 → None."""
    result = check(
        score_info=_si(period_number=3, clock_seconds=60, our_score=90, opp_score=105),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_unavailable_score_hold():
    result = check(
        score_info={"available": False},
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_math_dead_buy_yes_q4():
    """BUY_YES, trailing by 12 with 5.5 spread, 60s left → margin=17.5 > threshold(6.67) → dead."""
    # our_score=88, opp_score=100 → actual_diff=-12
    # margin_to_cover = 5.5 - (-12) = 17.5
    # 0.861 * sqrt(60) = 6.67 → 17.5 >= 6.67 → True
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, our_score=88, opp_score=100),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.20,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "SPREAD_MATH_DEAD" in result.detail
    assert result.sell_pct == 1.0
    assert result.partial is False


def test_math_dead_buy_no_q4():
    """BUY_NO underdog, favorite leading by 20 with 7.5 spread, 120s → margin=12.5 >= 9.43 → dead."""
    # our=80, opp=100 → actual_diff=-20
    # BUY_NO: margin_to_cover = -actual_diff - spread_line = 20 - 7.5 = 12.5
    # 0.861 * sqrt(120) = 9.43 → 12.5 >= 9.43 → True
    result = check(
        score_info=_si(period_number=4, clock_seconds=120, our_score=80, opp_score=100),
        spread_line=7.5,
        direction="BUY_NO",
        bid_price=0.20,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "SPREAD_MATH_DEAD" in result.detail


def test_empirical_q4_endgame_key_number_3():
    """Q4 son 60s, margin_to_cover=3 → EMPIRICAL_DEAD."""
    # BUY_YES, our=97, opp=100 → actual_diff=-3, spread_line=0
    # margin=0 - (-3) = 3 >= q4_endgame_margin=3 AND clock<=60 → True
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, our_score=97, opp_score=100),
        spread_line=0.0,
        direction="BUY_YES",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_empirical_q4_late_key_number_7():
    """Q4 360s kala, margin_to_cover=11 >= q4_late_margin=7 → EMPIRICAL_DEAD."""
    # our=93, opp=100, spread=4 → actual_diff=-7, margin=4-(-7)=11 ≥ 7
    result = check(
        score_info=_si(period_number=4, clock_seconds=360, our_score=93, opp_score=100),
        spread_line=4.0,
        direction="BUY_YES",
        bid_price=0.25,
        entry_price=0.60,
        bill_james_multiplier=_M,
        q4_late_margin=7,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_structural_damage_q4():
    """Q4, fiyat entry'nin %30'unun altı + math dead → STRUCTURAL_DAMAGE."""
    # entry=0.60, bid=0.17 → ratio=0.283 < 0.30
    # our=85, opp=100, spread=5.5, 120s
    # margin=5.5-(-15)=20.5 → 0.861*sqrt(120)=9.43 → dead
    result = check(
        score_info=_si(period_number=4, clock_seconds=120, our_score=85, opp_score=100),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.17,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "STRUCTURAL" in result.detail


def test_covering_spread_alive():
    """Cover'dayız (margin_to_cover < 0) → None."""
    # our=106, opp=100, spread=5.5 → actual_diff=6 → margin=5.5-6=-0.5 < 0 → alive
    result = check(
        score_info=_si(period_number=4, clock_seconds=300, our_score=106, opp_score=100),
        spread_line=5.5,
        direction="BUY_YES",
        bid_price=0.60,
        entry_price=0.50,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_ot_spread_dead():
    """OT, son 60s, margin_to_cover >= 8 → OT_DEAD."""
    # our=90, opp=100, spread=0 → margin=10, period=5
    result = check(
        score_info=_si(period_number=5, clock_seconds=60, our_score=90, opp_score=100),
        spread_line=0.0,
        direction="BUY_YES",
        bid_price=0.15,
        entry_price=0.60,
        bill_james_multiplier=_M,
        ot_seconds=60,
        ot_margin=8,
    )
    assert result is not None
    assert "OT_DEAD" in result.detail
