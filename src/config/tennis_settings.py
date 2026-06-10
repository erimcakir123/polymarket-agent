"""Tennis-specific pydantic config classes.

Bölünme nedeni: ARCH_GUARD §3 (settings.py 400 satır limitini aştı). Sport-specific
config'ler kendi modülünde — settings.py re-export eder (geri uyumlu import path).
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class TennisConfig(BaseModel):
    """Tennis yetki filtresi config'i (ARCH_GUARD §6 — magic number yasağı).

    max_phi_for_trade: Glicko phi (rating deviation) eşiği. phi >= bu → model
      konuşmaz (~25+ maç oynamamış oyuncu = güvenilmez rating).
    low_tier_slug_prefixes: Polymarket slug prefix bazlı low-tier filter.
    low_tier_question_keywords: Question metni keyword bazlı filter (Polymarket
      bazen "atp-" / "wta-" slug + question'da gerçek tier yazıyor).
    surface_unknown_recheck_days: UNKNOWN damgalı turnuva zemini bu kadar gün
      sonra Wikipedia'dan tekrar sorgulanır (TTL — varsayılan günlük).
    sackmann_max_age_days: Sackmann CSV cache bu yaştan eskiyse tazelenir
      (PLAN-DATA1: 3→1 gün; kaynak ~2-3 haftada bir güncellenir, günlük kontrol
      bedava ve 8 Haz tipi kıl-payı kaçırmaları önler).
    """
    model_config = ConfigDict(extra="ignore")
    max_phi_for_trade: float = 100.0
    surface_unknown_recheck_days: int = 1
    sackmann_max_age_days: int = 1
    # 2026-06-10 kalıcılık testi kanıtıyla 150→100: yüzey reytingi phi'si bu eşiği
    # aşarsa genel (overall) reytinge düşülür — orta bant bloklanmaz, genel karneyle
    # oynar (çim akışı veri gecikmesinden bağımsız açık kalır).
    surface_phi_fallback: float = 100.0
    low_tier_slug_prefixes: List[str] = Field(
        default_factory=lambda: ["itf-", "challenger-", "futures-"]
    )
    low_tier_question_keywords: List[str] = Field(
        default_factory=lambda: [
            "ITF", "Futures", "Challenger",
            "M15", "M25", "W15", "W25",
        ]
    )
