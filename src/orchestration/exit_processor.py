"""Exit processor — light cycle exit flow (DECISIONS §4).

Pozisyon state tick + exit monitor → full/partial exit execute.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.portfolio.lifecycle import tick_position_state
from src.models.enums import ExitReason
from src.models.position import Position
from src.orchestration import operational_writers
from src.orchestration.force_close_executor import (
    ForceCloseExecutor,
    reason_to_exit_reason,
)
from src.strategy.exit import monitor as exit_monitor
from src.strategy.exit.monitor import ExitSignal, FavoredTransition, MonitorResult

logger = logging.getLogger(__name__)


class ExitProcessor:
    """Light cycle: tick state + exit evaluation + execution."""

    def __init__(self, deps) -> None:
        self.deps = deps
        # Force-close executor — espn_client deps üzerinden opsiyonel; None ise
        # time-based path tek başına çalışır (graceful degradation).
        self._force_close = ForceCloseExecutor(
            espn_client=getattr(deps, "espn_client", None),
            executor=deps.executor,
        )

    def run_light(self, score_map: dict[str, dict] | None = None) -> None:
        """Her pozisyonu cycle-state tick + exit_monitor'dan geçir.

        Args:
            score_map: condition_id → score_info dict (SPEC-B). None → empty
                (mevcut davranış: monitor.evaluate score_info={} alır).
        """
        state = self.deps.state
        scores = score_map or {}
        exits_processed = 0
        for cid in list(state.portfolio.positions.keys()):
            pos = state.portfolio.positions.get(cid)
            if pos is None:
                continue

            tick_position_state(pos)
            score_info = scores.get(cid, {})
            result: MonitorResult = exit_monitor.evaluate(
                pos,
                score_info=score_info,
                near_resolve_max_spread=self.deps.state.config.price_feed.max_spread_for_near_resolve,
                basketball_exit_cfg=self.deps.state.config.exit_basketball,
                scale_out_tiers=self.deps.state.config.scale_out.tiers,
                stop_loss_exempt_market_types=self.deps.state.config.risk.stop_loss_exempt_market_types,
            )
            self._apply_fav_transition(pos, result.fav_transition)

            if result.exit_signal is not None:
                exit_status = self._execute_exit(pos, result.exit_signal)
                if exit_status == "FILLED":
                    exits_processed += 1
                    continue
                # REJECTED veya PARTIAL_FILL → pozisyon hala (kısmen) açık.
                # Force-close safety net'i aşağıda çalıştır — derin zarar +
                # maç bitti senaryosunda bid yoksa 0 ile realize edebilsin.

            # Force-close safety net (SPEC-force-close 2026-05-27) — deep-loss
            # pozisyon + maç bitti senaryosu. ForceCloseExecutor pure-check döner,
            # tetiklenirse aşağıda fill + finalize.
            timeouts = self.deps.state.config.risk.force_close_timeouts
            fc_signal = self._force_close.check(pos, timeouts)
            if fc_signal is not None:
                self._execute_force_close(pos, fc_signal)
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

    def _execute_exit(self, pos: Position, signal: ExitSignal) -> str:
        """Exit sinyalini execute et — full veya partial.

        Executor result dict status'ı kontrol edilir:
        - REJECTED → pozisyon değişmez, retry_count artar (force-close fallback)
        - PARTIAL_FILL → kısmi satış (paper-mode adapter; bu lab şu an DRY/PAPER
          simulated FILLED dönüyor, branch dormant ama symmetry için var)
        - FILLED (veya "simulated") → tam çıkış

        Returns:
            "FILLED" → pozisyon kapandı (caller continue eder)
            "REJECTED" → bid yok / slippage → pozisyon hala açık, caller force-close'a düşmeli
            "PARTIAL_FILL" → kısmi → kalan açık, force-close kalan için tetiklenebilir
        """
        if signal.partial:
            self._execute_partial_exit(pos, signal)
            return "FILLED"  # partial-exit kendi içinde işliyor

        result = self.deps.executor.exit_position(pos, reason=signal.reason.value)
        status = result.get("status")

        if status == "REJECTED":
            # Tennis-lab Position'da exit_retry_count yok (paper-lab Phase 2 alanı).
            # setattr ile defansif artır — dormant branch ama symmetry için kalıyor.
            retry = getattr(pos, "exit_retry_count", 0) + 1
            setattr(pos, "exit_retry_count", retry)
            logger.warning(
                "EXIT REJECTED %s: %s (retry=%d)",
                pos.slug[:35], result.get("reason", "?"), retry,
            )
            return "REJECTED"

        if status == "PARTIAL_FILL":
            # Paper-mode partial fill branch — bu lab şu an simulated FILLED
            # dönüyor; bu branch dormant ama symmetry için kalıyor.
            logger.warning(
                "EXIT PARTIAL_FILL %s: paper-fill yolu bu lab'da etkin değil — full close",
                pos.slug[:35],
            )

        # FILLED (veya "simulated") — tam çıkış. Realized actual avg_price üzerinden.
        filled_shares = result.get("filled_shares", pos.shares)
        avg_price = result.get("avg_price", pos.current_price)
        self._finalize_full_exit(
            pos=pos,
            exit_price=avg_price,
            sold_shares=filled_shares,
            exit_reason_value=signal.reason.value,
            audit_signal=signal,
        )
        return "FILLED"

    def _finalize_full_exit(
        self,
        pos: Position,
        exit_price: float,
        sold_shares: float,
        exit_reason_value: str,
        audit_signal: ExitSignal | None,
    ) -> None:
        """Full-exit finalize: portfolio remove + breaker + cooldown + ws unsub + audit.

        DRY: `_execute_exit` (normal FILLED branch) + `_execute_force_close` ortak
        kullanıyor. `audit_signal=None` → synth-from-exit fallback'te `signal.detail`
        olmayan force-close path için synth record yine yazılır (signal.reason.value
        yerine exit_reason_value kullanılır).
        """
        realized = sold_shares * exit_price - pos.size_usdc

        self.deps.state.portfolio.remove_position(pos.condition_id, realized_pnl_usdc=realized)
        self.deps.state.circuit_breaker.record_exit(
            pnl_usd=realized, portfolio_value=self.deps.state.portfolio.bankroll + pos.size_usdc,
        )
        self.deps.cooldown.record_outcome(win=(realized >= 0))

        if self.deps.price_feed is not None:
            self.deps.price_feed.unsubscribe([pos.token_id])

        pnl_pct = realized / pos.size_usdc if pos.size_usdc > 0 else 0.0
        now_iso = datetime.now(timezone.utc).isoformat()
        logged = self.deps.trade_logger.update_on_exit(pos.condition_id, {
            "exit_price": exit_price,
            "exit_reason": exit_reason_value,
            "exit_pnl_usdc": round(realized, 2),
            "exit_pnl_pct": round(pnl_pct, 4),
            "exit_timestamp": now_iso,
        })
        if not logged:
            # SPEC-G: matching open record yok (orphan / phantom recovery atlandı).
            # Audit gap olusturmamak icin synth-from-exit complete record yaz.
            self._write_synth_exit_record(
                pos, exit_reason_value, exit_price, realized, pnl_pct, now_iso,
            )

        detail = audit_signal.detail if audit_signal is not None else "force_close"
        logger.info("EXIT %s: reason=%s realized=$%.2f detail=%s",
                    pos.slug[:35], exit_reason_value, realized, detail)

    def _execute_force_close(self, pos: Position, signal) -> None:
        """Force-close execution — bid book walk full slippage bypass.

        Bid varsa: realize @ avg_price (FORCE_CLOSE_ESPN veya FORCE_CLOSE_TIME).
        Bid yoksa: realize @ 0 (FORCE_CLOSE_NO_BIDS) — tam kayıp.
        Hem fill hem finalize `_finalize_full_exit` üzerinden (DRY).
        """
        avg_price, filled_shares, no_bids = self._force_close.fill_via_book(pos)
        if no_bids:
            exit_reason_value = ExitReason.FORCE_CLOSE_NO_BIDS.value
            self._finalize_full_exit(
                pos=pos, exit_price=0.0, sold_shares=pos.shares,
                exit_reason_value=exit_reason_value, audit_signal=None,
            )
        else:
            exit_reason_value = reason_to_exit_reason(signal.reason).value
            # filled_shares < pos.shares ise yine "full close" semantik:
            # bid'le satılabilen kadar realize, kalan share zarar yazılır
            # (sold_shares=filled_shares + size_usdc=pos.size_usdc → realized formula
            # otomatik kayıp gösterir).
            self._finalize_full_exit(
                pos=pos, exit_price=avg_price, sold_shares=filled_shares,
                exit_reason_value=exit_reason_value, audit_signal=None,
            )
        logger.info(
            "FORCE_CLOSE %s reason=%s shares_filled=%.2f avg=%.3f",
            (pos.slug or pos.token_id)[:40], exit_reason_value, filled_shares, avg_price,
        )

    def _write_synth_exit_record(
        self,
        pos: Position,
        exit_reason_value: str,
        exit_price: float,
        realized: float,
        pnl_pct: float,
        now_iso: str,
    ) -> None:
        """SPEC-G: orphan/phantom-yok exit'lerde audit gap'i kapatmak icin
        complete synth record yaz. Entry + exit aynı satirda, gercek pos verileriyle.

        2026-05-27: signature signal yerine primitive — force-close path da
        kullanır (signal nesnesi olmayabilir)."""
        from src.infrastructure.persistence.trade_logger import TradeRecord, _split_sport_tag
        category, league = _split_sport_tag(pos.sport_tag or "")
        try:
            record = TradeRecord(
                slug=pos.slug or "",
                condition_id=pos.condition_id,
                event_id=pos.event_id or "",
                token_id=pos.token_id or "",
                question=pos.question or "",
                sport_tag=pos.sport_tag or "",
                sport_category=category,
                league=league,
                direction=pos.direction,
                entry_price=pos.entry_price,
                size_usdc=pos.size_usdc,
                shares=pos.shares,
                confidence=pos.confidence or "",
                bookmaker_prob=pos.bookmaker_prob or 0.0,
                anchor_probability=pos.anchor_probability,
                num_bookmakers=0,
                has_sharp=False,
                entry_reason=f"synth-from-exit:{pos.entry_reason or 'unknown'}",
                entry_timestamp=pos.match_start_iso or now_iso,
                exit_price=exit_price,
                exit_reason=exit_reason_value,
                exit_pnl_usdc=round(realized, 2),
                exit_pnl_pct=round(pnl_pct, 4),
                exit_timestamp=now_iso,
            )
            self.deps.trade_logger.log(record)
            logger.info(
                "EXIT %s: synth-from-exit kaydi yazildi (orphan recovery, audit gap kapatildi)",
                pos.slug[:35],
            )
        except Exception as e:
            logger.warning(
                "EXIT %s: synth-from-exit yazimi da basarisiz: %s — bakiye in-memory korunur",
                pos.slug[:35], e,
            )

    def _execute_partial_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Scale-out partial exit.

        Basis payı (`old_size × sell_pct`) pozisyon küçültülmeden ÖNCE yakalanır
        ve bankroll'a geri kredilenir — identity `bankroll + invested = initial +
        realized_pnl` korunur (DECISIONS §5.7.7).
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
        logged = self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=pos.current_price,
        )
        if not logged:
            # SPEC-D: log_partial_exit False → audit'te matching entry yok (orphan).
            # Bakiye in-memory dogru ama defter eksik — gorunur uyari at.
            logger.warning(
                "SCALE-OUT %s: trade_history defter kayit yapilamadi "
                "(orphan?) - bakiye in-memory dogru ama audit eksik",
                pos.slug[:35],
            )
        logger.info(
            "SCALE-OUT %s: tier=%d sold=%.1f shares realized=$%.2f remaining=$%.2f",
            pos.slug[:35], signal.tier, shares_to_sell, realized, pos.size_usdc,
        )
