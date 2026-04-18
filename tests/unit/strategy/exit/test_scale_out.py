"""scale_out.py icin birim testler (TDD §6.6) — config-driven."""
from __future__ import annotations

from src.strategy.exit.scale_out import ScaleOutDecision, check_scale_out

TIERS = [
    {"threshold": 0.35, "sell_pct": 0.25},
    {"threshold": 0.50, "sell_pct": 0.50},
]


def test_tier1_fires_at_35pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.35, tiers=TIERS)
    assert isinstance(r, ScaleOutDecision)
    assert r.tier == 1
    assert r.sell_pct == 0.25


def test_tier1_fires_above_35pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.40, tiers=TIERS)
    assert r is not None
    assert r.tier == 1


def test_tier1_skipped_below_35pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.34, tiers=TIERS)
    assert r is None


def test_tier2_fires_at_50pct_after_tier1() -> None:
    r = check_scale_out(scale_out_tier=1, unrealized_pnl_pct=0.50, tiers=TIERS)
    assert r is not None
    assert r.tier == 2
    assert r.sell_pct == 0.50


def test_tier2_needs_tier1_done() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, tiers=TIERS)
    assert r is not None
    assert r.tier == 1  # Tier 1 once tetiklenir


def test_beyond_max_tier_returns_none() -> None:
    r = check_scale_out(scale_out_tier=2, unrealized_pnl_pct=0.80, tiers=TIERS)
    assert r is None


def test_empty_tiers_returns_none() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, tiers=[])
    assert r is None


def test_single_tier_works() -> None:
    single = [{"threshold": 0.50, "sell_pct": 0.50}]
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, tiers=single)
    assert r is not None
    assert r.tier == 1
    assert r.sell_pct == 0.50


def test_old_tier1_threshold_no_trigger() -> None:
    """Eski +%25 esigi artik tetiklenmez."""
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.25, tiers=TIERS)
    assert r is None
