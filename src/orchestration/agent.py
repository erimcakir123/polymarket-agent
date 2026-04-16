"""Ana agent döngüsü — katmanları bağlayan orchestrator (TDD §4).

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
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.infrastructure.telegram.command_poller import TelegramCommandPoller
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.entry_processor import EntryProcessor
from src.orchestration.exit_processor import ExitProcessor
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import RuntimeState, persist
from src.orchestration.stock_queue import StockQueue
from src.strategy.entry.gate import EntryGate

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


class Agent:
    """Bot ana döngüsü. Thin orchestration layer."""

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps
        self._stop_requested = False
        self._ws_started = False
        self._entry = EntryProcessor(deps)
        self._exit = ExitProcessor(deps)
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
                if tick.run_light:
                    self._exit.run_light()
            except Exception as e:
                logger.error("Cycle error (%s): %s", tick.reason, e, exc_info=True)

            persist(self.deps.state)
            self.deps.bot_status_writer.write_from_tick(
                mode=self.deps.state.config.mode.value, tick=tick
            )

            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            time.sleep(self.deps.cycle_manager.sleep_seconds())

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
