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
    # 2026-05-29 (Phase 3 follow-up): tennis-paper-lab parity. Eğer set edilirse
    # scanner sadece bu market_type'ları kabul eder; None/empty → legacy
    # (moneyline/spreads/totals). Tennis için: tennis_first_set_winner,
    # tennis_set_handicap, tennis_set_totals, moneyline, tennis_match_totals.
    allowed_sports_market_types: List[str] = []
    # Tennis match_start ESPN override icin cache TTL (saniye).
    # TennisStartEnricher cycle basina bir kere ESPN tennis/atp+wta scoreboard ceker.
    tennis_start_cache_ttl_sec: int = 300
    tennis_athlete_cache_ttl_sec: int = 86400  # 24 saat — ESPN tennis athlete adi cache


class EdgeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_edge: float = 0.06
    confidence_multipliers: dict = {"A": 1.00, "B": 1.00}  # 19 Apr peak (A: 1.25 → 1.00)
    # Data-driven entry exclusions (Phase 3, 2026-05-29). Tennis paper lab
    # analizinden negative-EV kanıtlı sub-market'ler. Genişletilebilir
    # (yeni evidence olduğunda).
    exclude_combos: list[dict] = Field(default_factory=list)


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # SPEC-P (2026-05-21): fixed-tier sizing — bankroll dalgalanmasından bağımsız.
    # SPEC-U (2026-05-23): bimodal-aware. Non-bimodal (moneyline) eski sizing;
    # bimodal (totals + spreads) tenis paritesi cap.
    fixed_bet_usdc: dict[str, float] = {"A": 50.0, "B": 30.0}    # non-bimodal
    bimodal_bet_usdc: dict[str, float] = {"A": 15.0, "B": 10.0}  # bimodal (totals + spreads)
    max_positions: int = 20
    max_positions_per_event: int = 3  # SPEC-J/K: aynı event'te moneyline+spread+totals bağımsız bahisler (Kural 8 gevşedi)
    # Soft cap: exposure < cap iken tam trade alınır (sonuç cap'i geçse de OK).
    # Hard blok: exposure ≥ cap → yeni trade reddedilir. Clipping uygulanmaz.
    max_exposure_pct: float = 0.50
    # 2026-05-31: 0.88 → 0.80. R/R sıkılaştırma (89¢ Rublev trade öğreticisi).
    max_entry_price: float = 0.80
    entry_price_slippage_buffer: float = 0.01
    # SPEC-X (2026-05-24): bimodal market'ler için entry alt sınır.
    bimodal_min_entry_price: float = 0.20
    consecutive_loss_cooldown: int = 3
    cooldown_cycles: int = 2
    stop_loss_pct: float = 0.30
    # Adım 5 (2026-05-31): Tennis Kelly sizing — kalibre model için dinamik stake.
    kelly_enabled_tennis: bool = True
    kelly_multiplier: float = 0.25
    kelly_max_pct: float = 0.05
    # Tennis H2H pricer: Glicko prob + Markov serve prob blend ağırlığı.
    # 0.6 = Glicko'ya daha çok güven (PLOS One 2022 referansı).
    tennis_h2h_glicko_weight: float = 0.6
    # 2026-05-27 (SPEC-force-close): market_type → max dakika; süre dolarsa pozisyon
    # zorla kapatılır. Boş dict → feature devre dışı (mevcut SL/TP zincirine etki yok).
    force_close_timeouts: dict[str, int] = Field(default_factory=dict)
    # 2026-05-28: Polymarket auto-resolution detector. ExitProcessor light cycle her N
    # tick'te bir pozisyonun underlying market'ini gamma'da sorgular (closed=true +
    # umaResolutionStatus=resolved → exit @ owned-side payout). 5sn light interval × 60
    # = 5dk per pozisyon. 0 → devre disi.
    polymarket_resolution_check_every_n_ticks: int = 60


class MlbSubmarketConfig(BaseModel):
    """MLB submarket (totals/run-line) model-anchor config (SPEC-R)."""
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    min_edge: float = Field(0.05, gt=0.0)
    statsapi_timeout_sec: float = Field(10.0, gt=0.0)
    rate_cache_path: str = "data/mlb_rate_cache.jsonl"


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


class PaperConfig(BaseModel):
    """Paper mode realism parameters (real Polymarket behavior, no synthetic).

    FOK + GTC limit order parity with live mode, 1¢ tick, $1 min order,
    maker/taker fee + Polygon gas modeling.
    """
    model_config = ConfigDict(extra="ignore")
    max_buy_slippage_pct: float = 0.02
    max_sell_slippage_pct: float = 0.05
    min_fill_ratio: float = 0.95
    book_cache_ttl_sec: int = 5
    max_open_cycles: int = 6
    max_stuck_cycles: int = 12
    min_order_usdc: float = 1.0
    price_tick: float = 0.01
    maker_fee_pct: float = 0.0
    taker_fee_pct: float = 0.0
    polygon_gas_usdc: float = 0.01
    # 2026-05-31: Entry-time bid-depth guard. Polymarket alt market (totals,
    # spreads, tennis set_handicap) bid book çoğunlukla çok ince — pozisyon
    # açılır ama çıkış yapılamaz. Bot %82 SELL reject gördü. Eğer top-3 bid
    # toplam USDC değeri bu eşiğin altında ise giriş REJECTED.
    min_bid_depth_usdc: float = 50.0


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
    exit_basketball: BasketballExitConfig = Field(default_factory=BasketballExitConfig)
    mlb_submarket: MlbSubmarketConfig = Field(default_factory=MlbSubmarketConfig)
    paper: PaperConfig = Field(default_factory=PaperConfig)


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
