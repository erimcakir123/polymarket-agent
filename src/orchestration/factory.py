"""Agent dependency injection factory — tüm katmanları inşa edip Agent döner.

main.py burayı çağırır. Test izolasyonu için agent.py DI container
(AgentDeps) üzerinden çalışır; factory sadece production wiring yapar.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config.settings import AppConfig, Mode
from src.domain.guards.manipulation import ManipulationCheck, check_market as manipulation_check
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.espn_client import ESPNClient
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.apis.odds_client import OddsAPIClient
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.stock_snapshot import StockSnapshot
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration._factory_loggers import build_equity_logger, build_trade_logger
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.scanner import MarketScanner
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.startup import RuntimeState
from src.orchestration.stock_queue import StockConfig, StockQueue
from src.orchestration.tennis_start_enricher import TennisStartEnricher
from src.strategy.entry.gate import EntryGate, GateConfig
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol
from src.strategy.enrichment.odds_enricher import enrich_market

logger = logging.getLogger(__name__)

# All 30 active MLB ballparks (2024-2026 season).
# lat/lon rounded to 4 decimals; cf_orientation_deg = direction CF points (0=N, 90=E, 180=S, 270=W).
_DEFAULT_BALLPARK_METADATA: dict[str, dict[str, Any]] = {
    "COORS":            {"park_id": "COORS",            "lat": 39.7559, "lon": -104.9942, "cf_orientation_deg": 0.0},
    "FENWAY":           {"park_id": "FENWAY",           "lat": 42.3467, "lon": -71.0972,  "cf_orientation_deg": 75.0},
    "YANKEE":           {"park_id": "YANKEE",           "lat": 40.8296, "lon": -73.9262,  "cf_orientation_deg": 60.0},
    "DODGER":           {"park_id": "DODGER",           "lat": 34.0739, "lon": -118.2400, "cf_orientation_deg": 0.0},
    "PETCO":            {"park_id": "PETCO",            "lat": 32.7073, "lon": -117.1566, "cf_orientation_deg": 0.0},
    "WRIGLEY":          {"park_id": "WRIGLEY",          "lat": 41.9484, "lon": -87.6553,  "cf_orientation_deg": 70.0},
    "BUSCH":            {"park_id": "BUSCH",            "lat": 38.6226, "lon": -90.1928,  "cf_orientation_deg": 30.0},
    "GLOBE_LIFE":       {"park_id": "GLOBE_LIFE",       "lat": 32.7473, "lon": -97.0817,  "cf_orientation_deg": 0.0},
    "GREAT_AMERICAN":   {"park_id": "GREAT_AMERICAN",   "lat": 39.0975, "lon": -84.5067,  "cf_orientation_deg": 320.0},
    "CITIZENS_BANK":    {"park_id": "CITIZENS_BANK",    "lat": 39.9061, "lon": -75.1665,  "cf_orientation_deg": 30.0},
    "AMERICAN_FAMILY":  {"park_id": "AMERICAN_FAMILY",  "lat": 43.0280, "lon": -87.9712,  "cf_orientation_deg": 0.0},
    "TARGET":           {"park_id": "TARGET",           "lat": 44.9817, "lon": -93.2776,  "cf_orientation_deg": 0.0},
    "KAUFFMAN":         {"park_id": "KAUFFMAN",         "lat": 39.0517, "lon": -94.4803,  "cf_orientation_deg": 90.0},
    "PROGRESSIVE":      {"park_id": "PROGRESSIVE",      "lat": 41.4962, "lon": -81.6852,  "cf_orientation_deg": 90.0},
    "GUARANTEED_RATE":  {"park_id": "GUARANTEED_RATE",  "lat": 41.8300, "lon": -87.6338,  "cf_orientation_deg": 0.0},
    "ROGERS":           {"park_id": "ROGERS",           "lat": 43.6414, "lon": -79.3894,  "cf_orientation_deg": 0.0},
    "ORACLE":           {"park_id": "ORACLE",           "lat": 37.7786, "lon": -122.3893, "cf_orientation_deg": 0.0},
    "CHASE":            {"park_id": "CHASE",            "lat": 33.4453, "lon": -112.0667, "cf_orientation_deg": 0.0},
    "T_MOBILE":         {"park_id": "T_MOBILE",         "lat": 47.5914, "lon": -122.3325, "cf_orientation_deg": 0.0},
    "ANGEL":            {"park_id": "ANGEL",            "lat": 33.8003, "lon": -117.8827, "cf_orientation_deg": 0.0},
    "MINUTE_MAID":      {"park_id": "MINUTE_MAID",      "lat": 29.7572, "lon": -95.3556,  "cf_orientation_deg": 0.0},
    "TROPICANA":        {"park_id": "TROPICANA",        "lat": 27.7682, "lon": -82.6534,  "cf_orientation_deg": 0.0},
    "LOAN_DEPOT":       {"park_id": "LOAN_DEPOT",       "lat": 25.7781, "lon": -80.2197,  "cf_orientation_deg": 0.0},
    "TRUIST":           {"park_id": "TRUIST",           "lat": 33.8908, "lon": -84.4678,  "cf_orientation_deg": 0.0},
    "ORIOLE_PARK":      {"park_id": "ORIOLE_PARK",      "lat": 39.2839, "lon": -76.6217,  "cf_orientation_deg": 70.0},
    "NATIONALS":        {"park_id": "NATIONALS",        "lat": 38.8730, "lon": -77.0074,  "cf_orientation_deg": 30.0},
    "CITI":             {"park_id": "CITI",             "lat": 40.7571, "lon": -73.8458,  "cf_orientation_deg": 60.0},
    "PNC":              {"park_id": "PNC",              "lat": 40.4469, "lon": -80.0058,  "cf_orientation_deg": 290.0},
    "COMERICA":         {"park_id": "COMERICA",         "lat": 42.3390, "lon": -83.0485,  "cf_orientation_deg": 30.0},
    "OAKLAND_COLISEUM": {"park_id": "OAKLAND_COLISEUM", "lat": 37.7516, "lon": -122.2005, "cf_orientation_deg": 0.0},
}

# Stats API team_id → ballpark_id (_DEFAULT_BALLPARK_METADATA anahtarı).
# 2026 sezonu (Athletics geçici Sacramento 2025-2027, OAKLAND_COLISEUM key korunur).
TEAM_ID_TO_PARK_ID: dict[int, str] = {
    # AL East
    110: "ORIOLE_PARK",     # Orioles
    111: "FENWAY",          # Red Sox
    147: "YANKEE",          # Yankees
    139: "TROPICANA",       # Rays
    141: "ROGERS",          # Blue Jays
    # AL Central
    145: "GUARANTEED_RATE", # White Sox
    114: "PROGRESSIVE",     # Guardians
    116: "COMERICA",        # Tigers
    118: "KAUFFMAN",        # Royals
    142: "TARGET",          # Twins
    # AL West
    117: "MINUTE_MAID",     # Astros
    108: "ANGEL",           # Angels
    133: "OAKLAND_COLISEUM",# Athletics (geçici Sacramento 2025-27)
    136: "T_MOBILE",        # Mariners
    140: "GLOBE_LIFE",      # Rangers
    # NL East
    144: "TRUIST",          # Braves
    146: "LOAN_DEPOT",      # Marlins
    121: "CITI",            # Mets
    143: "CITIZENS_BANK",   # Phillies
    120: "NATIONALS",       # Nationals
    # NL Central
    112: "WRIGLEY",         # Cubs
    113: "GREAT_AMERICAN",  # Reds
    158: "AMERICAN_FAMILY", # Brewers
    134: "PNC",             # Pirates
    138: "BUSCH",           # Cardinals
    # NL West
    109: "CHASE",           # D-backs
    115: "COORS",           # Rockies
    119: "DODGER",          # Dodgers
    135: "PETCO",           # Padres
    137: "ORACLE",          # Giants
}


def park_meta_for_team(team_id: int) -> dict | None:
    """Stats API team_id → ballpark metadata. Bilinmeyen → None."""
    park_id = TEAM_ID_TO_PARK_ID.get(team_id)
    if park_id is None:
        return None
    return _DEFAULT_BALLPARK_METADATA.get(park_id)


def build_agent(state: RuntimeState) -> Agent:
    """Tüm agent bağımlılıklarını inşa et."""
    cfg = state.config

    gamma = GammaClient()
    odds = OddsAPIClient()
    espn = ESPNClient(athlete_cache_ttl_sec=cfg.scanner.tennis_athlete_cache_ttl_sec)
    score_enricher = ScoreEnricher(
        espn_client=espn,
        odds_client=odds,
        config=cfg.score,
    )
    tennis_enricher = TennisStartEnricher(
        espn_client=espn,
        cache_ttl_sec=cfg.scanner.tennis_start_cache_ttl_sec,
    )
    scanner = MarketScanner(
        cfg.scanner,
        gamma_client=gamma,
        tennis_start_enricher=tennis_enricher,
    )
    cycle_manager = CycleManager(cfg.cycle)
    cooldown = CooldownTracker(
        trigger_threshold=cfg.risk.consecutive_loss_cooldown,
        cooldown_cycles=cfg.risk.cooldown_cycles,
    )
    # WS price feed — agent entry/exit'te subscribe/unsubscribe yapacak,
    # callback agent.__init__'te bağlanır. Test senaryosunda None verilebilir;
    # production'da her zaman inşa edilir. SPEC-M: spike rejection threshold config'den.
    price_feed = PriceFeed(max_spike_pct=cfg.price_feed.max_spike_pct)

    # Executor: LIVE ise CLOB client gerekli — main.py LIVE confirm'dan sonra wire'lar
    executor = _build_executor(cfg)

    # 3-tier log paths: audit (kalıcı) + session (reboot mirror) + runtime (reboot temizler).
    # State (positions/breaker/blacklist) startup.py'de data/'da; operasyonel state burada data/'da.
    trade_logger = build_trade_logger()
    equity_logger = build_equity_logger()
    skipped_logger = SkippedTradeLogger("logs/runtime/skipped_trades.jsonl")
    stock_snapshot = StockSnapshot("data/stock_queue.json")
    stock = StockQueue(
        config=StockConfig(
            enabled=cfg.stock.enabled,
            jit_batch_multiplier=cfg.stock.jit_batch_multiplier,
            ttl_hours=cfg.stock.ttl_hours,
            pre_match_cutoff_min=cfg.stock.pre_match_cutoff_min,
            max_no_edge_attempts=cfg.stock.max_no_edge_attempts,
        ),
        snapshot=stock_snapshot,
    )
    stock.load()  # restart sonrası restore
    bot_status_store = JsonStore("data/bot_status.json")
    bot_status_writer = BotStatusWriter(bot_status_store, cycle_manager)

    # Gate: enricher + manipulation_check closure'ları
    def _enricher(market):
        return enrich_market(market, odds)

    def _manip(question: str, liquidity: float) -> ManipulationCheck:
        return manipulation_check(
            question=question, liquidity=liquidity,
            min_liquidity_usd=cfg.manipulation.min_liquidity_usd,
        )

    gate_cfg = GateConfig(
        min_edge=cfg.edge.min_edge,
        max_positions=cfg.risk.max_positions,
        max_positions_per_event=cfg.risk.max_positions_per_event,
        max_exposure_pct=cfg.risk.max_exposure_pct,
        fixed_bet_usdc=cfg.risk.fixed_bet_usdc,
        bimodal_bet_usdc=cfg.risk.bimodal_bet_usdc,
        max_entry_price=cfg.risk.max_entry_price,
        bimodal_min_entry_price=cfg.risk.bimodal_min_entry_price,
        # Consensus
        consensus_enabled=cfg.consensus.enabled,
        consensus_min_price=cfg.consensus.min_price,
        # Early entry
        early_enabled=cfg.early.enabled,
        early_min_edge=cfg.early.min_edge,
        early_min_anchor_probability=cfg.early.min_anchor_probability,
        early_min_confidence=cfg.early.min_confidence,
        early_max_entry_price=cfg.early.max_entry_price,
        early_min_hours_to_start=cfg.early.min_hours_to_start,
        early_max_hours_to_start=cfg.early.max_hours_to_start,
    )
    gate = EntryGate(
        config=gate_cfg,
        portfolio=state.portfolio,
        circuit_breaker=state.circuit_breaker,
        cooldown=cooldown,
        blacklist=state.blacklist,
        odds_enricher=_enricher,
        manipulation_checker=_manip,
    )

    # Telegram command poller — /stop ile botu uzaktan durdurma
    command_poller: TelegramCommandPoller | None = None
    tg = cfg.telegram
    if tg.enabled and tg.bot_token and tg.chat_id:
        # on_stop callback agent oluşturulduktan sonra bağlanır (aşağıda)
        command_poller = TelegramCommandPoller(
            bot_token=tg.bot_token, chat_id=tg.chat_id, on_stop=lambda: None,
        )

    mlb_engine: MlbSubmarketEngineProtocol | None = None
    if cfg.mlb_submarket.enabled:
        from src.infrastructure.mlb_data.rate_cache import RateCache
        from src.infrastructure.mlb_data.statcast_client import StatcastClient
        from src.infrastructure.mlb_data.statsapi_client import StatsApiClient
        from src.infrastructure.mlb_data.weather_client import WeatherClient
        from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine

        statsapi = StatsApiClient(timeout=cfg.mlb_submarket.statsapi_timeout_sec)
        statcast = StatcastClient(cache_dir=Path("data/mlb_statcast_cache"))
        weather = WeatherClient()
        rate_cache = RateCache(Path(cfg.mlb_submarket.rate_cache_path))

        fixed_bet = getattr(cfg.risk, "fixed_bet_usdc", {"A": 50.0, "B": 30.0})
        bimodal_bet = getattr(cfg.risk, "bimodal_bet_usdc", {"A": 15.0, "B": 10.0})

        mlb_engine = MlbSubmarketEngine(
            statsapi=statsapi,
            statcast=statcast,
            weather=weather,
            rate_cache=rate_cache,
            config=cfg.mlb_submarket,
            ballpark_metadata=_DEFAULT_BALLPARK_METADATA,
            team_id_to_park_id=TEAM_ID_TO_PARK_ID,
            fixed_bet_usdc=fixed_bet,
            bimodal_bet_usdc=bimodal_bet,
        )
        logger.info("MlbSubmarketEngine initialized (config.mlb_submarket.enabled=True)")

    deps = AgentDeps(
        state=state, scanner=scanner, cycle_manager=cycle_manager,
        executor=executor, odds_client=odds, trade_logger=trade_logger,
        gate=gate, cooldown=cooldown,
        equity_logger=equity_logger, skipped_logger=skipped_logger,
        stock=stock, bot_status_writer=bot_status_writer,
        price_feed=price_feed,
        command_poller=command_poller,
        score_enricher=score_enricher,
        mlb_submarket_engine=mlb_engine,
        tennis_start_enricher=tennis_enricher,
        espn_client=espn,  # SPEC-force-close 2026-05-27
    )
    agent = Agent(deps)

    # Callback'i agent oluştuktan sonra bağla
    if command_poller is not None:
        command_poller.set_on_stop(agent.request_stop)

    return agent


def _build_executor(cfg: AppConfig) -> Executor:
    """LIVE mode → CLOB client wire; dry_run/paper → stub."""
    if cfg.mode != Mode.LIVE:
        return Executor(mode=cfg.mode)
    # LIVE: py-clob-client runtime wiring
    import os
    from src.infrastructure.apis.clob_client import ClobOrderClient, build_client
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("LIVE mode requires PRIVATE_KEY env var")
    raw = build_client(host="https://clob.polymarket.com", chain_id=137, private_key=private_key)
    clob = ClobOrderClient(raw)
    return Executor(mode=cfg.mode, clob_client=clob)
