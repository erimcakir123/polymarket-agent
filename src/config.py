"""Pydantic config loader from YAML."""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import List

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
    min_liquidity: float = 100  # Floor: ensures orderbook has some orders
    tags: List[str] = []
    prefer_short_duration: bool = True
    max_markets_per_cycle: int = 300
    max_duration_days: int = 14  # Skip markets resolving more than N days out
    allowed_categories: List[str] = []  # Empty = allow all; e.g. ["sports", "esports"]


class AIConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    cache_ttl_min: int = 15
    cache_invalidate_price_move_pct: float = 0.05
    batch_size: int = 20
    monthly_budget_usd: float = 48.0
    sprint_budget_usd: float = 24.0
    input_cost_per_mtok: float = 3.0
    output_cost_per_mtok: float = 15.0


class EdgeConfig(BaseModel):
    min_edge: float = 0.06


class RiskConfig(BaseModel):
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
    max_positions: int = 20
    correlation_cap_pct: float = 0.30
    stop_loss_pct: float = 0.30
    near_stop_loss_multiplier: float = 0.83  # Shorten cycle when PnL nears SL
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    price_drift_reanalysis_pct: float = 0.15

    # Exposure guard (#P0) -- block entries when total invested > X% of bankroll
    # 50% cap supports ~15 positions at 3-5% sizing each, keeps 50% cash buffer
    max_exposure_pct: float = 0.50


class VolatilitySwingConfig(BaseModel):
    enabled: bool = True
    reserved_slots: int = 0  # Single pool — all entry modes share max_positions
    max_concurrent: int = 5
    max_token_price: float = 0.50
    min_token_price: float = 0.10
    max_hours_to_start: float = 24.0
    bet_pct: float = 0.05
    stop_loss_pct: float = 0.20
    polling_interval_min: int = 5


class EarlyEntryConfig(BaseModel):
    enabled: bool = True
    max_slots: int = 2
    max_entry_price: float = 0.70
    min_edge: float = 0.10
    min_ai_probability: float = 0.55
    min_confidence: str = "B-"
    bookmaker_pre_screen_edge: float = 0.08
    min_hours_to_start: float = 6.0       # Only markets >6h out qualify as early entry
    max_hours_to_start: float = 336.0     # 14 days max
    bet_pct: float = 0.05                 # 5% bankroll per early entry bet
    stop_loss_pct: float = 0.30


class UpsetHunterConfig(BaseModel):
    enabled: bool = True
    min_price: float = 0.05
    max_price: float = 0.15
    bet_pct: float = 0.02
    max_concurrent: int = 3
    stop_loss_pct: float = 0.50
    min_liquidity: float = 5_000
    min_odds_divergence: float = 0.05
    max_hours_before_match: float = 48
    late_match_exit_pct: float = 0.10
    max_hold_hours: float = 3.0


class LiveMomentumConfig(BaseModel):
    enabled: bool = True
    min_edge: float = 0.06
    bet_pct: float = 0.04              # 4% bankroll per momentum trade
    max_hold_minutes: int = 30
    max_concurrent: int = 2


class ConsensusEntryConfig(BaseModel):
    enabled: bool = True
    min_price: float = 0.65            # AI and market both ≥65% same direction
    bet_pct: float = 0.05              # Fixed 5% bankroll (no Kelly -- edge≈0)
    max_slots: int = 5                 # Max concurrent consensus positions


class TrailingTPConfig(BaseModel):
    enabled: bool = False  # Disabled: scale-out handles profit-taking, TP was cutting winners short
    activation_pct: float = 0.20       # Activate at +20% profit
    trail_distance: float = 0.15       # Sell when 15% below peak


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
    initial_bankroll: float = 1000.0
    cycle: CycleConfig = CycleConfig()
    scanner: ScannerConfig = ScannerConfig()
    ai: AIConfig = AIConfig()
    edge: EdgeConfig = EdgeConfig()
    risk: RiskConfig = RiskConfig()
    volatility_swing: VolatilitySwingConfig = VolatilitySwingConfig()
    early: EarlyEntryConfig = EarlyEntryConfig()
    upset_hunter: UpsetHunterConfig = UpsetHunterConfig()
    live_momentum: LiveMomentumConfig = LiveMomentumConfig()
    consensus_entry: ConsensusEntryConfig = ConsensusEntryConfig()
    trailing_tp: TrailingTPConfig = TrailingTPConfig()
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
