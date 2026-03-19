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
    min_volume_24h: float = 50_000
    min_liquidity: float = 5_000
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
        "low": 1.5, "medium": 1.0, "high": 0.75
    }


class RiskConfig(BaseModel):
    kelly_fraction: float = 0.25
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
    max_positions: int = 5
    correlation_cap_pct: float = 0.30
    stop_loss_pct: float = 0.30
    take_profit_pct: float = 0.40
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    drawdown_halt_pct: float = 0.50

    @field_validator("kelly_fraction")
    @classmethod
    def kelly_in_range(cls, v: float) -> float:
        if not 0 < v <= 1.0:
            raise ValueError("kelly_fraction must be in (0, 1]")
        return v



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
