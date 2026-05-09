"""3-tier scale-out (TDD §6.6) — pure.

Tier 1 (Risk-Free):   PnL ≥ +25% → %40 sat
Tier 2 (Profit-Lock): PnL ≥ +50% → kalan %50 sat
Tier 3 (Final):       Resolution / trailing / exit → hepsini sat (PnL-triggered değil)

Min realized USD gate: hesaplanan realized < min_realized_usdc ise tetikleme atlanır
(küçük pozisyonlarda anlamsız scale-out engelle).
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
    unrealized_pnl_usdc: float = 0.0,
    min_realized_usdc: float = 0.0,
) -> ScaleOutDecision | None:
    """Pozisyon bir sonraki tier'a hak kazandı mı? None → hayır.

    Tetiklenme öncesi realized estimate kontrol edilir: realized < min_realized_usdc
    ise None döner. Geri uyumluluk için her iki yeni param 0.0 default.
    """
    if scale_out_tier == 0 and unrealized_pnl_pct >= TIER1_TRIGGER_PNL:
        realized_estimate = unrealized_pnl_usdc * TIER1_SELL_PCT
        if realized_estimate < min_realized_usdc:
            return None
        return ScaleOutDecision(
            tier=1,
            sell_pct=TIER1_SELL_PCT,
            reason=f"Tier 1 (risk-free) at +{unrealized_pnl_pct:.0%}",
        )

    if scale_out_tier == 1 and unrealized_pnl_pct >= TIER2_TRIGGER_PNL:
        realized_estimate = unrealized_pnl_usdc * TIER2_SELL_PCT
        if realized_estimate < min_realized_usdc:
            return None
        return ScaleOutDecision(
            tier=2,
            sell_pct=TIER2_SELL_PCT,
            reason=f"Tier 2 (profit-lock) at +{unrealized_pnl_pct:.0%}",
        )

    return None
