"""scale_out.py için birim testler (TDD §6.6)."""
from __future__ import annotations

from src.strategy.exit.scale_out import ScaleOutDecision, check_scale_out


def test_tier1_fires_at_25pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.25)
    assert isinstance(r, ScaleOutDecision)
    assert r.tier == 1
    assert r.sell_pct == 0.40


def test_tier1_fires_above_25pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.30)
    assert r is not None
    assert r.tier == 1


def test_tier1_skipped_below_25pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.24)
    assert r is None


def test_tier2_fires_at_50pct_after_tier1() -> None:
    r = check_scale_out(scale_out_tier=1, unrealized_pnl_pct=0.50)
    assert r is not None
    assert r.tier == 2
    assert r.sell_pct == 0.50


def test_tier2_needs_tier1_done() -> None:
    # scale_out_tier=0 ama 50% kazanç → tier 1 döner (50% > 25%), tier 2 değil
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50)
    assert r is not None
    assert r.tier == 1  # Önce tier 1


def test_tier3_no_pnl_trigger() -> None:
    # scale_out_tier=2 → Tier 3 PnL-triggered değil (resolution ile kapanır)
    r = check_scale_out(scale_out_tier=2, unrealized_pnl_pct=0.80)
    assert r is None


def test_tier1_skipped_when_realized_below_min() -> None:
    """SPEC-F: Tier 1 tetiklenmeli ama realized estimate < min → skip."""
    # %25 PnL × $20 size × %40 sell = $2 realized → min=$7 altı → skip
    result = check_scale_out(
        scale_out_tier=0,
        unrealized_pnl_pct=0.25,
        unrealized_pnl_usdc=5.0,  # %25 of $20
        min_realized_usdc=7.0,
    )
    assert result is None


def test_tier1_fires_when_realized_above_min() -> None:
    """SPEC-F: realized estimate >= min → normal tetiklenme."""
    # %25 × $80 × %40 = $8 realized >= $7 → fires
    result = check_scale_out(
        scale_out_tier=0,
        unrealized_pnl_pct=0.25,
        unrealized_pnl_usdc=20.0,  # %25 of $80
        min_realized_usdc=7.0,
    )
    assert result is not None
    assert result.tier == 1


def test_tier2_skipped_when_realized_below_min() -> None:
    """SPEC-F: Tier 2 (50% sell) realized < min → skip."""
    # %50 × $10 × %50 sell = $2.5 realized → min=$7 altı → skip
    result = check_scale_out(
        scale_out_tier=1,
        unrealized_pnl_pct=0.50,
        unrealized_pnl_usdc=5.0,
        min_realized_usdc=7.0,
    )
    assert result is None


def test_min_realized_default_zero_backwards_compat() -> None:
    """Default min_realized=0 → eski davranış korunur (her PnL>=25% tetikler)."""
    result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.25)
    assert result is not None
    assert result.tier == 1
