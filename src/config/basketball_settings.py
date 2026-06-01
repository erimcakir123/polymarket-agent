"""Basketball-specific pydantic config classes.

Bölünme nedeni: ARCH_GUARD §3 (settings.py 400 satır limitini aştı). Sport-specific
config'ler kendi modülünde — settings.py re-export eder (geri uyumlu import path).
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class BasketballLeagueParams(BaseModel):
    """Lig-spesifik model parametreleri (Plan 1.B Task 7 + Faz 2/3).

    home_advantage: rating puanı.
      NBA 100, WNBA 95, NCAAB 130, WNCAAB 120, EUL 90.
    k_factor: Elo update hızı.
    blend_elo: moneyline blend ağırlığı (Elo vs Pace×Efficiency).
    margin_std: maç sonu skor farkı std (NBA 11, NCAAB 13, EUL 10).
    total_std: toplam skor std (NBA 20, NCAAB 22, EUL 16).
    """
    model_config = ConfigDict(extra="ignore")
    home_advantage: float = 100.0
    k_factor: float = 20.0
    blend_elo: float = Field(0.55, ge=0.0, le=1.0)
    margin_std: float = Field(11.0, gt=0.0)
    total_std: float = Field(20.0, gt=0.0)


class BasketballConfig(BaseModel):
    """Basketball model foundation — veri + model katmanı config (SPEC 2026-06-01 Faz 1).

    enabled_leagues: hangi ligler için refresh hook tetiklensin (NBA + WNBA Faz 1).
    primary/secondary: çift-kaynak fallback için.
    leagues: lig-başına model tuning (Plan 1.B Task 7).
    """
    model_config = ConfigDict(extra="ignore")
    enabled_leagues: List[str] = Field(default_factory=lambda: ["nba"])
    cache_dir: str = "data/basketball_cache"
    health_file: str = "data/basketball_cache/_health/sources_status.json"
    primary_source: str = "nba_api"
    secondary_source: str = "espn"
    leagues: dict[str, BasketballLeagueParams] = Field(
        default_factory=lambda: {
            "nba": BasketballLeagueParams(
                home_advantage=100.0, k_factor=20.0,
                margin_std=11.0, total_std=20.0,
            ),
            "wnba": BasketballLeagueParams(
                home_advantage=95.0, k_factor=22.0,
                margin_std=9.5, total_std=16.0,
            ),
            "ncaab": BasketballLeagueParams(
                home_advantage=130.0, k_factor=25.0, blend_elo=0.60,
                margin_std=13.0, total_std=22.0,
            ),
            "wncaab": BasketballLeagueParams(
                home_advantage=120.0, k_factor=25.0, blend_elo=0.60,
                margin_std=12.0, total_std=20.0,
            ),
            "euroleague": BasketballLeagueParams(
                home_advantage=90.0, k_factor=20.0, blend_elo=0.50,
                margin_std=10.0, total_std=16.0,
            ),
            "g_league": BasketballLeagueParams(
                home_advantage=80.0, k_factor=22.0, blend_elo=0.50,
                margin_std=13.0, total_std=22.0,
            ),
            "summer_league": BasketballLeagueParams(
                home_advantage=70.0, k_factor=30.0, blend_elo=0.45,
                margin_std=14.0, total_std=22.0,
            ),
            "eurocup": BasketballLeagueParams(
                home_advantage=85.0, k_factor=22.0, blend_elo=0.50,
                margin_std=10.0, total_std=16.0,
            ),
        }
    )


class OvertimeExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    seconds: int = 60
    deficit: int = 8


class TotalsEmpiricalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ot_over_scale_pct: float = 0.5
    q4_late_seconds: int = 360
    q4_late_gap: float = 7
    q4_final_seconds: int = 180
    q4_final_gap: float = 4
    q4_endgame_seconds: int = 60
    q4_endgame_gap: float = 3


class PredictiveExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    safety_margin: float = 0.03
    hold_threshold: float = 0.20


class BasketballExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    structural_damage_ratio: float = 0.30
    totals_multiplier: float = 1.218
    overtime: OvertimeExitConfig = Field(default_factory=OvertimeExitConfig)
    totals_empirical: TotalsEmpiricalConfig = Field(default_factory=TotalsEmpiricalConfig)
    predictive_exit: PredictiveExitConfig = Field(default_factory=PredictiveExitConfig)
