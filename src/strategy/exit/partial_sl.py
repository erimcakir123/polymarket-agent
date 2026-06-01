"""Loss-based partial stop loss — scale-out'un kayıp tarafı simetriği.

Hangi sorunu çözer:
  - Eski sistem: pozisyon %30 düşünce TAMAMINI sat (flat/graduated SL).
  - Sorun: %30 düşüş geçici olabilir, geri dönüş ihtimali var. Tam satış o şansı keser.
  - Yeni: %20 düşüş → %30 sat, %35 düşüş → kalanın %50'sini sat,
          %50 düşüş → kalanı tamamen sat.

Pattern scale_out.py paraleli:
  - tier index (Position.partial_sl_tier) ile takip
  - Pure: I/O yok, dışarıdan parametre alır
  - ExitSignal(partial=True, sell_pct, tier) döner

Mantık (lab-ERKEN dönemi paralellik):
  - Erken parçalı satış güvenlik ağı (scale-out gibi)
  - Tam satış sadece son çare (-50%+)
  - Geçici dipte tüm pozisyonu kaybetmiyoruz
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import PartialSlTier


@dataclass(frozen=True)
class PartialSlDecision:
    tier: int           # 1-indexed: 1 = tier1, 2 = tier2, 3 = tier3
    sell_pct: float     # of remaining shares to sell


def check_partial_sl(
    *,
    partial_sl_tier: int,
    unrealized_pnl_pct: float,
    tiers: list[PartialSlTier],
) -> PartialSlDecision | None:
    """Sıradaki partial SL kararını döner (None = tetik yok).

    partial_sl_tier: zaten kaç tier fire ettiği (0 = hiç, 1 = tier1 fired vs.)
    unrealized_pnl_pct: pozisyonun kâr/zarar yüzdesi (-0.25 = %25 zararda)
    tiers: config.partial_sl.tiers — sırayla [-loss_threshold, sell_pct]
    """
    next_tier_idx = partial_sl_tier
    if next_tier_idx >= len(tiers):
        return None
    tier_cfg = tiers[next_tier_idx]
    # loss_threshold pozitif yüzde (örn. 0.20 = %20 kayıp eşiği)
    if unrealized_pnl_pct <= -tier_cfg.loss_threshold:
        return PartialSlDecision(
            tier=next_tier_idx + 1,
            sell_pct=tier_cfg.sell_pct,
        )
    return None
