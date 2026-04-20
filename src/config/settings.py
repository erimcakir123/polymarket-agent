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


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 75    # SPEC-010 + SPEC-016: bet tavani (probability-weighted ile efektif ~$56)
    max_bet_pct: float = 0.05
    confidence_bet_pct: dict[str, float] = {"A": 0.05, "B": 0.04}
    max_positions: int = 20
    max_exposure_pct: float = 0.50
    hard_cap_overflow_pct: float = 0.02
    min_entry_size_pct: float = 0.015
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    probability_weighted: bool = True  # SPEC-016: stake = base × win_prob


class EntryConfig(BaseModel):
    """Directional entry (SPEC-017) — edge-free entry kararı.

    Bookmaker favorilik ana filtre. Market fiyatı alt tabanı YOK
    (undervalue girişler alınsın); sadece pahalı outlier cap (max_entry_price).
    """
    model_config = ConfigDict(extra="ignore")
    min_favorite_probability: float = 0.60  # güçlü favori eşiği (bookmaker)
    max_entry_price: float = 0.80           # aşırı pahalı girişi engelle (R/R outlier cap)


class StockConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    jit_batch_multiplier: int = 3
    ttl_hours: float = 24.0
    pre_match_cutoff_min: float = 30.0
    max_stale_attempts: int = 3


class ScaleOutTier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    threshold: float
    sell_pct: float


class ScaleOutConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    tiers: List[ScaleOutTier] = [
        ScaleOutTier(threshold=0.15, sell_pct=0.40),
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


class DashboardConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 5050


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class CricketConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    daily_limit: int = 100          # SPEC-011 free tier; TODO-003 paid 1000
    cache_ttl_sec: int = 240        # 4dk bulk cache
    timeout_sec: int = 15           # HTTP timeout


class OddsApiConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    daily_credit_cap: int = 800  # 0 = unlimited (SPEC-015)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: Mode = Mode.DRY_RUN
    initial_bankroll: float = 1000.0
    cycle: CycleConfig = CycleConfig()
    scanner: ScannerConfig = ScannerConfig()
    risk: RiskConfig = RiskConfig()
    entry: EntryConfig = EntryConfig()
    stock: StockConfig = StockConfig()
    scale_out: ScaleOutConfig = ScaleOutConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    manipulation: ManipulationConfig = ManipulationConfig()
    liquidity: LiquidityConfig = LiquidityConfig()
    near_resolve: NearResolveConfig = NearResolveConfig()
    a_conf_hold: AConfHoldConfig = AConfHoldConfig()
    favored: FavoredConfig = FavoredConfig()
    score: ScoreConfig = ScoreConfig()
    dashboard: DashboardConfig = DashboardConfig()
    telegram: TelegramConfig = TelegramConfig()
    cricket: CricketConfig = CricketConfig()  # SPEC-011
    odds_api: OddsApiConfig = OddsApiConfig()  # SPEC-015


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
