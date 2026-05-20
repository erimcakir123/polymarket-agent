"""Tennis lab sandbox composition root.

Builds tennis-specific dependencies (config, ratings, predictor) + paper-mode
entry/exit infrastructure (state, executor, loggers, entry_processor,
exit_processor) wired with the main bot's modules.

Stage 4 PLAN-TENNIS-001: tennis_agent artık `entry_processor.process_signals`
çağırarak gerçek pozisyon açıyor (paper mode).
Stage 5 PLAN-TENNIS-001: light cycle `exit_processor.run_light` ile tennis
pozisyonları SL/TP/graduated/near-resolve guard'larından geçiyor.
EntryGate yalnızca config/breaker/cooldown/blacklist/manip taşıyıcısı;
`gate.run()` ÇAĞRILMIYOR (bookmaker enricher tennis için anlamsız).

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §11.2 (shared modules)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import AppConfig, load_config
from src.domain.guards.manipulation import ManipulationCheck, check_market as manipulation_check
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.data.sackmann_csv_client import SackmannCsvClient
from src.infrastructure.data.tennis_ratings_store import TennisRatingsStore
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.json_store import JsonStore
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.entry_processor import EntryProcessor
from src.orchestration.exit_processor import ExitProcessor
from src.orchestration.startup import RuntimeState, bootstrap
from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger
from src.strategy.entry.gate import EntryGate, GateConfig

logger = logging.getLogger(__name__)


@dataclass
class TennisDeps:
    """Tennis sandbox dependencies — composition root output.

    `entry_processor` paper-mode pozisyon açar (sport-agnostic guard'lar +
    in-memory portfolio + trade_history.jsonl). `state.portfolio` heavy
    cycle sonunda `persist(state)` ile positions.json'a yazılır.
    `exit_processor` light cycle'da tüm açık pozisyonları SL/TP/graduated/
    near-resolve guard'larından geçirir; tetiklenen exit'ler executor.exit_position
    (paper sim) + trade_logger.update_on_exit ile defterleniyor.
    """

    config: AppConfig
    ratings_store: TennisRatingsStore
    sackmann_client: SackmannCsvClient
    diagnostic_logger: TennisDiagnosticLogger
    state: RuntimeState
    entry_processor: EntryProcessor
    exit_processor: ExitProcessor


def build_tennis_deps(
    config_path: Path,
    *,
    data_dir: Path | str = "data",
    logs_dir: Path | str = "logs",
) -> TennisDeps:
    """Build all tennis sandbox dependencies from config file.

    Args:
        config_path: Path to YAML config (e.g. config_tennis.yaml).
        data_dir: State dosyaları için kök dizin (positions.json,
            stock_queue.json, bot_status.json). Test'te tmp_path verilir.
        logs_dir: Skipped/trade/equity JSONL'leri için kök dizin.

    Returns:
        TennisDeps — entry_processor dahil tamamı paper mode için hazır.
    """
    cfg = load_config(config_path)

    data_path = Path(data_dir)
    logs_path = Path(logs_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    logs_path.mkdir(parents=True, exist_ok=True)

    # Tennis-specific deps
    sackmann_client = SackmannCsvClient(cache_dir=Path(cfg.tennis.data_dir))
    ratings_store = TennisRatingsStore(path=Path(cfg.tennis.ratings_cache))
    diagnostic_logger = TennisDiagnosticLogger(
        log_dir=Path(cfg.tennis.diagnostic_log_dir),
    )

    # Runtime state (portfolio + circuit_breaker + blacklist + persistent stores)
    state = bootstrap(
        cfg,
        logs_dir=data_path,
        trade_history_path=logs_path / "trade_history.jsonl",
    )

    # Entry + exit infrastructure (shared deps container — built once, used both)
    entry_processor, exit_processor = _build_entry_exit_processors(
        cfg, state, data_path, logs_path,
    )

    logger.info(
        "Tennis deps built: mode=%s bankroll=$%.2f dashboard=:%d",
        cfg.mode.value,
        cfg.initial_bankroll,
        cfg.dashboard.port,
    )
    return TennisDeps(
        config=cfg,
        ratings_store=ratings_store,
        sackmann_client=sackmann_client,
        diagnostic_logger=diagnostic_logger,
        state=state,
        entry_processor=entry_processor,
        exit_processor=exit_processor,
    )


def _build_entry_exit_processors(
    cfg: AppConfig,
    state: RuntimeState,
    data_dir: Path,
    logs_dir: Path,
) -> tuple[EntryProcessor, ExitProcessor]:
    """Paper-mode entry + exit pipeline'larını ortak deps üzerinde kur.

    EntryProcessor + ExitProcessor aynı `_TennisAgentDeps` instance'ını
    paylaşır — state/executor/trade_logger/equity_logger/cooldown/cycle_manager
    tek yerde build edilir, iki processor da aynı portfolyoyu görür.

    Tennis akışı `entry_processor.process_signals` + `exit_processor.run_light`
    çağırır; `run_heavy`/`process_markets` için gereken scanner/stock/odds_client/
    score_enricher/price_feed verilmez (Stage 5 scope).
    """
    executor = Executor(mode=cfg.mode)

    trade_logger = TradeHistoryLogger(str(logs_dir / "trade_history.jsonl"))
    equity_logger = EquityHistoryLogger(str(logs_dir / "equity_history.jsonl"))
    skipped_logger = SkippedTradeLogger(str(logs_dir / "skipped_trades.jsonl"))

    cooldown = CooldownTracker(
        trigger_threshold=cfg.risk.consecutive_loss_cooldown,
        cooldown_cycles=cfg.risk.cooldown_cycles,
    )

    cycle_manager = CycleManager(cfg.cycle)
    bot_status_store = JsonStore(data_dir / "bot_status.json")
    bot_status_writer = BotStatusWriter(bot_status_store, cycle_manager)

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
        hard_cap_overflow_pct=cfg.risk.hard_cap_overflow_pct,
        min_entry_size_pct=cfg.risk.min_entry_size_pct,
        max_single_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_entry_price=cfg.risk.max_entry_price,
    )
    # EntryGate yalnızca config/breaker/cooldown/blacklist/_manip_check
    # taşıyıcısı olarak kullanılır; `gate.run()` tennis akışında çağrılmaz.
    gate = EntryGate(
        config=gate_cfg,
        portfolio=state.portfolio,
        circuit_breaker=state.circuit_breaker,
        cooldown=cooldown,
        blacklist=state.blacklist,
        odds_enricher=lambda m: None,  # tennis bookmaker enricher kullanmaz
        manipulation_checker=_manip,
    )

    # EntryProcessor + ExitProcessor ortak deps subset — tennis paper akışı:
    # state, gate, executor, trade_logger, skipped_logger, equity_logger,
    # bot_status_writer, cycle_manager, cooldown, price_feed=None.
    # (scanner/stock/odds_client/score_enricher/command_poller None — run_heavy
    # çağrılmıyor; ExitProcessor score_map=None ile çalıştırılıyor.)
    from dataclasses import dataclass as _dc

    @_dc
    class _TennisAgentDeps:
        state: RuntimeState
        executor: Executor
        trade_logger: TradeHistoryLogger
        equity_logger: EquityHistoryLogger
        skipped_logger: SkippedTradeLogger
        bot_status_writer: BotStatusWriter
        gate: EntryGate
        cooldown: CooldownTracker
        cycle_manager: CycleManager
        price_feed: None = None

    deps = _TennisAgentDeps(
        state=state,
        executor=executor,
        trade_logger=trade_logger,
        equity_logger=equity_logger,
        skipped_logger=skipped_logger,
        bot_status_writer=bot_status_writer,
        gate=gate,
        cooldown=cooldown,
        cycle_manager=cycle_manager,
    )
    return EntryProcessor(deps), ExitProcessor(deps)
