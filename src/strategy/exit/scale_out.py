"""3-tier scale-out (TDD §6.6) — pure.

Tier 1 (Risk-Free):   PnL ≥ +25% → %40 sat
Tier 2 (Profit-Lock): PnL ≥ +50% → kalan %50 sat
Tier 3 (Final):       Resolution / trailing / exit → hepsini sat (PnL-triggered değil)
"""
from __future__ import annotations

from dataclasses import dataclass

TIER1_TRIGGER_PNL = 0.25
TIER1_SELL_PCT = 0.40
TIER2_TRIGGER_PNL = 0.50
TIER2_SELL_PCT = 0.50


@dataclass
class ScaleOutDecision:
    tier: int          # 1, 2 — hangi tier tetiklendi
    sell_pct: float    # Pozisyonun ne kadarını sat
    reason: str


def check_scale_out(
    scale_out_tier: int,
    unrealized_pnl_pct: float,
) -> ScaleOutDecision | None:
    """Pozisyon bir sonraki tier'a hak kazandı mı? None → hayır."""
    if scale_out_tier == 0 and unrealized_pnl_pct >= TIER1_TRIGGER_PNL:
        return ScaleOutDecision(
            tier=1,
            sell_pct=TIER1_SELL_PCT,
            reason=f"Tier 1 (risk-free) at +{unrealized_pnl_pct:.0%}",
        )

    if scale_out_tier == 1 and unrealized_pnl_pct >= TIER2_TRIGGER_PNL:
        return ScaleOutDecision(
            tier=2,
            sell_pct=TIER2_SELL_PCT,
            reason=f"Tier 2 (profit-lock) at +{unrealized_pnl_pct:.0%}",
        )

    return None
