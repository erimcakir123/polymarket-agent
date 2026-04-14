"""scale_out.py için birim testler (TDD §6.6)."""
from __future__ import annotations

from src.strategy.exit.scale_out import ScaleOutDecision, check_scale_out


def test_tier1_fires_at_25pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.25, volatility_swing=False)
    assert isinstance(r, ScaleOutDecision)
    assert r.tier == 1
    assert r.sell_pct == 0.40


def test_tier1_fires_above_25pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.30, volatility_swing=False)
    assert r is not None
    assert r.tier == 1


def test_tier1_skipped_below_25pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.24, volatility_swing=False)
    assert r is None


def test_tier2_fires_at_50pct_after_tier1() -> None:
    r = check_scale_out(scale_out_tier=1, unrealized_pnl_pct=0.50, volatility_swing=False)
    assert r is not None
    assert r.tier == 2
    assert r.sell_pct == 0.50


def test_tier2_needs_tier1_done() -> None:
    # scale_out_tier=0 ama 50% kazanç → tier 1 döner (50% > 25%), tier 2 değil
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, volatility_swing=False)
    assert r is not None
    assert r.tier == 1  # Önce tier 1


def test_tier3_no_pnl_trigger() -> None:
    # scale_out_tier=2 → Tier 3 PnL-triggered değil (resolution ile kapanır)
    r = check_scale_out(scale_out_tier=2, unrealized_pnl_pct=0.80, volatility_swing=False)
    assert r is None


def test_vs_skipped() -> None:
    # Volatility swing scale-out'a girmez
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, volatility_swing=True)
    assert r is None
