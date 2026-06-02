"""Ana agent döngüsü — katmanları bağlayan orchestrator (DECISIONS §4).

Heavy cycle: EntryProcessor'a delegate edilir.
Light cycle: ExitProcessor'a delegate edilir.

Bu dosya sadece lifecycle koordinasyonu yapar — iş mantığı
entry_processor/exit_processor + domain/strategy'de, I/O infrastructure'da.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.apis.espn_client import ESPNClient
from src.infrastructure.apis.gamma_client import GammaClient
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.presentation.notifier import TelegramNotifier
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration._agent_resilience import CycleResilience
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.entry_processor import EntryProcessor
from src.orchestration.exit_processor import ExitProcessor
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import RuntimeState, persist
from src.orchestration.stock_queue import StockQueue
from src.orchestration.score_enricher import ScoreEnricher
from src.orchestration.tennis_start_enricher import TennisStartEnricher
from src.strategy.entry.gate import EntryGate
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependency injection container — test için mock'lanabilir."""
    state: RuntimeState
    scanner: MarketScanner
    cycle_manager: CycleManager
    executor: Executor
    odds_client: object
    trade_logger: TradeHistoryLogger
    gate: EntryGate
    cooldown: CooldownTracker
    equity_logger: EquityHistoryLogger
    skipped_logger: SkippedTradeLogger
    stock: StockQueue
    bot_status_writer: BotStatusWriter
    price_feed: PriceFeed | None = None
    command_poller: TelegramCommandPoller | None = None
    score_enricher: ScoreEnricher | None = None  # SPEC-B: light cycle score injector + SPEC-Z5 match_live refresh
    mlb_submarket_engine: MlbSubmarketEngineProtocol | None = None  # SPEC-R: Plan 4'te gerçek engine
    tennis_start_enricher: TennisStartEnricher | None = None  # SPEC: light cycle'da tennis pozisyonlarinin match_start_iso'sunu ESPN ile refresh eder
    espn_client: ESPNClient | None = None  # SPEC-force-close 2026-05-27: get_match_status icin
    gamma_client: GammaClient | None = None  # 2026-05-28: ExitProcessor polymarket-resolution detector
    notifier: TelegramNotifier | None = None  # SPEC-TG-001 2026-06-02: entry/exit/critical alert


class Agent:
    """Bot ana döngüsü. Thin orchestration layer."""

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps
        self._stop_requested = False
        self._ws_started = False
        self._entry = EntryProcessor(deps)
        self._exit = ExitProcessor(deps)
        self._resilience = CycleResilience(
            max_consecutive=deps.state.config.agent.cycle_max_consecutive_errors
        )
        if self.deps.price_feed is not None:
            self.deps.price_feed.set_callback(self._on_price_update)

    def request_stop(self) -> None:
        self._stop_requested = True
        if self.deps.price_feed is not None:
            self.deps.price_feed.stop()

    def run(self, max_ticks: int | None = None) -> None:
        """Ana döngü. max_ticks=None → sonsuza kadar; test için sayılı tick."""
        self._start_ws_if_needed()
        self._start_command_poller()
        ticks = 0
        while not self._stop_requested:
            tick = self.deps.cycle_manager.tick(has_positions=self.deps.state.portfolio.count() > 0)
            self.deps.cooldown.new_cycle()

            try:
                if tick.run_heavy:
                    self._entry.run_heavy()
                    # SPEC-M: Heavy sonrasi en yakin maca kadar saatleri hesapla,
                    # cycle_manager bir sonraki interval'i bu bilgiyle secsin.
                    nearest = self._compute_nearest_match_hours()
                    self.deps.cycle_manager.update_nearest_match_hours(nearest)
                if tick.run_light:
                    # Tennis pozisyonlarinin match_start_iso'sunu ESPN ile refresh et
                    # (TTL-cached, exit kararlari guncel match start ile alinsin).
                    if self.deps.tennis_start_enricher is not None:
                        self.deps.tennis_start_enricher.refresh_positions(
                            list(self.deps.state.portfolio.positions.values()),
                        )
                    score_map: dict[str, dict] = {}
                    if self.deps.score_enricher is not None:
                        try:
                            # SPEC-Z5: ESPN'den match_live/match_ended bayraklarini tum
                            # sporlar icin tazele (eskiden sadece tenis icin vardi).
                            # Polymarket event.live gecikiyor olabilir; ESPN canli kaynak.
                            self.deps.score_enricher.refresh_match_status(
                                self.deps.state.portfolio.positions,
                            )
                            score_map = self.deps.score_enricher.get_scores_if_due(
                                self.deps.state.portfolio.positions,
                            )
                        except Exception as e:
                            logger.warning(
                                "Score enrichment failed: %s — using empty score_map", e,
                            )
                            score_map = {}
                    self._exit.run_light(score_map=score_map)
                self._resilience.record_success()
            except Exception as e:
                logger.error("Cycle error (%s): %s", tick.reason, e, exc_info=True)
                self._resilience.record_error(e)
                if self._resilience.should_stop():
                    logger.critical(
                        "STOPPING: %d ardışık programatik hata (%s) — bot durduruldu",
                        self._resilience.consecutive_count, type(e).__name__,
                    )
                    self._stop_requested = True

            persist(self.deps.state)
            self.deps.bot_status_writer.write_from_tick(
                mode=self.deps.state.config.mode.value, tick=tick
            )

            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            time.sleep(self.deps.cycle_manager.sleep_seconds())

    def _compute_nearest_match_hours(self) -> float | None:
        """SPEC-M: Acik pozisyon + stock'taki market'lerden en yakin maca saatleri.

        Kaynaklar: portfolio.positions + stock.entries (her ikisinde match_start_iso var).
        Sadece gelecek (positive hours) macleri sayar. Hiç maç yoksa None.

        Caller (cycle_manager) None gorunce default heavy/night davranisi uygular.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        candidates: list[str] = []
        # Acik pozisyonlar
        for pos in self.deps.state.portfolio.positions.values():
            iso = (pos.match_start_iso or "").strip()
            if iso:
                candidates.append(iso)
        # Stock'taki market'ler
        try:
            for entry in self.deps.stock.all_entries():
                iso = (entry.market.match_start_iso or "").strip()
                if iso:
                    candidates.append(iso)
        except (AttributeError, TypeError):
            pass  # stock erisilebilir degilse atla (cold start, test mock)

        min_hours: float | None = None
        for iso in candidates:
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            hours = (dt - now).total_seconds() / 3600.0
            if hours <= 0:
                continue  # gecmis veya bashlamis mac
            if min_hours is None or hours < min_hours:
                min_hours = hours
        return min_hours

    def _start_ws_if_needed(self) -> None:
        if self._ws_started or self.deps.price_feed is None:
            return
        tokens = [p.token_id for p in self.deps.state.portfolio.positions.values() if p.token_id]
        if tokens:
            self.deps.price_feed.subscribe(tokens)
        self.deps.price_feed.start_background()
        self._ws_started = True

    def _start_command_poller(self) -> None:
        if self.deps.command_poller is None:
            return
        self.deps.command_poller.start()

    def _on_price_update(self, token_id: str, yes_price: float, bid_price: float, _ts: float) -> None:
        try:
            self.deps.state.portfolio.update_position_price(token_id, yes_price, bid_price)
        except Exception as e:
            logger.error("WS price update error: %s", e)
