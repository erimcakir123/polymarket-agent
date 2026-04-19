"""Config-driven scale-out — pure, midpoint-to-resolution semantigi (SPEC-013).

Tier'lar config.yaml'dan okunur. `threshold` semantigi:
  entry_price + threshold × (0.99 - entry_price) fiyatinda tetikler.
  (threshold = 0.5 -> entry ile 0.99 arasinin yarisi)

Bu semantik eski "PnL %" yaklasimini replace eder cunku PnL % entry fiyatina
bagli olarak cok farkli noktalarda tetikleyebiliyordu (43c entry'de +%15 PnL =
50c fiyat; 70c entry'de +%15 PnL = 80c fiyat). Yeni semantik "kalan mesafe" ile
calistigi icin her entry icin adil.

Hardcoded sabit YOK (ARCH_GUARD Kural 6). _RESOLUTION_PRICE Polymarket
payout cap (near_resolve threshold 94c'den yuksek ama 1.0 degil — fee/spread).
"""
from __future__ import annotations

from dataclasses import dataclass

_RESOLUTION_PRICE = 0.99  # Polymarket near-resolve cap


@dataclass
class ScaleOutDecision:
    tier: int
    sell_pct: float
    reason: str


def check_scale_out(
    scale_out_tier: int,
    entry_price: float,
    current_price: float,
    tiers: list[dict],
) -> ScaleOutDecision | None:
    """Pozisyon bir sonraki tier'a hak kazandi mi?

    Args:
      scale_out_tier: pozisyonun su an gecmis oldugu tier (0 = hic, 1 = ilk tier, ...).
      entry_price: effective entry (BUY_YES icin yes_price, BUY_NO icin no_price).
      current_price: current effective price (ayni taraf).
      tiers: config'den [{"threshold": 0.50, "sell_pct": 0.40}, ...].
             threshold = fraction of distance from entry to resolution (0.99).

    Returns:
      ScaleOutDecision if next tier triggered, None otherwise.
    """
    if not tiers:
        return None
    if entry_price >= _RESOLUTION_PRICE:
        return None  # Giris zaten resolution'da, scale-out anlamsiz
    if current_price <= entry_price:
        return None  # Kar yok, scale-out yok

    max_distance = _RESOLUTION_PRICE - entry_price
    current_distance = current_price - entry_price
    distance_fraction = current_distance / max_distance

    for i, tier in enumerate(tiers):
        tier_num = i + 1
        if scale_out_tier < tier_num and distance_fraction >= tier["threshold"]:
            return ScaleOutDecision(
                tier=tier_num,
                sell_pct=tier["sell_pct"],
                reason=f"Tier {tier_num} at {distance_fraction*100:.0f}% of distance to resolution",
            )
    return None
