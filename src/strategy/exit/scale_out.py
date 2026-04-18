"""Config-driven scale-out (TDD §6.6) — pure.

Tier'lar config.yaml'dan okunur. Hardcoded sabit YOK (ARCH_GUARD Kural 6).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScaleOutDecision:
    tier: int
    sell_pct: float
    reason: str


def check_scale_out(
    scale_out_tier: int,
    unrealized_pnl_pct: float,
    tiers: list[dict],
) -> ScaleOutDecision | None:
    """Pozisyon bir sonraki tier'a hak kazandi mi? None → hayir.

    tiers: config'den gelen [{"threshold": 0.35, "sell_pct": 0.25}, ...] listesi.
    scale_out_tier: pozisyonun su an gecmis oldugu tier (0 = hic, 1 = ilk tier, ...).
    """
    for i, tier in enumerate(tiers):
        tier_num = i + 1
        if scale_out_tier < tier_num and unrealized_pnl_pct >= tier["threshold"]:
            return ScaleOutDecision(
                tier=tier_num,
                sell_pct=tier["sell_pct"],
                reason=f"Tier {tier_num} at +{unrealized_pnl_pct:.0%}",
            )
    return None
