"""Agent dependency injection factory — tüm katmanları inşa edip Agent döner.

main.py burayı çağırır. Test izolasyonu için agent.py DI container
(AgentDeps) üzerinden çalışır; factory sadece production wiring yapar.
"""
from __future__ import annotations

import logging

from src.config.settings import AppConfig, Mode
from src.domain.guards.manipulation import ManipulationCheck, check_market as manipulation_check
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.apis.odds_client import OddsAPIClient
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.archive_logger import ArchiveLogger
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.stock_snapshot import StockSnapshot
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.infrastructure.websocket.price_feed import PriceFeed
from src.infrastructure.apis.cricket_client import CricketAPIClient
from src.infrastructure.apis.espn_client import fetch_scoreboard
from src.infrastructure.apis.espn_injury_client import EspnInjuryClient
from src.infrastructure.apis.espn_leagues_client import fetch_soccer_leagues  # PLAN-012
from src.infrastructure.apis.espn_schedule_client import EspnScheduleClient
from src.infrastructure.persistence.soccer_league_cache import SoccerLeagueCache  # PLAN-012
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.edge_enricher import EdgeEnricher
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.scanner import MarketScanner
from src.orchestration.soccer_league_discovery import SoccerLeagueDiscovery  # PLAN-012
from src.orchestration.startup import RuntimeState
from src.orchestration.stock_queue import StockConfig, StockQueue
from src.strategy.entry.gate import EntryGate, GateConfig
from src.strategy.enrichment.odds_enricher import enrich_market

logger = logging.getLogger(__name__)


def build_agent(state: RuntimeState) -> Agent:
    """Tüm agent bağımlılıklarını inşa et."""
    cfg = state.config

    gamma = GammaClient()
    odds = OddsAPIClient(daily_cap=cfg.odds_api.daily_credit_cap)  # SPEC-015
    scanner = MarketScanner(cfg.scanner, gamma_client=gamma)
    cycle_manager = CycleManager(cfg.cycle)
    cooldown = CooldownTracker(
        trigger_threshold=cfg.risk.consecutive_loss_cooldown,
        cooldown_cycles=cfg.risk.cooldown_cycles,
    )
    # WS price feed — agent entry/exit'te subscribe/unsubscribe yapacak,
    # callback agent.__init__'te bağlanır. Test senaryosunda None verilebilir;
    # production'da her zaman inşa edilir.
    price_feed = PriceFeed()

    # Executor: LIVE ise CLOB client gerekli — main.py LIVE confirm'dan sonra wire'lar
    executor = _build_executor(cfg)

    trade_logger = TradeHistoryLogger("logs/trade_history.jsonl")
    equity_logger = EquityHistoryLogger("logs/equity_history.jsonl")
    skipped_logger = SkippedTradeLogger("logs/skipped_trades.jsonl")
    archive_logger = ArchiveLogger("logs/archive")  # SPEC-009
    stock_snapshot = StockSnapshot("logs/stock_queue.json")
    stock = StockQueue(
        config=StockConfig(
            enabled=cfg.stock.enabled,
            jit_batch_multiplier=cfg.stock.jit_batch_multiplier,
            ttl_hours=cfg.stock.ttl_hours,
            pre_match_cutoff_min=cfg.stock.pre_match_cutoff_min,
            max_stale_attempts=cfg.stock.max_stale_attempts,
        ),
        snapshot=stock_snapshot,
    )
    stock.load()  # restart sonrası restore
    bot_status_store = JsonStore("logs/bot_status.json")
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
        min_favorite_probability=cfg.entry.min_favorite_probability,  # SPEC-017
        max_entry_price=cfg.entry.max_entry_price,
        max_positions=cfg.risk.max_positions,
        max_exposure_pct=cfg.risk.max_exposure_pct,
        hard_cap_overflow_pct=cfg.risk.hard_cap_overflow_pct,
        min_entry_size_pct=cfg.risk.min_entry_size_pct,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_single_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
        probability_weighted=cfg.risk.probability_weighted,  # SPEC-016
        min_bookmakers=cfg.entry.min_bookmakers,              # PLAN-013
        min_sharps=cfg.entry.min_sharps,                      # PLAN-013
        active_sports=cfg.entry.active_sports,
        min_gap_threshold=cfg.entry.min_gap_threshold,
        gap_high_zone=cfg.entry.gap_high_zone,
        gap_extreme_zone=cfg.entry.gap_extreme_zone,
        min_polymarket_price=cfg.entry.min_polymarket_price,
        min_market_volume=cfg.entry.min_market_volume,
        max_match_start_hours=cfg.entry.max_match_start_hours,
        confidence_a_pct=cfg.entry.confidence_a_pct,
        confidence_b_pct=cfg.entry.confidence_b_pct,
        high_gap_multiplier=cfg.entry.high_gap_multiplier,
        extreme_gap_multiplier=cfg.entry.extreme_gap_multiplier,
        min_bet_usd=cfg.entry.min_bet_usd,
        # Spread/totals filters
        spread_min_price=cfg.entry.spread_min_price,
        spread_max_price=cfg.entry.spread_max_price,
        spread_large_threshold=cfg.entry.spread_large_threshold,
        spread_gap_bonus=cfg.entry.spread_gap_bonus,
        totals_min_price=cfg.entry.totals_min_price,
        totals_max_price=cfg.entry.totals_max_price,
        totals_min_target_total=cfg.entry.totals_min_target_total,
    )

    # Telegram command poller — /stop ile botu uzaktan durdurma
    command_poller: TelegramCommandPoller | None = None
    tg = cfg.telegram
    if tg.enabled and tg.bot_token and tg.chat_id:
        # on_stop callback agent oluşturulduktan sonra bağlanır (aşağıda)
        command_poller = TelegramCommandPoller(
            bot_token=tg.bot_token, chat_id=tg.chat_id, on_stop=lambda: None,
        )

    # CricAPI (SPEC-011) — conditional on config + env key
    cricket_client: CricketAPIClient | None = None
    if cfg.cricket.enabled:
        import os
        cricapi_key = os.getenv("CRICAPI_KEY", "")
        if cricapi_key:
            cricket_client = CricketAPIClient(
                api_key=cricapi_key,
                daily_limit=cfg.cricket.daily_limit,
                cache_ttl_sec=cfg.cricket.cache_ttl_sec,
                timeout_sec=cfg.cricket.timeout_sec,
            )
        else:
            logger.warning("CRICAPI_KEY env missing — cricket disabled")

    # Edge enricher: ESPN injury + schedule clients (NBA edge detection)
    _injury_client = EspnInjuryClient()
    _schedule_client = EspnScheduleClient()
    _edge_enricher = EdgeEnricher(
        injury_client=_injury_client,
        schedule_client=_schedule_client,
        injury_window_hours=cfg.entry.injury_window_hours,
    )

    # Gate: cricket_client + edge_enricher hazır olduktan sonra inşa edilir (SPEC-011)
    gate = EntryGate(
        config=gate_cfg,
        portfolio=state.portfolio,
        circuit_breaker=state.circuit_breaker,
        cooldown=cooldown,
        blacklist=state.blacklist,
        odds_enricher=_enricher,
        manipulation_checker=_manip,
        cricket_client=cricket_client,  # SPEC-011
        edge_enricher=_edge_enricher,
    )

    # Score enricher: ESPN primary + Odds API fallback (SPEC-005)
    score_enricher: ScoreEnricher | None = None
    if cfg.score.enabled:
        class _ESPNBridge:
            """Thin bridge: wraps module function for DI."""
            @staticmethod
            def fetch(sport: str, league: str, date: str | None = None) -> list:
                return fetch_scoreboard(sport, league, date)

        espn_bridge = _ESPNBridge()

        # PLAN-012: soccer runtime league discovery
        soccer_cache = SoccerLeagueCache(
            cache_path="logs/soccer_league_cache.json",
            ttl_hours=cfg.score.espn_leagues_cache_ttl_hours,
        )
        soccer_discovery = SoccerLeagueDiscovery(
            leagues_fetcher=fetch_soccer_leagues,
            espn_fetcher=espn_bridge.fetch,
            cache=soccer_cache,
            max_candidates=cfg.score.soccer_discovery_max_candidates,
        )

        score_enricher = ScoreEnricher(
            espn_client=espn_bridge,
            odds_client=odds,
            poll_normal_sec=cfg.score.poll_normal_sec,
            poll_critical_sec=cfg.score.poll_critical_sec,
            critical_price_threshold=cfg.score.critical_price_threshold,
            match_window_hours=cfg.score.match_window_hours,
            archive_logger=archive_logger,  # SPEC-009
            cricket_client=cricket_client,  # SPEC-011
            soccer_discovery=soccer_discovery,  # PLAN-012
        )

    deps = AgentDeps(
        state=state, scanner=scanner, cycle_manager=cycle_manager,
        executor=executor, odds_client=odds, trade_logger=trade_logger,
        gate=gate, cooldown=cooldown,
        equity_logger=equity_logger, skipped_logger=skipped_logger,
        stock=stock, bot_status_writer=bot_status_writer,
        archive_logger=archive_logger,
        price_feed=price_feed,
        score_enricher=score_enricher,
        command_poller=command_poller,
        cricket_client=cricket_client,  # SPEC-011
    )
    agent = Agent(deps)

    # Callback'i agent oluştuktan sonra bağla
    if command_poller is not None:
        command_poller._on_stop = agent.request_stop

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
