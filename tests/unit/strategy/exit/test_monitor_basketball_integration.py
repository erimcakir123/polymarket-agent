"""Monitor → NBA dispatch entegrasyonu (SPEC-J Group 4A).

monitor.evaluate basketbol pos için totals dispatch çağırmalı.
NOT: SPREADS dispatch 2026-05-15 rollback ile silindi (0 trade dead code).
Öncelik: near_resolve > scale_out > basketball dispatch (totals) > flat SL > graduated SL stack.
"""
from __future__ import annotations

from src.config.settings import BasketballExitConfig
from src.models.enums import Direction, ExitReason, SportsMarketType, TotalSide
from src.models.position import Position
from src.strategy.exit.monitor import evaluate


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction=Direction.BUY_YES.value,
        entry_price=0.50, size_usdc=10.0, shares=20.0,
        slug="nba-bos-mia-2026-04-15-totals-over-220",
        anchor_probability=0.55, current_price=0.40, bid_price=0.10,
        confidence="B", sport_tag="nba",
        sports_market_type=SportsMarketType.TOTALS,
        total_line=220.0,
        total_side=TotalSide.OVER,
    )
    base.update(over)
    return Position(**base)


def _score_q4_totals_dead() -> dict:
    """Q4, son 30s, OVER 220 hedef ama current 200 → TOTALS_MATH_DEAD."""
    return {
        "available": True,
        "period_number": 4,
        "clock_seconds": 30,
        "home_score": 100,
        "away_score": 100,
    }


def _score_q1_safe() -> dict:
    """Q1, dispatch HOLD döner (Q1-Q3 → None)."""
    return {
        "available": True,
        "period_number": 1,
        "clock_seconds": 600,
        "home_score": 20,
        "away_score": 22,
    }


# ── Dispatch tetiklenmesi ──

def test_monitor_basketball_totals_dispatch_called() -> None:
    """NBA totals + Q4 dispatch → SCORE_EXIT döner."""
    p = _pos()
    r = evaluate(
        p,
        score_info=_score_q4_totals_dead(),
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT


# ── Dispatch'i atlama (moneyline, spreads, non-basketball) ──

def test_monitor_basketball_moneyline_skips_dispatch() -> None:
    """NBA moneyline → dispatch ÇAĞRILMAZ; normal flow (None döner)."""
    p = _pos(
        sports_market_type=SportsMarketType.MONEYLINE,
        total_line=None,
        total_side=None,
        slug="nba-bos-mia-2026-04-15-team-wins",
    )
    r = evaluate(
        p,
        score_info=_score_q4_totals_dead(),
        basketball_exit_cfg=BasketballExitConfig(),
    )
    # Dispatch atlanır, normal flow → calm pozisyon (pnl<25%, eff<0.94, SL korunur)
    assert r.exit_signal is None


def test_monitor_basketball_spreads_skips_dispatch() -> None:
    """NBA spreads → dispatch ÇAĞRILMAZ (2026-05-15 rollback ile spreads dispatch dışı)."""
    p = _pos(
        sports_market_type=SportsMarketType.SPREADS,
        total_line=None,
        total_side=None,
        slug="nba-bos-mia-2026-04-15-spread-home-cover",
    )
    r = evaluate(
        p,
        score_info=_score_q4_totals_dead(),
        basketball_exit_cfg=BasketballExitConfig(),
    )
    # Dispatch atlanır, normal flow → calm pozisyon (pnl<25%, eff<0.94, SL korunur)
    assert r.exit_signal is None


def test_monitor_non_basketball_skips_dispatch() -> None:
    """NHL totals → dispatch ÇAĞRILMAZ (basketbol dışı)."""
    p = _pos(sport_tag="nhl")
    r = evaluate(
        p,
        score_info=_score_q4_totals_dead(),
        basketball_exit_cfg=BasketballExitConfig(),
    )
    # Dispatch atlanır → normal flow → SCORE_EXIT yerine None
    assert r.exit_signal is None


# ── Dispatch HOLD fallthrough ──

def test_monitor_basketball_no_exit_falls_through() -> None:
    """Q1-Q3 totals → dispatch None döner → normal SL/graduated flow çalışır."""
    p = _pos(current_price=0.48, entry_price=0.50)  # küçük zarar, sakin
    r = evaluate(
        p,
        score_info=_score_q1_safe(),
        basketball_exit_cfg=BasketballExitConfig(),
    )
    # Dispatch None → flow devam → SL tetiklenmez (pnl ~ -4%)
    assert r.exit_signal is None


# ── Öncelik: scale_out > dispatch ──

def test_monitor_basketball_dispatch_runs_after_scale_out() -> None:
    """Hem scale_out hem totals death → scale_out kazanır (öncelik korunur)."""
    # entry 0.40, current 0.50, shares=25 → pnl = (25*0.50 - 10)/10 = 25% → tier 1
    p = _pos(
        entry_price=0.40, current_price=0.50, size_usdc=10.0, shares=25.0,
    )
    r = evaluate(
        p,
        score_info=_score_q4_totals_dead(),
        basketball_exit_cfg=BasketballExitConfig(),
    )
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCALE_OUT
    assert r.exit_signal.partial is True
