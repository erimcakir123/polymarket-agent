"""Basketball EXIT config classes (model config kaldırıldı).

SPEC-Z21 (2026-06-06): BasketballConfig + BasketballLeagueParams (in-house model
tuning) silindi — basketbol artık bahisçi konsensüsü ile fiyatlanır, model yok.
Burada SADECE in-game EXIT yönetimi config'i kalır (model-bağımsız: live skor
ile maç-içi çıkış). settings.py re-export eder (geri uyumlu import path).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
