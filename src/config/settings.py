"""Pydantic config loader (TDD §9)."""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, ConfigDict


class Mode(str, Enum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


class CycleConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    heavy_interval_min: int = 30
    light_interval_sec: int = 5
    night_interval_min: int = 60
    night_hours: List[int] = [8, 9, 10, 11, 12, 13]


class ScannerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_liquidity: float = 1000
    max_markets_per_cycle: int = 300
    max_duration_days: int = 14
    # Odds API h2h penceresi — maç > bu kadar saat sonraysa bookmaker verisi
    # olmayacak, scanner'da ele.
    max_hours_to_start: float = 24.0
    # Fiyat-based "resolved" detection: yes_price >= bu veya <= 1 - bu ise
    # market sonucu belli (Polymarket flag lag'ini atlatır).
    resolved_price_threshold: float = 0.98
    allowed_categories: List[str] = ["sports"]
    allowed_sport_tags: List[str] = []


class EdgeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_edge: float = 0.06
    confidence_multipliers: dict = {"A": 1.25, "B": 1.00}


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
    max_positions: int = 20
    max_exposure_pct: float = 0.50
    hard_cap_overflow_pct: float = 0.02
    min_entry_size_pct: float = 0.015
    max_entry_price: float = 0.88
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    stop_loss_pct: float = 0.30


class EarlyEntryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    max_slots: int = 2
    max_entry_price: float = 0.70
    min_edge: float = 0.10
    min_anchor_probability: float = 0.55
    min_confidence: str = "B"
    bookmaker_pre_screen_edge: float = 0.08
    min_hours_to_start: float = 6.0
    max_hours_to_start: float = 24.0
    bet_pct: float = 0.05
    stop_loss_pct: float = 0.30


class ConsensusConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    min_price: float = 0.60
    bet_pct: float = 0.05
    max_slots: int = 5


class StockConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    jit_batch_multiplier: int = 3
    ttl_hours: float = 24.0
    pre_match_cutoff_min: float = 30.0
    max_no_edge_attempts: int = 3


class ScaleOutTier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    threshold: float
    sell_pct: float


class ScaleOutConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    tiers: List[ScaleOutTier] = [
        ScaleOutTier(threshold=0.25, sell_pct=0.40),
        ScaleOutTier(threshold=0.50, sell_pct=0.50),
    ]


class CircuitBreakerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    daily_max_loss_pct: float = -0.08
    hourly_max_loss_pct: float = -0.05
    consecutive_loss_limit: int = 4
    cooldown_after_daily_min: int = 120
    cooldown_after_hourly_min: int = 60
    cooldown_after_consecutive_min: int = 60
    entry_block_threshold: float = -0.03
    # Dashboard Loss Protection renk bölgeleri (drawdown %)
    safe_drawdown_pct: float = 15.0
    warn_drawdown_pct: float = 30.0


class ManipulationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_liquidity_usd: float = 10_000


class LiquidityConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entry_min_depth_usdc: float = 100
    entry_halve_threshold: float = 0.20
    exit_min_fill_ratio: float = 0.80


class NearResolveConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    threshold_cents: int = 94
    pre_match_guard_minutes: int = 5


class AConfHoldConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_entry_price: float = 0.60
    market_flip_threshold: float = 0.50
    market_flip_elapsed_gate: float = 0.85


class FavoredConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    promote_eff_price: float = 0.65
    demote_eff_price: float = 0.65
    conf_required: List[str] = ["A", "B"]


class ScoreConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    poll_normal_sec: int = 60
    poll_critical_sec: int = 30
    critical_price_threshold: float = 0.35
    match_window_hours: float = 4.0


class ExitExtrasConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    catastrophic_trigger: float = 0.25
    catastrophic_drop_pct: float = 0.10
    catastrophic_cancel: float = 0.50


class DashboardConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 5050
    big_win_roi_pct: float = 30.0


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: Mode = Mode.DRY_RUN
    initial_bankroll: float = 1000.0
    cycle: CycleConfig = CycleConfig()
    scanner: ScannerConfig = ScannerConfig()
    edge: EdgeConfig = EdgeConfig()
    risk: RiskConfig = RiskConfig()
    early: EarlyEntryConfig = EarlyEntryConfig()
    consensus: ConsensusConfig = ConsensusConfig()
    stock: StockConfig = StockConfig()
    scale_out: ScaleOutConfig = ScaleOutConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    manipulation: ManipulationConfig = ManipulationConfig()
    liquidity: LiquidityConfig = LiquidityConfig()
    near_resolve: NearResolveConfig = NearResolveConfig()
    a_conf_hold: AConfHoldConfig = AConfHoldConfig()
    favored: FavoredConfig = FavoredConfig()
    score: ScoreConfig = ScoreConfig()
    exit: ExitExtrasConfig = ExitExtrasConfig()
    dashboard: DashboardConfig = DashboardConfig()
    telegram: TelegramConfig = TelegramConfig()


def load_config(path: Path = Path("config.yaml")) -> AppConfig:
    """YAML'dan config yükle; dosya yoksa default'larla döner.

    Telegram secret'ları .env'den okunur (config.yaml'a yazılmaz).
    """
    if not path.exists():
        return AppConfig()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Telegram: .env'den secret override (token/chat_id yaml'a yazılmaz)
    tg = data.setdefault("telegram", {})
    if not tg.get("bot_token"):
        tg["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not tg.get("chat_id"):
        tg["chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")
    if tg["bot_token"] and tg["chat_id"]:
        tg["enabled"] = True

    return AppConfig(**data)
