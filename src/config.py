"""Pydantic config loader from YAML."""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, field_validator


class Mode(str, Enum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


class CycleConfig(BaseModel):
    default_interval_min: int = 30
    breaking_news_interval_min: int = 10
    near_stop_loss_interval_min: int = 15
    night_interval_min: int = 60
    night_hours: List[int] = [0, 1, 2, 3, 4, 5, 6]


class ScannerConfig(BaseModel):
    min_volume_24h: float = 1_000   # Low threshold — volume spikes near match time, early entry is the strategy
    min_liquidity: float = 1_000
    tags: List[str] = []
    prefer_short_duration: bool = True
    max_markets_per_cycle: int = 20
    max_duration_days: int = 14  # Skip markets resolving more than N days out
    allowed_categories: List[str] = []  # Empty = allow all; e.g. ["sports", "esports"]


class AIConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    cache_ttl_min: int = 15
    cache_invalidate_price_move_pct: float = 0.05
    batch_size: int = 5
    monthly_budget_usd: float = 48.0
    sprint_budget_usd: float = 24.0  # Per 2-week sprint (2 sprints/month)
    input_cost_per_mtok: float = 3.0
    output_cost_per_mtok: float = 15.0


class EdgeConfig(BaseModel):
    min_edge: float = 0.06
    confidence_multipliers: Dict[str, float] = {
        "C": 1.5, "B-": 1.0, "B+": 0.85, "A": 0.75
    }
    fill_ratio_scaling: bool = False
    fill_ratio_aggressive: float = 0.3
    fill_ratio_selective: float = 0.7
    bookmaker_confidence_boost: bool = False
    default_spread: float = 0.02
    min_edge_swap: float = 0.085


class TrailingStopTier(BaseModel):
    min_peak: float
    drop_pct: float


class RiskConfig(BaseModel):
    kelly_fraction: float = 0.20  # 20% Kelly (user-confirmed)
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
    max_positions: int = 5
    correlation_cap_pct: float = 0.30
    stop_loss_pct: float = 0.30
    take_profit_pct: float = 0.40
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    drawdown_halt_pct: float = 0.50
    esports_stop_loss_pct: float = 0.50
    trailing_stop_tiers: List[TrailingStopTier] = []

    # Re-entry (#6, #12)
    max_daily_reentries: int = 5

    # Correlation (#17)
    max_match_exposure_pct: float = 0.15

    # Scale-In (#7)
    scale_in_min_pnl_pct: float = 0.02
    scale_in_min_cycles: int = 3
    scale_in_num_tranches: int = 2
    price_drift_reanalysis_pct: float = 0.15

    @field_validator("kelly_fraction")
    @classmethod
    def kelly_in_range(cls, v: float) -> float:
        if not 0 < v <= 1.0:
            raise ValueError("kelly_fraction must be in (0, 1]")
        return v


class VolatilitySwingConfig(BaseModel):
    enabled: bool = True
    stop_loss_pct: float = 0.20
    take_profit_pct: float = 0.60
    tp_floor: float = 0.30
    tp_ceiling: float = 1.00
    reserved_slots: int = 5
    max_concurrent: int = 5
    max_token_price: float = 0.50
    min_token_price: float = 0.10
    max_hours_to_start: float = 24.0
    bet_pct: float = 0.05
    polling_interval_min: int = 5


class FarConfig(BaseModel):
    enabled: bool = True
    max_slots: int = 2
    min_edge: float = 0.10
    min_ai_probability: float = 0.55
    min_confidence: str = "B-"
    bookmaker_pre_screen_edge: float = 0.08
    min_hours_to_start: float = 6.0       # Only markets >6h out qualify as FAR
    max_hours_to_start: float = 336.0     # 14 days max
    bet_pct: float = 0.05                 # 5% bankroll per FAR bet
    stop_loss_pct: float = 0.30
    take_profit_pct: float = 0.40         # Swing trade TP (overridden for penny)
    # Penny Alpha thresholds ($0.01-$0.02 tokens)
    penny_max_price: float = 0.02         # Tokens at $0.01-$0.02
    penny_1c_target_multiplier: float = 5.0  # $0.01 → wait for 5x ($0.05)
    penny_2c_target_multiplier: float = 2.0  # $0.02 → wait for 2x ($0.04)
    penny_bet_pct: float = 0.05           # 5% bankroll for penny bets


class BondFarmingConfig(BaseModel):
    enabled: bool = True
    min_yes_price: float = 0.90
    max_yes_price: float = 0.97
    bet_pct: float = 0.08              # 8% bankroll per bond
    max_total_bond_pct: float = 0.20   # 20% max across all bonds
    max_concurrent: int = 3
    min_volume_24h: float = 5_000
    min_liquidity: float = 5_000
    max_days_to_resolution: float = 0.25  # ~6 hours — only near-resolution bonds


class LiveMomentumConfig(BaseModel):
    enabled: bool = True
    min_edge: float = 0.06
    bet_pct: float = 0.04              # 4% bankroll per momentum trade
    max_hold_minutes: int = 30
    max_concurrent: int = 2


class TrailingTPConfig(BaseModel):
    enabled: bool = True
    activation_pct: float = 0.20       # Activate at +20% profit
    trail_distance: float = 0.08       # Sell when 8% below peak


class PennyAlphaConfig(BaseModel):
    enabled: bool = True
    max_price: float = 0.02
    bet_pct: float = 0.05
    max_concurrent: int = 3
    min_volume: float = 500
    target_1c: float = 5.0             # $0.01 → 5x target
    target_2c: float = 2.0             # $0.02 → 2x target


class ProbabilityEngineConfig(BaseModel):
    book_weight: float = 0.55
    ai_weight: float = 0.45
    shrinkage_factor: float = 0.10
    high_divergence_threshold: float = 0.15


class NotificationConfig(BaseModel):
    telegram_enabled: bool = False


class DashboardConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5050


class LoggingConfig(BaseModel):
    trades_file: str = "logs/trades.jsonl"
    portfolio_file: str = "logs/portfolio.jsonl"
    performance_file: str = "logs/performance.jsonl"


class AppConfig(BaseModel):
    mode: Mode = Mode.DRY_RUN
    initial_bankroll: float = 60.0
    cycle: CycleConfig = CycleConfig()
    scanner: ScannerConfig = ScannerConfig()
    ai: AIConfig = AIConfig()
    edge: EdgeConfig = EdgeConfig()
    risk: RiskConfig = RiskConfig()
    volatility_swing: VolatilitySwingConfig = VolatilitySwingConfig()
    far: FarConfig = FarConfig()
    bond_farming: BondFarmingConfig = BondFarmingConfig()
    live_momentum: LiveMomentumConfig = LiveMomentumConfig()
    trailing_tp: TrailingTPConfig = TrailingTPConfig()
    penny_alpha: PennyAlphaConfig = PennyAlphaConfig()
    probability_engine: ProbabilityEngineConfig = ProbabilityEngineConfig()
    notifications: NotificationConfig = NotificationConfig()
    dashboard: DashboardConfig = DashboardConfig()
    logging: LoggingConfig = LoggingConfig()


def load_config(path: Path = Path("config.yaml")) -> AppConfig:
    """Load config from YAML file, fall back to defaults if missing."""
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()
