"""Agent dependency injection factory — tüm katmanları inşa edip Agent döner.

main.py burayı çağırır. Test izolasyonu için agent.py DI container
(AgentDeps) üzerinden çalışır; factory sadece production wiring yapar.
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import AppConfig, Mode
from src.domain.guards.manipulation import ManipulationCheck, check_market as manipulation_check
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.espn_client import ESPNClient
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.apis.odds_client import OddsAPIClient
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.stock_snapshot import StockSnapshot
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.infrastructure.telegram.notifier import TelegramNotifier
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration.health_monitor import HealthMonitor
from src.orchestration._factory_loggers import (
    build_equity_logger, build_trade_event_log,
)
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.scanner import MarketScanner
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.startup import RuntimeState
from src.orchestration.stock_queue import StockConfig, StockQueue
from src.orchestration.tennis_start_enricher import TennisStartEnricher
from src.infrastructure.data.calibration_store import load_calibration as load_tennis_calibration
from src.infrastructure.data.tennis_ratings_store import load_ratings as load_tennis_ratings
from src.infrastructure.data.tennis_surface_map_store import load_surface_map
from src.strategy.entry.gate import EntryGate, GateConfig
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol
from src.strategy.enrichment.odds_enricher import enrich_market
from src.strategy.enrichment.tennis_dispatch import enrich_with_tennis_dispatch

logger = logging.getLogger(__name__)

# Ballpark metadata + team_id mapping ayrı modülde (ARCH_GUARD §3).
from src.orchestration.factory_ballpark_data import (  # noqa: F401
    TEAM_ID_TO_PARK_ID,
    _DEFAULT_BALLPARK_METADATA,
    park_meta_for_team,
)


def build_agent(state: RuntimeState) -> Agent:
    """Tüm agent bağımlılıklarını inşa et."""
    cfg = state.config

    # Phase 3: tennis aktif iken Sackmann cache refresh hook (build_deps öncesi
    # blocking, ratings.json'ı agent'ın taze yüklemesi için). Stale değilse skip.
    _maybe_invoke_sackmann_refresh(cfg)

    # SPEC-Z21 (2026-06-06): basketbol modeli kaldırıldı — refresh/ratings-build
    # hook'ları silindi. Basketbol artık bahisçi konsensüsü (model verisi gerekmez).

    # Plan 1.D Task 6: haftalık calibration eğrisi update (FiveThirtyEight paterni).
    _maybe_invoke_calibration_refresh()

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
        lookahead_days=cfg.scanner.tennis_espn_lookahead_days,
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
    price_feed = PriceFeed(
        max_spike_pct=cfg.price_feed.max_spike_pct,
        max_spike_corroboration_spread=cfg.price_feed.max_spike_corroboration_spread,
    )

    # Executor: LIVE ise CLOB client gerekli — main.py LIVE confirm'dan sonra wire'lar
    executor = _build_executor(cfg)

    # 3-tier log paths: audit (kalıcı) + session (reboot mirror) + runtime (reboot temizler).
    # State (positions/breaker/blacklist) startup.py'de data/'da; operasyonel state burada data/'da.
    # SPEC-Z17 (2026-06-04): tek truth = trade_event_log (append-only).
    # Legacy trade_history.jsonl writer kaldırıldı (Task 12).
    trade_event_log = build_trade_event_log()
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

    # Tennis ratings cache — startup'ta yüklenir, runtime'da statik kullanılır.
    # Build script tarafından üretilir (scripts/build_tennis_ratings.py).
    # Yok ise dispatch boş dict ile çağrılır → moneyline bookmaker'a düşer.
    tennis_ratings = load_tennis_ratings(Path("data/tennis_ratings.json"))
    # 2026-06-02: Surface-specific Glicko (Hard/Clay/Grass) — eğer mevcutsa
    # tennis dispatch yüzey bilinen rating dict'i kullanır (PLOS One 2022).
    _surface_ratings_path = Path("data/tennis_ratings_surface.json")
    tennis_surface_ratings = None
    if _surface_ratings_path.exists():
        from src.infrastructure.data.tennis_surface_ratings_store import load_all_surfaces
        # 2026-06-10: phi_fallback config'den (kalıcılık testi kanıtıyla 150→100).
        tennis_surface_ratings = load_all_surfaces(
            _surface_ratings_path, cfg.tennis.surface_phi_fallback,
        )
        logger.info(
            "Tennis SURFACE-specific Glicko aktif: Hard=%d Clay=%d Grass=%d oyuncu",
            len(tennis_surface_ratings.get("Hard", {})),
            len(tennis_surface_ratings.get("Clay", {})),
            len(tennis_surface_ratings.get("Grass", {})),
        )
    tennis_calibration = load_tennis_calibration(Path("data/tennis_calibration.json"))
    tennis_surface_map = load_surface_map(Path("data/tennis_surface_map.json"))
    # PLAN-Z30 g5: zemin çözücü (Sackmann harita → override TTL → Wikipedia → event-link).
    from src.infrastructure.apis.wikipedia_surface_client import WikipediaSurfaceClient
    from src.infrastructure.data.tennis_surface_override_store import load_overrides, save_overrides
    from src.strategy.enrichment.surface_resolver import SurfaceResolver
    _ovr_path = Path("data/tennis_surface_overrides.json")
    tennis_surface_resolver = SurfaceResolver(
        tennis_surface_map,
        wiki=WikipediaSurfaceClient(),
        overrides=load_overrides(_ovr_path),
        save_fn=lambda ov: save_overrides(ov, _ovr_path),
        reload_fn=lambda: load_overrides(_ovr_path),
        ttl_days=cfg.tennis.surface_unknown_recheck_days,
        found_recheck_days=cfg.tennis.surface_found_recheck_days,  # görünce-tazele (6 ay)
    )
    tennis_active = bool({"atp", "wta"} & {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])})

    # SPEC-Z21 (2026-06-06): basketbol ratings/efficiencies/rest-days/calibration
    # yüklemesi kaldırıldı — model yok, basketbol bahisçiyle fiyatlanır.
    if tennis_ratings:
        logger.info(
            "Tennis model anchor aktif: %d oyuncu reytingi, calibration curves=%d",
            len(tennis_ratings), len(tennis_calibration),
        )
    elif tennis_active:
        logger.warning(
            "Tennis allowed_sport_tags'te AMA tennis_ratings.json yok — "
            "alt market'ler tamamen skip, h2h bookmaker fallback. "
            "Çözüm: python -m scripts.build_tennis_ratings",
        )
    else:
        logger.info("Tennis ratings yok ve tennis pasif — sorun yok")

    def _bookmaker_enrich(market):
        return enrich_market(market, odds)

    _tennis_low_tier_slug_prefixes = tuple(cfg.tennis.low_tier_slug_prefixes)
    _tennis_low_tier_question_keywords = tuple(cfg.tennis.low_tier_question_keywords)

    # 2026-06-02: Surface-aware tennis dispatch (yüzey-spesifik Glicko).
    # Mevcutsa surface dict kullanılır, yoksa flat ratings (geriye uyumlu).
    if tennis_surface_ratings is not None:
        from src.strategy.enrichment.tennis_dispatch_surface import (
            make_surface_aware_dispatch,
        )
        _surface_aware = make_surface_aware_dispatch(tennis_surface_ratings)

        def _tennis_dispatched(market):
            return _surface_aware(
                market, _bookmaker_enrich, tennis_ratings,
                calibration_curves=tennis_calibration,
                glicko_weight=cfg.risk.tennis_h2h_glicko_weight,
                max_phi_for_trade=cfg.tennis.max_phi_for_trade,
                low_tier_slug_prefixes=_tennis_low_tier_slug_prefixes,
                low_tier_question_keywords=_tennis_low_tier_question_keywords,
                surface_resolver=tennis_surface_resolver,
            )
    else:
        def _tennis_dispatched(market):
            return enrich_with_tennis_dispatch(
                market, _bookmaker_enrich, tennis_ratings, tennis_calibration,
                glicko_weight=cfg.risk.tennis_h2h_glicko_weight,
                max_phi_for_trade=cfg.tennis.max_phi_for_trade,
                low_tier_slug_prefixes=_tennis_low_tier_slug_prefixes,
                low_tier_question_keywords=_tennis_low_tier_question_keywords,
                surface_resolver=tennis_surface_resolver,
            )

    # Gate: enricher + manipulation_check closure'ları.
    # SPEC-Z21 (2026-06-06): basketbol modeli kaldırıldı. tennis kendi dispatch'i
    # (model); diğer TÜM sporlar (basketbol dahil) tennis_dispatch'in non-tennis
    # fallback'i ile bahisçiye düşer (enrich_market: ML + totals, kazanan dönem hali).
    def _enricher(market):
        return _tennis_dispatched(market)

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
        entry_price_slippage_buffer=cfg.risk.entry_price_slippage_buffer,
        model_min_anchor_distance_from_half=cfg.risk.model_min_anchor_distance_from_half,
        bimodal_min_entry_price=cfg.risk.bimodal_min_entry_price,
        # Consensus
        consensus_enabled=cfg.consensus.enabled,
        consensus_min_price=cfg.consensus.min_price,
        consensus_min_model_edge=cfg.consensus.min_model_edge,
        consensus_favorite_band_min_prob=cfg.consensus.favorite_band_min_prob,
        consensus_favorite_band_max_prob=cfg.consensus.favorite_band_max_prob,
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

    # Telegram: notifier (entry/exit/alert gönderici) + command poller (/stop alıcı)
    tg = cfg.telegram
    notifier = TelegramNotifier(
        enabled=tg.enabled, bot_token=tg.bot_token, chat_id=tg.chat_id,
    )
    command_poller: TelegramCommandPoller | None = None
    if tg.enabled and tg.bot_token and tg.chat_id:
        command_poller = TelegramCommandPoller(
            bot_token=tg.bot_token, chat_id=tg.chat_id, on_stop=lambda: None,
        )
        # Boot mesajı: kullanıcı bağlantıyı doğrulasın (notifier.send rate-limit aware)
        notifier.send(
            f"🤖 <b>Bot başladı</b>\n"
            f"Mode: {cfg.mode.value}\n"
            f"Bankroll: ${cfg.initial_bankroll:.0f}"
        )
    # SPEC-TG-001 Task 4: HealthMonitor — periyodik scraper/exposure/stale check
    health_monitor = HealthMonitor(
        notifier=notifier,
        state_dir=Path("data"),
        audit_dir=Path("logs/audit"),
        runtime_dir=Path("logs/runtime"),
        stale_price_threshold=tg.alert.stale_price_rate_threshold,
        exposure_lockup_minutes=tg.alert.exposure_lockup_minutes,
        consecutive_losses=tg.alert.consecutive_losses,
        dedupe_window_minutes=tg.alert.dedupe_window_minutes,
        calibration_stale_days=tg.alert.calibration_stale_days,
        scraper_stale_hours=tg.alert.scraper_stale_hours,
        muted_alert_categories=tg.alert.muted_alert_categories,
        odds_client=odds,
        odds_low_credit_threshold=tg.alert.odds_low_credit_threshold,
        surface_resolver=tennis_surface_resolver,  # PLAN-Z30 g6: SURFACE_UNKNOWN alert
    )
    # SPEC-Z9 (2026-06-03): Polymarket roster drift detector — günde 1 /teams + /sports diff
    from src.orchestration.roster_drift_monitor import RosterDriftMonitor
    roster_drift_monitor = RosterDriftMonitor(gamma_client=gamma)

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
        executor=executor, odds_client=odds,
        trade_event_log=trade_event_log,
        gate=gate, cooldown=cooldown,
        equity_logger=equity_logger, skipped_logger=skipped_logger,
        stock=stock, bot_status_writer=bot_status_writer,
        price_feed=price_feed,
        command_poller=command_poller,
        score_enricher=score_enricher,
        mlb_submarket_engine=mlb_engine,
        tennis_start_enricher=tennis_enricher,
        espn_client=espn,  # SPEC-force-close 2026-05-27
        gamma_client=gamma,  # 2026-05-28: ExitProcessor polymarket-resolution detector
        notifier=notifier,  # SPEC-TG-001 2026-06-02: entry/exit/critical alert
        health_monitor=health_monitor,  # SPEC-TG-001 Task 4: periyodik health check
        roster_drift_monitor=roster_drift_monitor,  # SPEC-Z9 2026-06-03: 12h drift check
        tennis_surface_resolver=tennis_surface_resolver,  # PLAN-Z30 g5: cycle event→turnuva map
    )
    agent = Agent(deps)

    # Callback'i agent oluştuktan sonra bağla
    if command_poller is not None:
        command_poller.set_on_stop(agent.request_stop)

    return agent


# Sackmann + calibration refresh hooks ayrı modülde (ARCH_GUARD §3).
from src.orchestration.factory_refresh_hooks import (  # noqa: E402,F401
    _maybe_invoke_calibration_refresh,
    _maybe_invoke_sackmann_refresh,
    maybe_refresh_sackmann_on_startup,
)

# SPEC-Z21 (2026-06-06): factory_basketball re-export'ları kaldırıldı (model yok).


def _build_executor(cfg: AppConfig) -> Executor:
    """Mode dispatch: dry_run → stub; paper → realistic fill; live → CLOB."""
    if cfg.mode == Mode.DRY_RUN:
        return Executor(mode=cfg.mode)
    if cfg.mode == Mode.PAPER:
        return Executor(
            mode=cfg.mode,
            paper_config=cfg.paper,
            paper_audit_path="logs/audit/paper_executions.jsonl",
        )
    # LIVE: py-clob-client runtime wiring
    import os
    from src.infrastructure.apis.clob_client import ClobOrderClient, build_client
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("LIVE mode requires PRIVATE_KEY env var")
    raw = build_client(host="https://clob.polymarket.com", chain_id=137, private_key=private_key)
    clob = ClobOrderClient(raw)
    return Executor(mode=cfg.mode, clob_client=clob)
