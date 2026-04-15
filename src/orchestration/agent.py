"""Ana agent döngüsü — katmanları bağlayan orchestrator (TDD §4).

Heavy cycle: scanner → eligible-queue / fresh → enrich → gate → execute → persist.
Light cycle: WS tick drain + exit check + position mark-to-market + persist.
Exit-triggered heavy: sonraki tick'te eligible-queue önce.

Bu dosya sadece koordinasyon yapar — iş mantığı domain/strategy'de, I/O infrastructure'da.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.portfolio.exposure import exceeds_exposure_limit
from src.domain.portfolio.lifecycle import tick_position_state
from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger, TradeRecord, _split_sport_tag
from src.infrastructure.websocket.price_feed import PriceFeed
from src.models.market import MarketData
from src.models.position import Position
from src.orchestration import operational_writers
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import RuntimeState, persist
from src.orchestration.stock_queue import StockQueue
from src.strategy.entry.gate import EntryGate
from src.strategy.exit import monitor as exit_monitor
from src.strategy.exit.monitor import ExitSignal, FavoredTransition, MonitorResult

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependency injection container — test için mock'lanabilir.

    price_feed opsiyonel: None ise WS hiç başlatılmaz (test senaryosunda
    anlık fiyat güncellemesi gerekmeyebilir). Production'da factory her zaman
    verir — gerçek exit tetiklenmesi için şart.
    """
    state: RuntimeState
    scanner: MarketScanner
    cycle_manager: CycleManager
    executor: Executor
    odds_client: object  # OddsAPIClient benzeri
    trade_logger: TradeHistoryLogger
    gate: EntryGate
    cooldown: CooldownTracker
    equity_logger: EquityHistoryLogger
    skipped_logger: SkippedTradeLogger
    stock: StockQueue
    bot_status_writer: BotStatusWriter
    price_feed: PriceFeed | None = None


class Agent:
    """Bot ana döngüsü. Thin orchestration layer."""

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps
        self._stop_requested = False
        self._ws_started = False
        # WS callback'i agent'a bağla — pozisyon fiyatlarını günceller
        if self.deps.price_feed is not None:
            self.deps.price_feed.set_callback(self._on_price_update)

    def request_stop(self) -> None:
        self._stop_requested = True
        if self.deps.price_feed is not None:
            self.deps.price_feed.stop()

    def run(self, max_ticks: int | None = None) -> None:
        """Ana döngü. max_ticks=None → sonsuza kadar; test için sayılı tick."""
        self._start_ws_if_needed()
        ticks = 0
        while not self._stop_requested:
            tick = self.deps.cycle_manager.tick(has_positions=self.deps.state.portfolio.count() > 0)
            self.deps.cooldown.new_cycle()

            try:
                if tick.run_heavy:
                    self._run_heavy(prefer_eligible_queue=tick.prefer_eligible_queue)
                if tick.run_light:
                    self._run_light()
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

    # ── WS price feed integration ──

    def _start_ws_if_needed(self) -> None:
        """İlk run'da WS başlat + mevcut pozisyonlara subscribe."""
        if self._ws_started or self.deps.price_feed is None:
            return
        # Restore edilmiş pozisyonlar varsa token'larına subscribe
        tokens = [p.token_id for p in self.deps.state.portfolio.positions.values() if p.token_id]
        if tokens:
            self.deps.price_feed.subscribe(tokens)
        self.deps.price_feed.start_background()
        self._ws_started = True

    def _on_price_update(self, token_id: str, yes_price: float, bid_price: float, _ts: float) -> None:
        """WS background thread'den geliyor — thread-safe portfolio fiyat güncellemesi.

        Sadece anlık fiyat set eder (current_price + bid_price). Peak/momentum
        state'i light cycle'da tick_position_state ile güncellenir — exit kararları
        orada alınır, WS callback hafif kalır.

        `_ts`: PriceCallback interface'i (token_id, yes_price, bid_price, timestamp).
        Timestamp şu an kullanılmıyor ama signature uyumu için positional gerekli.
        """
        try:
            self.deps.state.portfolio.update_position_price(token_id, yes_price, bid_price)
        except Exception as e:
            logger.error("WS price update error: %s", e)

    # ── Heavy cycle ──

    def _run_heavy(self, prefer_eligible_queue: bool = False) -> None:
        """Stock-first heavy cycle:

        1. Gamma scan (fresh markets + prices)
        2. Stock refresh + TTL eviction
        3. JIT batch: stock top-N (match_start ASC) enrich edilir, gate'e gider
        4. Kalan slot varsa fresh-only (stock'ta olmayan) batch aynı pipeline'dan geçer
        5. Stock snapshot disk'e yazılır

        `prefer_eligible_queue` eski exit-triggered path'i tetikliyordu; stock
        zaten her cycle match_start ASC önceliklendirdiği için informational kaldı.
        """
        del prefer_eligible_queue  # stock prioritization obsoletes the flag
        mode = self.deps.state.config.mode.value
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="scanning")

        scan_fresh = self.deps.scanner.scan()
        scan_by_cid = {m.condition_id: m for m in scan_fresh}

        # Stock housekeeping
        open_event_ids = frozenset(
            p.event_id for p in self.deps.state.portfolio.positions.values() if p.event_id
        )
        self.deps.stock.refresh_from_scan(scan_by_cid)
        self.deps.stock.evict_expired(open_event_ids=open_event_ids)

        # Slot math
        max_positions = self.deps.gate.config.max_positions
        empty_slots = max_positions - self.deps.state.portfolio.count()
        if empty_slots <= 0:
            self.deps.stock.save()
            operational_writers.log_equity_snapshot(self.deps.state.portfolio, self.deps.equity_logger)
            self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="idle")
            return

        jit_mult = self.deps.stock.config.jit_batch_multiplier

        # Stock batch first (persistent pool, chronological)
        stock_batch = self.deps.stock.top_n_by_match_start(empty_slots * jit_mult)
        if stock_batch:
            logger.info("Heavy: stock batch=%d (empty_slots=%d × %d)",
                        len(stock_batch), empty_slots, jit_mult)
            self._process_markets(stock_batch)

        # Fresh candidates not in stock — fill remaining slots
        still_empty = max_positions - self.deps.state.portfolio.count()
        if still_empty > 0:
            fresh_only = [m for m in scan_fresh if not self.deps.stock.has(m.condition_id)]
            fresh_batch = fresh_only[: still_empty * jit_mult]
            if fresh_batch:
                logger.info("Heavy: fresh batch=%d (still_empty=%d × %d)",
                            len(fresh_batch), still_empty, jit_mult)
                self._process_markets(fresh_batch)

        self.deps.stock.save()
        operational_writers.log_equity_snapshot(self.deps.state.portfolio, self.deps.equity_logger)
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="idle")

    def _process_markets(self, markets: list[MarketData]) -> None:
        """Gate'ten geçir, onaylı signal'leri execute et.

        Gate'de yapılan exposure check statik (300 market tek pass'te değerlendirilir,
        portfolio o an boş gibi görünür). Bu loop'ta execution öncesi TEKRAR kontrol
        edilir — çünkü her add_position sonrası portfolio değişiyor ve cap aşılabilir.
        """
        mode = self.deps.state.config.mode.value
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="analyzing")
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}
        max_exposure_pct = self.deps.gate.config.max_exposure_pct
        executing_written = False
        for r in results:
            market = by_cid.get(r.condition_id)
            if r.signal is None:
                if market is not None:
                    operational_writers.log_skip(self.deps.skipped_logger, market, r.skipped_reason)
                    self.deps.stock.add(market, r.skipped_reason)
                continue

            if market is None:
                continue

            # Execution-time exposure re-check (gate-time statik check yetersiz)
            if exceeds_exposure_limit(
                self.deps.state.portfolio.positions,
                r.signal.size_usdc,
                self.deps.state.portfolio.bankroll,
                max_exposure_pct,
            ):
                operational_writers.log_skip(self.deps.skipped_logger, market, "exposure_cap_reached")
                self.deps.stock.add(market, "exposure_cap_reached")
                continue

            if not executing_written:
                self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="executing")
                executing_written = True
            self._execute_entry(market, r.signal)
            self.deps.stock.remove(market.condition_id)

    def _execute_entry(self, market: MarketData, signal) -> None:
        """Sim/live order → position open → trade record."""
        token_id = market.yes_token_id if signal.direction.value == "BUY_YES" else market.no_token_id
        side = "BUY"  # Polymarket'te YES/NO ayrı token; hep BUY
        price = market.yes_price if signal.direction.value == "BUY_YES" else market.no_price
        order = self.deps.executor.place_order(
            token_id=token_id, side=side, price=price, size_usdc=signal.size_usdc,
        )
        if order.get("status") != "simulated" and order.get("status") != "placed":
            logger.warning("Order rejected: %s", order.get("reason", "?"))
            return

        fill_price = order.get("price", price)
        shares = signal.size_usdc / fill_price if fill_price > 0 else 0.0

        pos = Position(
            condition_id=market.condition_id,
            token_id=token_id,
            direction=signal.direction.value,
            entry_price=fill_price,
            size_usdc=signal.size_usdc,
            shares=shares,
            current_price=fill_price,
            anchor_probability=signal.anchor_probability,
            entry_reason=signal.entry_reason.value,
            confidence=signal.confidence,
            sport_tag=market.sport_tag,
            event_id=market.event_id or "",
            match_start_iso=market.match_start_iso,
            question=market.question,
            end_date_iso=market.end_date_iso,
            slug=market.slug,
            bookmaker_prob=signal.bookmaker_prob,
        )

        if not self.deps.state.portfolio.add_position(pos):
            # Defensive guard tetiklendi (gate normalde önler) — caller logla
            logger.warning(
                "BLOCKED add_position: %s (event=%s, cid=%s)",
                pos.slug[:35], pos.event_id, pos.condition_id[:16],
            )
            return

        # Anlık fiyat akışı için WS subscribe
        if self.deps.price_feed is not None and self._ws_started:
            self.deps.price_feed.subscribe([token_id])

        self._log_trade_entry(market, signal, pos)

    def _log_trade_entry(self, market: MarketData, signal, pos: Position) -> None:
        """TradeHistoryLogger'a yeni trade entry kaydı."""
        category, league = _split_sport_tag(market.sport_tag)
        record = TradeRecord(
            slug=market.slug,
            condition_id=market.condition_id,
            event_id=market.event_id or "",
            token_id=pos.token_id,
            sport_tag=market.sport_tag,
            sport_category=category,
            league=league,
            direction=signal.direction.value,
            entry_price=pos.entry_price,
            size_usdc=pos.size_usdc,
            shares=pos.shares,
            confidence=signal.confidence,
            bookmaker_prob=signal.bookmaker_prob,
            anchor_probability=signal.anchor_probability,
            num_bookmakers=signal.num_bookmakers,
            has_sharp=signal.has_sharp,
            entry_reason=signal.entry_reason.value,
            entry_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.deps.trade_logger.log(record)

    # ── Light cycle ──

    def _run_light(self) -> None:
        """Her pozisyonu cycle-state tick + exit_monitor'dan geçir; tetiklenen exit'leri execute et."""
        state = self.deps.state
        exits_processed = 0
        for cid in list(state.portfolio.positions.keys()):
            pos = state.portfolio.positions.get(cid)
            if pos is None:
                continue

            # Cycle state tick: peak, momentum, ever_in_profit, consecutive_down, cumulative_drop
            tick_position_state(pos)

            result: MonitorResult = exit_monitor.evaluate(pos)

            # FAV transition (state update)
            self._apply_fav_transition(pos, result.fav_transition)

            if result.exit_signal is not None:
                self._execute_exit(pos, result.exit_signal)
                exits_processed += 1

        if exits_processed > 0:
            self.deps.cycle_manager.signal_exit_happened()

    def _apply_fav_transition(self, pos: Position, transition: FavoredTransition) -> None:
        if transition.promote and not pos.favored:
            pos.favored = True
            logger.info("FAV PROMOTED: %s", pos.slug[:40])
        elif transition.demote and pos.favored:
            pos.favored = False
            logger.info("FAV DEMOTED: %s", pos.slug[:40])

    def _execute_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Exit sinyalini execute et — full veya partial (scale-out)."""
        if signal.partial:
            self._execute_partial_exit(pos, signal)
            return

        # Full exit
        self.deps.executor.exit_position(pos, reason=signal.reason.value)

        # Realized = unrealized_pnl (Position computed property, token-native).
        realized = pos.unrealized_pnl_usdc

        self.deps.state.portfolio.remove_position(pos.condition_id, realized_pnl_usdc=realized)
        self.deps.state.circuit_breaker.record_exit(
            pnl_usd=realized, portfolio_value=self.deps.state.portfolio.bankroll + pos.size_usdc,
        )
        self.deps.cooldown.record_outcome(win=(realized >= 0))

        # WS unsubscribe — bu token için artık fiyat akışına gerek yok
        if self.deps.price_feed is not None and self._ws_started:
            self.deps.price_feed.unsubscribe([pos.token_id])

        pnl_pct = realized / pos.size_usdc if pos.size_usdc > 0 else 0.0
        self.deps.trade_logger.update_on_exit(pos.condition_id, {
            "exit_price": pos.current_price,
            "exit_reason": signal.reason.value,
            "exit_pnl_usdc": round(realized, 2),
            "exit_pnl_pct": round(pnl_pct, 4),
            "exit_timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("EXIT %s: reason=%s realized=$%.2f detail=%s",
                    pos.slug[:35], signal.reason.value, realized, signal.detail)

    def _execute_partial_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Scale-out partial exit: pozisyon korunur, tier/shares/realized güncellenir,
        trade_history'e partial kayıt yazılır.
        """
        shares_to_sell = pos.shares * signal.sell_pct
        realized = pos.unrealized_pnl_usdc * signal.sell_pct
        pos.shares -= shares_to_sell
        pos.size_usdc *= (1 - signal.sell_pct)
        pos.scale_out_tier = signal.tier or pos.scale_out_tier
        pos.scale_out_realized_usdc += realized
        self.deps.state.portfolio.apply_partial_exit(pos.condition_id, realized_usdc=realized)
        self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(
            "SCALE-OUT %s: tier=%d sold=%.1f shares realized=$%.2f remaining=$%.2f",
            pos.slug[:35], signal.tier, shares_to_sell, realized, pos.size_usdc,
        )

