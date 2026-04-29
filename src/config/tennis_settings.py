"""Tennis-specific Pydantic config models.

Extracted from `src/config/settings.py` to keep that file under the
400-line architectural cap. Only `TennisConfig` is imported by
`AppConfig`; the sub-models are encapsulated here and surfaced via
the `TennisConfig` aggregate.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TennisSurfaceFactors(BaseModel):
    model_config = ConfigDict(extra="ignore")
    serve_pct_atp: dict[str, float] = Field(default_factory=lambda: {"grass": 1.0, "hard": 1.0, "clay": 0.92})
    serve_pct_wta: dict[str, float] = Field(default_factory=lambda: {"grass": 1.0, "hard": 1.05, "clay": 0.95})


class TennisFilters(BaseModel):
    model_config = ConfigDict(extra="ignore")
    paper_trade_relaxed: bool = True
    min_ranking: int = 100
    max_ranking_gap: int = 100
    min_edge: float = 0.05
    match_window_hours_min: float = 0.0
    match_window_hours_max: float = 24.0


class TennisExit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    near_resolve_bid: float = 0.95
    profit_lock_bid: float = 0.80
    risk_penalty_cap: float = 0.70
    w_momentum: float = 0.35
    w_value: float = 0.40
    bayesian_max_shift: float = 0.15
    momentum_decay: float = 0.85
    momentum_window_games: int = 7


class TennisData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sackmann_cache_dir: str = "data/sackmann_cache/"
    sackmann_refresh_days: int = 7
    player_xref_path: str = "data/tennis_player_xref.json"


class TennisConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    phase: str = "disabled"
    position_size_usdc: dict[str, int] = Field(default_factory=lambda: {"paper_trade": 0, "v1": 15, "v2": 25, "v3": 35})
    filters: TennisFilters = Field(default_factory=TennisFilters)
    exit: TennisExit = Field(default_factory=TennisExit)
    data: TennisData = Field(default_factory=TennisData)
    surface_factors: TennisSurfaceFactors = Field(default_factory=TennisSurfaceFactors)
    tournaments: dict[str, dict[str, str]] = Field(default_factory=dict)
    excluded_tiers: list[str] = Field(default_factory=lambda: ["itf", "challenger", "futures"])
