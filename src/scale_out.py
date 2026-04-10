# src/scale_out.py
"""3-tier scale-out (partial exit) system.

Tier 1 (Risk-Free): +25% PnL -> sell 40%
Tier 2 (Profit Lock): +50% PnL -> sell 50% of remaining
Tier 3 (Final): resolution/trailing/exit -> sell all remaining

Note: VS (volatility_swing) positions are skipped -- they have their own TP.
Scouted "hold to resolve" positions intentionally participate in scale-out (spec 9j).
"""
from __future__ import annotations


SCALE_OUT_TIERS = {
    "tier1_risk_free": {"trigger_pnl_pct": 0.25, "sell_pct": 0.40},
    "tier2_profit_lock": {"trigger_pnl_pct": 0.50, "sell_pct": 0.50},
}


def check_scale_out(
    scale_out_tier: int,
    unrealized_pnl_pct: float,
    volatility_swing: bool,
) -> dict | None:
    """Check if position qualifies for next scale-out tier. Pure function."""
    if volatility_swing:
        return None

    # PnL-based tiers
    if scale_out_tier == 0 and unrealized_pnl_pct >= 0.25:
        return {
            "action": "scale_out",
            "tier": "tier1_risk_free",
            "sell_pct": 0.40,
            "reason": f"Tier 1: Risk-free at +{unrealized_pnl_pct:.0%}",
        }

    if scale_out_tier == 1 and unrealized_pnl_pct >= 0.50:
        return {
            "action": "scale_out",
            "tier": "tier2_profit_lock",
            "sell_pct": 0.50,
            "reason": f"Tier 2: Profit lock at +{unrealized_pnl_pct:.0%}",
        }

    return None


def apply_partial_exit(
    shares: float,
    size_usdc: float,
    entry_price: float,
    direction: str,
    shares_sold: float,
    fill_price: float,
    tier: str,
    original_shares: float | None,
    original_size_usdc: float | None,
    scale_out_tier: int,
) -> dict:
    """Compute partial exit results. Pure function -- returns new values, doesn't mutate."""
    # Snapshot originals on first partial
    if original_shares is None:
        original_shares = shares
    if original_size_usdc is None:
        original_size_usdc = size_usdc

    # Realized PnL (direction-safe)
    cost_basis_sold = size_usdc * (shares_sold / shares)
    if direction == "BUY_NO":
        proceeds = shares_sold * (1 - fill_price)
    else:
        proceeds = shares_sold * fill_price
    realized_pnl = proceeds - cost_basis_sold

    # Remaining position
    reduction_ratio = shares_sold / shares
    remaining_shares = shares - shares_sold
    remaining_size_usdc = size_usdc * (1 - reduction_ratio)
    new_tier = scale_out_tier + 1

    # Dust check
    if remaining_size_usdc < 0.50 or remaining_shares < 1.0:
        status = "CLOSE_REMAINDER"
    else:
        status = "OK"

    return {
        "status": status,
        "remaining_shares": remaining_shares,
        "remaining_size_usdc": remaining_size_usdc,
        "realized_pnl": realized_pnl,
        "proceeds": proceeds,
        "cost_basis_sold": cost_basis_sold,
        "original_shares": original_shares,
        "original_size_usdc": original_size_usdc,
        "new_scale_out_tier": new_tier,
        "tier": tier,
        "pct_of_original": shares_sold / original_shares if original_shares else 0,
    }


def should_scale_in(
    unrealized_pnl_pct: float,
    cycles_held: int,
    scale_in_complete: bool,
    intended_size_usdc: float,
    current_size_usdc: float,
    score_ahead: bool = False,
    min_pnl_pct: float = 0.02,
    min_cycles: int = 3,
) -> tuple[bool, str]:
    """Check if position should scale in (add to winning position)."""
    if scale_in_complete:
        return False, "Scale-in already complete"
    if current_size_usdc >= intended_size_usdc:
        return False, "Already at intended size"
    if cycles_held < min_cycles:
        return False, f"Need {min_cycles} cycles, have {cycles_held}"
    if unrealized_pnl_pct < 0:
        return False, f"Position losing ({unrealized_pnl_pct:.1%}), no scale-in"
    pnl_confirmed = unrealized_pnl_pct >= min_pnl_pct
    if not pnl_confirmed and not score_ahead:
        return False, f"PnL {unrealized_pnl_pct:.1%} < {min_pnl_pct:.0%} and no score advantage"
    return True, "Position confirmed -- scale in"


def get_scale_in_size(
    intended_size_usdc: float,
    current_size_usdc: float,
    kelly_size_now: float,
) -> float:
    """Size based on Kelly re-evaluation. Returns min(remaining_intended, kelly_gap)."""
    remaining = intended_size_usdc - current_size_usdc
    if remaining <= 0:
        return 0.0
    kelly_gap = kelly_size_now - current_size_usdc
    if kelly_gap <= 0:
        return 0.0
    return min(remaining, kelly_gap)
