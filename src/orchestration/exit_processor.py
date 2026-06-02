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
from src.orchestration.exit_audit_writer import (
    emit_force_close_alert,
    write_synth_exit_record,
)
from src.orchestration.force_close_executor import ForceCloseExecutor
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
        # 2026-06-01: force-close artık otomatik exit YAPMAZ — alarm + manuel review.
        # Tek seferlik Telegram + dashboard kırmızı border (alert store flag).
        from src.infrastructure.persistence.force_close_alerts import (  # noqa: PLC0415
            ForceCloseAlertStore,
        )
        self._fc_alerts = ForceCloseAlertStore()
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
                partial_sl_tiers=self.deps.state.config.partial_sl.tiers,
                partial_sl_enabled=self.deps.state.config.partial_sl.enabled,
                graduated_sl_enabled=self.deps.state.config.graduated_sl.enabled,
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

            # Force-close ALARM (kullanıcı kararı 2026-06-01):
            # Otomatik exit YAPILMAZ — sadece tek seferlik Telegram bildirimi
            # + dashboard'da kırmızı border. Kullanıcı manuel karar verir.
            # ForceCloseExecutor.check() hâlâ eşik testini yapar (deep-loss + timeout),
            # signal varsa _emit_force_close_alert tetiklenir (no-op exit).
            timeouts = self.deps.state.config.risk.force_close_timeouts
            fc_signal = self._force_close.check(pos, timeouts)
            if fc_signal is not None:
                self._emit_force_close_alert(pos, fc_signal)

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
        # SPEC-TG-001 2026-06-02: telegram exit bildirimi (notifier disabled ise no-op)
        if self.deps.notifier is not None:
            self.deps.notifier.notify_exit(
                slug=pos.slug,
                exit_price=exit_price,
                realized_pnl=realized,
                reason=exit_reason_value,
            )

    def _emit_force_close_alert(self, pos: Position, signal) -> None:
        emit_force_close_alert(self.deps, self._fc_alerts, pos, signal)

    def _write_synth_exit_record(
        self,
        pos: Position,
        exit_reason_value: str,
        exit_price: float,
        realized: float,
        pnl_pct: float,
        now_iso: str,
    ) -> None:
        write_synth_exit_record(
            self.deps, pos, exit_reason_value, exit_price,
            realized, pnl_pct, now_iso,
        )

    def _execute_partial_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Scale-out + Partial-SL parçalı çıkış (her ikisi de partial=True).

        Reason-aware: SCALE_OUT (kâr tarafı tier) vs PARTIAL_SL (kayıp tarafı tier)
        ayrı sayaçlarda tutulur (pos.scale_out_tier vs pos.partial_sl_tier).

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
        # Reason-aware tier increment (SCALE_OUT vs PARTIAL_SL ayrı sayaçlarda).
        is_partial_sl = signal.reason == ExitReason.PARTIAL_SL
        if is_partial_sl:
            pos.partial_sl_tier = signal.tier or pos.partial_sl_tier
            pos.partial_sl_realized_usdc += realized
        else:
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
            if is_partial_sl:
                pos.partial_sl_realized_usdc -= realized
            else:
                pos.scale_out_realized_usdc -= realized
            logger.warning(
                "Partial exit aborted (race): %s — %s; mutation rolled back",
                pos.slug[:35], e,
            )
            return
        current_tier = (
            pos.partial_sl_tier if is_partial_sl else pos.scale_out_tier
        )
        logged = self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or current_tier,
            sell_pct=actual_sell_pct,         # gerçek satılan oran
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=actual_price,                # gerçek satım fiyatı
        )
        label = "PARTIAL-SL" if is_partial_sl else "SCALE-OUT"
        if not logged:
            logger.warning(
                "%s %s: trade_history defter kayit yapilamadi "
                "(orphan?) - bakiye in-memory dogru ama audit eksik",
                label, pos.slug[:35],
            )
        logger.info(
            "%s %s: tier=%d sold=%.1f shares @ $%.3f realized=$%.2f remaining=$%.2f",
            label, pos.slug[:35], signal.tier, actual_shares, actual_price, realized, pos.size_usdc,
        )
