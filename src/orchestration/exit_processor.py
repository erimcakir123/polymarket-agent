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
from src.strategy.exit import polymarket_resolution
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
        # 2026-05-28: Polymarket resolution detector — light tick sayaci per pozisyon.
        # Her N tick'te bir gamma'ya sorgu; N=0 → devre disi. gamma_client deps'te
        # yoksa feature sessizce kapali (backwards-compat).
        self._resolution_tick_counters: dict[str, int] = {}

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

            # 2026-05-28: Polymarket auto-resolution detector — diğer exit chain'lerden
            # ÖNCE çalışır. Market kapanmış (closed=true + uma resolved) ise WS price
            # feed güncellemeyi durdurur, normal SL/TP/scale-out asla tetiklenmez.
            # Bu detector açık pozisyonu owned-side payout (0/1) ile finalize eder.
            if self._check_polymarket_resolution(pos):
                exits_processed += 1
                continue

            tick_position_state(pos)
            score_info = scores.get(cid, {})
            result: MonitorResult = exit_monitor.evaluate(
                pos,
                score_info=score_info,
                near_resolve_max_spread=self.deps.state.config.price_feed.max_spread_for_near_resolve,
                basketball_exit_cfg=self.deps.state.config.exit_basketball,
                scale_out_tiers=self.deps.state.config.scale_out.tiers,
                high_entry_threshold=self.deps.state.config.scale_out.high_entry_threshold,
                high_entry_upper=self.deps.state.config.scale_out.high_entry_upper,
            )
            self._apply_fav_transition(pos, result.fav_transition)

            if result.exit_signal is not None:
                exit_status = self._execute_exit(pos, result.exit_signal)
                if exit_status == "FILLED":
                    exits_processed += 1
                    continue
                # Hiç fill olmadıysa (ana botta şu an için simulated her zaman FILLED)
                # force-close safety net'i aşağıda çalıştır — pozisyon hâlâ açık demek.

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

    def _check_polymarket_resolution(self, pos: Position) -> bool:
        """Pozisyonun market'i Polymarket'te resolve oldu mu?

        Her N light tick'te bir gamma'ya sorgu (config.risk.polymarket_resolution_check_every_n_ticks).
        Resolved ise owned-side payout ile finalize → True. Aksi → False.

        Backwards-compat: gamma_client deps'te yoksa veya N=0 ise feature kapali,
        her zaman False döner (mevcut exit chain aynen çalışır).
        """
        every_n = self.deps.state.config.risk.polymarket_resolution_check_every_n_ticks
        if every_n <= 0:
            return False
        gamma_client = getattr(self.deps, "gamma_client", None)
        if gamma_client is None:
            return False

        counter = self._resolution_tick_counters.get(pos.condition_id, 0)
        self._resolution_tick_counters[pos.condition_id] = counter + 1
        # Tick 0 (ilk gör) ve her N tick'te bir → fetch
        if counter % every_n != 0:
            return False

        try:
            market = gamma_client.fetch_closed_market_by_condition(pos.condition_id)
        except Exception as e:
            logger.warning(
                "Polymarket resolution check failed for %s: %s",
                pos.slug[:35] or pos.condition_id[:20], e,
            )
            return False

        signal = polymarket_resolution.check_resolution(pos, market)
        if signal is None:
            return False

        # Payout-based realized: shares × payout - basis (owned-side semantik,
        # BUY_NO için shares NO token'a aittir, payout NO resolution price).
        realized = pos.shares * signal.exit_price - pos.size_usdc
        logger.info(
            "RESOLVED %s: payout=%.2f realized=$%.2f",
            (pos.slug or pos.condition_id)[:40], signal.exit_price, realized,
        )
        self._finalize_full_exit(
            pos=pos,
            exit_price=signal.exit_price,
            realized=realized,
            exit_reason_value=ExitReason.RESOLVED.value,
            audit_signal=None,
        )
        self._resolution_tick_counters.pop(pos.condition_id, None)
        return True

    def _apply_fav_transition(self, pos: Position, transition: FavoredTransition) -> None:
        if transition.promote and not pos.favored:
            pos.favored = True
            logger.info("FAV PROMOTED: %s", pos.slug[:40])
        elif transition.demote and pos.favored:
            pos.favored = False
            logger.info("FAV DEMOTED: %s", pos.slug[:40])

    def _execute_exit(self, pos: Position, signal: ExitSignal) -> str:
        """Exit sinyalini execute et — full veya partial.

        Returns:
            "FILLED" → pozisyon kapandı (caller continue eder)
            (ana bot mevcut akış: simulated/live her ikisi de FILLED varsayar;
            force-close branch'i ileride REJECTED/PARTIAL_FILL dönecek paper
            mode için hazır.)
        """
        if signal.partial:
            self._execute_partial_exit(pos, signal)
            return "FILLED"

        self.deps.executor.exit_position(pos, reason=signal.reason.value)
        realized = pos.unrealized_pnl_usdc

        self._finalize_full_exit(
            pos=pos,
            exit_price=pos.current_price,
            realized=realized,
            exit_reason_value=signal.reason.value,
            audit_signal=signal,
        )
        return "FILLED"

    def _finalize_full_exit(
        self,
        pos: Position,
        exit_price: float,
        realized: float,
        exit_reason_value: str,
        audit_signal: ExitSignal | None,
    ) -> None:
        """Full-exit finalize: portfolio remove + breaker + cooldown + ws unsub + audit.

        DRY: `_execute_exit` (normal FILLED branch) + `_execute_force_close` ortak
        kullanıyor. `audit_signal=None` → synth-from-exit fallback'te `signal.detail`
        olmayan force-close path için synth record yine yazılır.
        """
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
            # Audit gap olusturmamak icin synth-from-exit complete record yaz —
            # entry_price + exit_price ayni satirda, exit_reason "synth-from-exit".
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

        2026-05-29 (Phase 2): Paper modda no_bids → realize @ 0 YAPMAZ;
        pozisyon "stuck" durumda açık kalır + log alarm. Sonraki cycle yeniden
        dener (gerçek live davranışı). DRY_RUN/LIVE mevcut davranışı korur.
        """
        from src.config.settings import Mode
        avg_price, filled_shares, no_bids = self._force_close.fill_via_book(pos)
        executor_mode = getattr(self.deps.executor, "mode", Mode.DRY_RUN)
        if no_bids:
            if executor_mode == Mode.PAPER:
                logger.warning(
                    "FORCE_CLOSE_STUCK_PAPER %s no_bids — pozisyon acik, "
                    "sonraki cycle retry. pnl_pct=%.2f",
                    (pos.slug or pos.token_id)[:40], pos.unrealized_pnl_pct,
                )
                return  # state mutation yok; pozisyon stuck kalır
            exit_reason_value = ExitReason.FORCE_CLOSE_NO_BIDS.value
            # Bid yok → realize @ 0, tam size kaybı (-size_usdc).
            self._finalize_full_exit(
                pos=pos, exit_price=0.0, realized=-pos.size_usdc,
                exit_reason_value=exit_reason_value, audit_signal=None,
            )
        else:
            exit_reason_value = reason_to_exit_reason(signal.reason).value
            # filled_shares < pos.shares ise yine "full close" semantik:
            # bid'le satılabilen kadar realize, kalan share zarar yazılır.
            realized = filled_shares * avg_price - pos.size_usdc
            self._finalize_full_exit(
                pos=pos, exit_price=avg_price, realized=realized,
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

        2026-05-30 fix (tennis-paper-lab parity): GERÇEK satım YAPILMADAN
        defter mutate edilmiyordu — paper'da hayali +$334 kazanç yazıyordu,
        live'da Polymarket'e emir gitmeden bankroll yazılırdı.

        Akış:
          1. executor.partial_sell çağrılır (paper'da real book walk, live'da
             gerçek Polymarket market sell, dry_run'da sahte fill).
          2. status REJECTED → satım yapılamadı, pozisyon AYNEN kalır, defter
             kaydı YAPILMAZ. Live davranışıyla birebir.
          3. status FILLED/PARTIAL_FILL/simulated → gerçek filled_shares ile
             pozisyon küçültülür, gerçek avg_price ile PnL hesaplanır.

        Basis payı identity korunur: `bankroll + invested = initial + realized_pnl`.
        """
        intended_shares = pos.shares * signal.sell_pct
        order = self.deps.executor.partial_sell(
            token_id=pos.token_id,
            shares=intended_shares,
            target_price=pos.current_price,
            reason="scale_out",
        )
        status = order.get("status", "REJECTED")
        success = status in ("simulated", "placed", "FILLED", "PARTIAL_FILL")
        if not success:
            logger.warning(
                "SCALE-OUT REJECTED %s: %s — pozisyon korunur, defter kaydı yok",
                pos.slug[:40], order.get("reason", "?"),
            )
            return

        # GERÇEK filled_shares ve avg_price kullan (executor döndü)
        actual_shares = float(order.get("filled_shares") or intended_shares)
        actual_price = float(order.get("avg_price") or pos.current_price)
        if actual_shares <= 0:
            logger.warning(
                "SCALE-OUT FILLED ama filled_shares=0: %s — kayıt yapılmıyor",
                pos.slug[:40],
            )
            return

        # Gerçek satım miktarına göre defter güncelle
        actual_sell_pct = actual_shares / pos.shares if pos.shares > 0 else 0.0
        basis_returned = pos.size_usdc * actual_sell_pct
        # Realized PnL = actual sold shares × (sell_price - entry_price)
        realized = actual_shares * (actual_price - pos.entry_price)
        pos.shares -= actual_shares
        pos.size_usdc *= (1 - actual_sell_pct)
        pos.scale_out_tier = signal.tier or pos.scale_out_tier
        pos.scale_out_realized_usdc += realized
        try:
            self.deps.state.portfolio.apply_partial_exit(
                pos.condition_id,
                basis_returned_usdc=basis_returned,
                realized_usdc=realized,
            )
        except ValueError as e:
            pos.shares += actual_shares
            if actual_sell_pct < 1.0:
                pos.size_usdc /= (1 - actual_sell_pct)
            pos.scale_out_realized_usdc -= realized
            logger.warning(
                "Partial exit aborted (race): %s — %s; mutation rolled back",
                pos.slug[:35], e,
            )
            return
        logged = self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=actual_sell_pct,         # gerçek satılan oran
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=actual_price,                # gerçek satım fiyatı
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
            "SCALE-OUT %s: tier=%d sold=%.1f shares @ $%.3f realized=$%.2f remaining=$%.2f",
            pos.slug[:35], signal.tier, actual_shares, actual_price, realized, pos.size_usdc,
        )
