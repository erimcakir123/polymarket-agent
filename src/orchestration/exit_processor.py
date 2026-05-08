"""Exit processor — light cycle exit flow (TDD §4).

Pozisyon state tick + exit monitor → full/partial exit execute.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.portfolio.lifecycle import tick_position_state
from src.models.position import Position
from src.orchestration import operational_writers
from src.strategy.exit import monitor as exit_monitor
from src.strategy.exit.monitor import ExitSignal, FavoredTransition, MonitorResult

logger = logging.getLogger(__name__)


class ExitProcessor:
    """Light cycle: tick state + exit evaluation + execution."""

    def __init__(self, deps) -> None:
        self.deps = deps

    def run_light(self) -> None:
        """Her pozisyonu cycle-state tick + exit_monitor'dan geçir."""
        state = self.deps.state
        exits_processed = 0
        for cid in list(state.portfolio.positions.keys()):
            pos = state.portfolio.positions.get(cid)
            if pos is None:
                continue

            tick_position_state(pos)
            result: MonitorResult = exit_monitor.evaluate(pos)
            self._apply_fav_transition(pos, result.fav_transition)

            if result.exit_signal is not None:
                self._execute_exit(pos, result.exit_signal)
                exits_processed += 1

        if exits_processed > 0:
            self.deps.cycle_manager.signal_exit_happened()
            # Dashboard realized_pnl anlık güncellensin — bir sonraki heavy cycle bekleme.
            operational_writers.log_equity_snapshot(state.portfolio, self.deps.equity_logger)

    def _apply_fav_transition(self, pos: Position, transition: FavoredTransition) -> None:
        if transition.promote and not pos.favored:
            pos.favored = True
            logger.info("FAV PROMOTED: %s", pos.slug[:40])
        elif transition.demote and pos.favored:
            pos.favored = False
            logger.info("FAV DEMOTED: %s", pos.slug[:40])

    def _execute_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Exit sinyalini execute et — full veya partial."""
        if signal.partial:
            self._execute_partial_exit(pos, signal)
            return

        self.deps.executor.exit_position(pos, reason=signal.reason.value)
        realized = pos.unrealized_pnl_usdc

        self.deps.state.portfolio.remove_position(pos.condition_id, realized_pnl_usdc=realized)
        self.deps.state.circuit_breaker.record_exit(
            pnl_usd=realized, portfolio_value=self.deps.state.portfolio.bankroll + pos.size_usdc,
        )
        self.deps.cooldown.record_outcome(win=(realized >= 0))

        if self.deps.price_feed is not None:
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
        """Scale-out partial exit.

        Basis payı (`old_size × sell_pct`) pozisyon küçültülmeden ÖNCE yakalanır
        ve bankroll'a geri kredilenir — identity `bankroll + invested = initial +
        realized_pnl` korunur (TDD §5.7.7).
        """
        shares_to_sell = pos.shares * signal.sell_pct
        realized = pos.unrealized_pnl_usdc * signal.sell_pct
        basis_returned = pos.size_usdc * signal.sell_pct
        pos.shares -= shares_to_sell
        pos.size_usdc *= (1 - signal.sell_pct)
        pos.scale_out_tier = signal.tier or pos.scale_out_tier
        pos.scale_out_realized_usdc += realized
        # State mutation'ı (shares, size) BURADAN önce yapıldı.
        # apply_partial_exit ValueError fırlatırsa pozisyon arada silinmiş demek
        # → mutation'ı rollback edip uyarı log'la (full exit zaten state'i temizledi).
        try:
            self.deps.state.portfolio.apply_partial_exit(
                pos.condition_id,
                basis_returned_usdc=basis_returned,
                realized_usdc=realized,
            )
        except ValueError as e:
            # Rollback pozisyon mutation'ı (scale_out_tier monotonik forward-only, skip).
            pos.shares += shares_to_sell
            if signal.sell_pct < 1.0:
                pos.size_usdc /= (1 - signal.sell_pct)
            pos.scale_out_realized_usdc -= realized
            logger.warning(
                "Partial exit aborted (race): %s — %s; mutation rolled back",
                pos.slug[:35], e,
            )
            return
        self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=pos.current_price,
        )
        logger.info(
            "SCALE-OUT %s: tier=%d sold=%.1f shares realized=$%.2f remaining=$%.2f",
            pos.slug[:35], signal.tier, shares_to_sell, realized, pos.size_usdc,
        )
