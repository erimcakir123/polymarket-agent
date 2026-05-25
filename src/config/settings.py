"""Pydantic config loader (DECISIONS §9)."""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, ConfigDict, Field


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
    # SPEC-M: Adaptive cycle — maca yaklasildikca cycle siklasir.
    # Sebep: edge'ler maca yakin (lineup, goalie, sharp money) cikar.
    # nearest_match_hours bilgisi agent.py'dan tick() ile gelir; verilmezse mevcut
    # heavy/night davranisi (geriye uyumlu).
    near_interval_min: int = 15           # 1-3h: lineup baslangic
    imminent_interval_min: int = 10       # <1h: goalie + sharp + son haber
    near_threshold_hours: float = 3.0
    imminent_threshold_hours: float = 1.0


class ScannerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_liquidity: float = 1000
    max_markets_per_cycle: int = 300
    max_duration_days: int = 14
    # Odds API h2h penceresi — maç > bu kadar saat sonraysa bookmaker verisi
    # olmayacak, scanner'da ele.
    max_hours_to_start: float = 24.0
    # Maç başladıktan sonra max kabul süresi (canlı entry penceresi).
    # Bu kadar saatten daha eski match_start'lar (sezon-uzunluğu futures) elenir.
    max_post_start_hours: float = 8.0
    # Fiyat-based "resolved" detection: yes_price >= bu veya <= 1 - bu ise
    # market sonucu belli (Polymarket flag lag'ini atlatır).
    resolved_price_threshold: float = 0.98
    allowed_categories: List[str] = ["sports"]
    allowed_sport_tags: List[str] = []
    # Sandbox extension (Task 12 / Spec §11.3): opt-in strict allow-list for
    # sports_market_type. When set, ONLY listed types pass. When absent (None),
    # scanner falls back to legacy moneyline/spreads/totals behaviour so the
    # main bot is completely unaffected.
    allowed_sports_market_types: List[str] | None = None


class EdgeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_edge: float = 0.06
    confidence_multipliers: dict = {"A": 1.00, "B": 1.00}  # 19 Apr peak (A: 1.25 → 1.00)


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 75
    # Per-market overrides: bimodal piyasalar (set_totals + set_handicap) SL fire etmiyor →
    # full loss riski. Tennis-lab override eder. (2026-05-22 PLAN-SIZING-001)
    set_totals_max_usdc: float = 75
    set_handicap_max_usdc: float = 75
    max_bet_pct: float = 0.05  # 19 Apr peak (disabled 1.0 → 0.05)
    confidence_bet_pct: dict[str, float] = {"A": 0.05, "B": 0.04}  # 19 Apr peak sizing
    max_positions: int = 20
    max_positions_per_event: int = 2  # SPEC-J/K: aynı event'te moneyline+spread+totals bağımsız bahisler (Kural 8 gevşedi)
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
    """Scale-out tier: at threshold (distance-to-resolution), sell sell_pct of remaining.

    threshold: fraction of distance from entry to $1.00. Formula:
        progress = (current - entry) / (1.0 - entry)
        tier fires when progress >= threshold.
    Replaces profit-percentage semantic which locked too small $ on cheap entries
    and never fired on expensive entries.
    """
    model_config = ConfigDict(extra="ignore")
    threshold: float
    sell_pct: float


class ScaleOutConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    tiers: List[ScaleOutTier] = [
        ScaleOutTier(threshold=0.40, sell_pct=0.40),
        ScaleOutTier(threshold=0.70, sell_pct=0.50),
    ]


class CircuitBreakerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True  # Faz 2 gözlem için False'a alınabilir; multi-SL zaten maç-içi koruma
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


class FavoredConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    promote_eff_price: float = 0.65
    demote_eff_price: float = 0.65
    conf_required: List[str] = ["A", "B"]


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


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Programatik hata (TypeError, AttributeError vb.) 2 ardışık aynı tip sonrası
    # bot otomatik durur — sessiz çalışmayı engeller (SPEC-A1).
    cycle_max_consecutive_errors: int = 2


class ScoreConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    poll_normal_sec: int = 60
    poll_critical_sec: int = 30
    critical_price_threshold: float = 0.35


class PriceFeedConfig(BaseModel):
    """SPEC-M (2026-05-19) — WS price feed sanity layer.

    Bilgisayar uyku → REST 404 → cache stale → bot sahte fiyat ($0.97) ile
    near_resolve tetikledi. Bu config dört yapısal koruma sağlar:
    - max_spike_pct: tek tick'te %50+ atlama → reject
    - max_spread_for_near_resolve: ask-bid > 10¢ → near_resolve reddeder (sahte likidite)
    """
    model_config = ConfigDict(extra="ignore")
    max_spike_pct: float = 0.50
    max_spread_for_near_resolve: float = 0.10


class TennisConfidenceTier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_matches_12mo: int = 40
    min_surface_matches: int = 15
    min_h2h_years: int | None = None  # Optional — only Tier A enforces H2H (DECISIONS §6)
    max_form_age_days: int = 60
    max_glicko_rd: float = 100.0


class TennisConfig(BaseModel):
    """Tennis prediction lab config (sandbox-only).

    Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md
    """
    model_config = ConfigDict(extra="ignore")
    data_dir: str = "data/sackmann_cache"
    tml_dir: str = "data/tml_cache"
    ratings_cache: str = "data/tennis_ratings.json"
    diagnostic_log_dir: str = "logs/tennis_diagnostics"
    sackmann_years: list[int] = [2022, 2023, 2024, 2025, 2026]
    challenger_years: list[int] = [2022, 2023, 2024, 2025, 2026]
    # Empty default = WTA disabled; rebuild script skips women's tour unless set in yaml.
    sackmann_wta_years: list[int] = []
    glicko_initial_rating: float = 1500.0
    glicko_initial_rd: float = 350.0
    glicko_initial_volatility: float = 0.06
    glicko_tau: float = 0.5
    confidence_tier_a: TennisConfidenceTier = Field(
        default_factory=lambda: TennisConfidenceTier(
            min_matches_12mo=40, min_surface_matches=15, min_h2h_years=5,
            max_form_age_days=60, max_glicko_rd=100.0,
        ),
    )
    confidence_tier_b: TennisConfidenceTier = Field(
        default_factory=lambda: TennisConfidenceTier(
            min_matches_12mo=20, min_surface_matches=8,
            max_form_age_days=90, max_glicko_rd=150.0,
        ),
    )


# ── Basketbol exit config (SPEC-J — DECISIONS §6/§7 kalibrasyonları) ────────────────


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
    favored: FavoredConfig = FavoredConfig()
    dashboard: DashboardConfig = DashboardConfig()
    telegram: TelegramConfig = TelegramConfig()
    agent: AgentConfig = AgentConfig()
    score: ScoreConfig = ScoreConfig()
    price_feed: PriceFeedConfig = PriceFeedConfig()
    tennis: TennisConfig = Field(default_factory=TennisConfig)
    exit_basketball: BasketballExitConfig = Field(default_factory=BasketballExitConfig)


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
