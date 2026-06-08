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
from src.orchestration.notifier_hooks import notify_exit_safe
from src.orchestration.exit_audit_writer import emit_force_close_alert
from src.orchestration.force_close_executor import ForceCloseExecutor
from src.strategy.exit import monitor as exit_monitor
from src.strategy.exit import polymarket_resolution
from src.strategy.exit.monitor import ExitSignal, FavoredTransition, MonitorResult

logger = logging.getLogger(__name__)

# SPEC-Z24: Polymarket void/iptal protokol payout'u (her iki outcome 0.50/0.50).
# Bu payout'la resolve olan trade gerçek kazanç/kayıp değil → exit_reason=voided.
_VOID_PAYOUT = 0.50
_VOID_PAYOUT_TOL = 0.01  # float karşılaştırma toleransı

# Kayıp-tarafı çıkışlar — gerçek piyasa emri gibi satılır (kayma tabanı bypass).
# Kâr/lock tarafı (NEAR_RESOLVE, SCALE_OUT) market modu KULLANMAZ: yüksek bid'e
# satar, kayma kontrolü orada gerçekçidir.
_LOSS_CUT_REASONS = frozenset({
    ExitReason.STOP_LOSS, ExitReason.GRADUATED_SL, ExitReason.PARTIAL_SL,
    ExitReason.NEVER_IN_PROFIT, ExitReason.ULTRA_LOW_GUARD, ExitReason.HOLD_REVOKED,
})


def _is_loss_cut(reason: ExitReason) -> bool:
    return reason in _LOSS_CUT_REASONS


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
        # SPEC-Z27: void/iade DE gerçek payout. Polymarket 0.5/0.5'te her hisse 0.50
        # öder (basis iadesi DEĞİL) → 0.50 üstü girişte gerçek zarar, altı kâr.
        # is_void yalnızca etiket (VOIDED) içindir; muhasebe resolved ile aynı formül.
        is_void = abs(signal.exit_price - _VOID_PAYOUT) < _VOID_PAYOUT_TOL
        realized = pos.shares * signal.exit_price - pos.size_usdc
        reason = ExitReason.VOIDED.value if is_void else ExitReason.RESOLVED.value
        logger.info(
            "RESOLVED %s: payout=%.2f realized=$%.2f%s",
            (pos.slug or pos.condition_id)[:40], signal.exit_price, realized,
            " (void/iade)" if is_void else "",
        )
        self._finalize_full_exit(
            pos=pos,
            exit_price=signal.exit_price,
            realized=realized,
            exit_reason_value=reason,
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

        # GERÇEKÇİLİK: executor sonucunu onurlandır (partial exit deseniyle birebir).
        # Eski hata: sonuç yok sayılıp her zaman current_price'tan "FILLED" yazılıyordu
        # → boş defterde hayali kapanış + ask fiyatından şişkin realized.
        order = self.deps.executor.exit_position(
            pos, reason=signal.reason.value, market=_is_loss_cut(signal.reason),
        )
        status = order.get("status", "REJECTED")
        if status not in ("simulated", "placed", "FILLED", "PARTIAL_FILL"):
            logger.warning(
                "EXIT REJECTED %s: %s — pozisyon korunur, kapatma yok",
                pos.slug[:35], order.get("reason", "?"),
            )
            return "REJECTED"
        filled_shares = float(order.get("filled_shares") or pos.shares)
        avg_price = float(order.get("avg_price") or pos.current_price)
        if filled_shares <= 0:
            logger.warning("EXIT filled_shares=0 %s — pozisyon korunur", pos.slug[:35])
            return "REJECTED"

        # Kısmi dolum (tam çıkış istendi ama defter tamamını alamadı): gerçek piyasada
        # dolan kısım satılır, kalan elde kalır. Dolan kısmı işle, pozisyonu tut.
        if status == "PARTIAL_FILL" and filled_shares < pos.shares - 1e-9:
            ok, realized, _pct = self._book_sale(pos, filled_shares, avg_price)
            if not ok:
                return "REJECTED"
            self._append_partial_event(pos, tier=0, sell_pct=_pct, realized=realized, price=avg_price)
            logger.info(
                "EXIT PARTIAL-FILL %s: %.1f hisse @ $%.3f realized=$%.2f — kalan tutuluyor",
                pos.slug[:35], filled_shares, avg_price, realized,
            )
            return "PARTIAL"

        realized = filled_shares * avg_price - pos.size_usdc
        self._finalize_full_exit(
            pos=pos,
            exit_price=avg_price,
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

        now_iso = datetime.now(timezone.utc).isoformat()
        # SPEC-Z17 (2026-06-04): tek truth = append-only event log.
        # Legacy trade_history.jsonl yazımı (update_on_exit + synth-from-exit
        # fallback) tamamen kaldırıldı (Task 12). Event log her zaman append eder,
        # matching open record gereksinimi yok → orphan/phantom path artık yok.
        if getattr(self.deps, "trade_event_log", None) is not None:
            self.deps.trade_event_log.append_final(
                condition_id=pos.condition_id,
                slug=pos.slug or "",
                question=pos.question or "",
                sport_tag=pos.sport_tag or "",
                source=pos.source or "",
                exit_price=exit_price, exit_reason=exit_reason_value,
                exit_pnl_usdc=round(realized, 2), exit_timestamp=now_iso,
            )

        detail = audit_signal.detail if audit_signal is not None else "force_close"
        logger.info("EXIT %s: reason=%s realized=$%.2f detail=%s",
                    pos.slug[:35], exit_reason_value, realized, detail)
        notify_exit_safe(
            self.deps, slug=pos.slug, exit_price=exit_price,
            realized_pnl=realized, reason=exit_reason_value,
        )

    def _emit_force_close_alert(self, pos: Position, signal) -> None:
        emit_force_close_alert(self.deps, self._fc_alerts, pos, signal)

    def _book_sale(self, pos: Position, shares: float, price: float) -> tuple[bool, float, float]:
        """Pozisyonu `shares` kadar küçült + portfolio'ya realized işle (partial + tam-çıkış-kısmi-dolum ortak).

        Basis identity korunur (bankroll+invested = initial+realized). Race (ValueError)
        → shares/size_usdc mutation rollback + (False, 0, 0). Tier sayaçları ve event log
        ÇAĞIRANA ait (reason'a göre değişir).
        Returns: (ok, realized_usdc, sell_pct).
        """
        sell_pct = shares / pos.shares if pos.shares > 0 else 0.0
        basis_returned = pos.size_usdc * sell_pct
        realized = shares * (price - pos.entry_price)
        pos.shares -= shares
        pos.size_usdc *= (1 - sell_pct)
        try:
            self.deps.state.portfolio.apply_partial_exit(
                pos.condition_id,
                basis_returned_usdc=basis_returned,
                realized_usdc=realized,
            )
        except ValueError as e:
            pos.shares += shares
            if sell_pct < 1.0:
                pos.size_usdc /= (1 - sell_pct)
            logger.warning(
                "Sale aborted (race): %s — %s; mutation rolled back", pos.slug[:35], e,
            )
            return False, 0.0, 0.0
        return True, realized, sell_pct

    def _append_partial_event(
        self, pos: Position, tier: int, sell_pct: float, realized: float, price: float,
    ) -> None:
        if getattr(self.deps, "trade_event_log", None) is None:
            return
        self.deps.trade_event_log.append_partial(
            condition_id=pos.condition_id,
            slug=pos.slug or "",
            question=pos.question or "",
            sport_tag=pos.sport_tag or "",
            source=pos.source or "",
            tier=tier,
            sell_pct=sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=price,
        )

    def _execute_partial_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Scale-out + Partial-SL parçalı çıkış. Reason-aware tier sayaçları
        (scale_out_tier vs partial_sl_tier). REJECTED → pozisyon korunur, defter
        kaydı yok. Gerçek filled_shares/avg_price ile defter (_book_sale)."""
        intended_shares = pos.shares * signal.sell_pct
        order = self.deps.executor.partial_sell(
            token_id=pos.token_id,
            shares=intended_shares,
            target_price=pos.current_price,
            reason="scale_out",
            market=(signal.reason == ExitReason.PARTIAL_SL),
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

        # Gerçek satım miktarına göre defter güncelle (ortak _book_sale).
        ok, realized, actual_sell_pct = self._book_sale(pos, actual_shares, actual_price)
        if not ok:
            return
        # Reason-aware tier increment (SCALE_OUT vs PARTIAL_SL ayrı sayaçlarda).
        is_partial_sl = signal.reason == ExitReason.PARTIAL_SL
        if is_partial_sl:
            pos.partial_sl_tier = signal.tier or pos.partial_sl_tier
            pos.partial_sl_realized_usdc += realized
        else:
            pos.scale_out_tier = signal.tier or pos.scale_out_tier
            pos.scale_out_realized_usdc += realized
        current_tier = pos.partial_sl_tier if is_partial_sl else pos.scale_out_tier
        self._append_partial_event(
            pos, tier=signal.tier or current_tier, sell_pct=actual_sell_pct,
            realized=realized, price=actual_price,
        )
        label = "PARTIAL-SL" if is_partial_sl else "SCALE-OUT"
        logger.info(
            "%s %s: tier=%s sold=%.1f shares @ $%.3f realized=$%.2f remaining=$%.2f",
            label, pos.slug[:35], signal.tier, actual_shares, actual_price, realized, pos.size_usdc,
        )
