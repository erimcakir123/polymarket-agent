"""Exit processor — light cycle exit flow (TDD §4).

Pozisyon state tick + exit monitor → full/partial exit execute.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.portfolio.lifecycle import tick_position_state
from src.infrastructure.persistence.archive_logger import ArchiveExitRecord
from src.infrastructure.persistence.trade_logger import TradeRecord, _split_sport_tag
from src.models.position import Position
from src.strategy.exit import monitor as exit_monitor
from src.strategy.exit.monitor import ExitSignal, FavoredTransition, MonitorResult
from src.strategy.exit.price_cap import SLParams

logger = logging.getLogger(__name__)


class ExitProcessor:
    """Light cycle: tick state + exit evaluation + execution."""

    def __init__(self, deps) -> None:
        self.deps = deps

    def run_light(self, score_map: dict[str, dict] | None = None) -> None:
        """Her pozisyonu cycle-state tick + exit_monitor'dan geçir."""
        score_map = score_map or {}
        state = self.deps.state
        scale_out_tiers = self._scale_out_tiers()
        exits_processed = 0
        for cid in list(state.portfolio.positions.keys()):
            pos = state.portfolio.positions.get(cid)
            if pos is None:
                continue

            tick_position_state(pos)
            score_info = score_map.get(cid, {})
            # ESPN start time ile match_start_iso düzelt (card vs maç saati farkı)
            espn_start = score_info.get("espn_start", "")
            if espn_start and espn_start != pos.match_start_iso:
                pos.match_start_iso = espn_start
            # score_info'dan match_score/period fallback — enricher bu tick'te
            # çalışmadıysa (rate-limit) archive kaydı boş kalmasın.
            if score_info.get("available") and not pos.match_score:
                our = score_info.get("our_score")
                opp = score_info.get("opp_score")
                if our is not None and opp is not None:
                    pos.match_score = f"{our}-{opp}"
            if score_info.get("available") and not pos.match_period:
                pos.match_period = str(score_info.get("period", "") or "")
            result: MonitorResult = exit_monitor.evaluate(
                pos, score_info=score_info, scale_out_tiers=scale_out_tiers,
                sl_params=self._sl_params(),
                scale_out_min_realized_usd=self._scale_out_min_realized(),
                basketball_exit_cfg=self._basketball_exit_cfg(),
                scale_out_threshold=self._scale_out_threshold(),
            )
            self._apply_fav_transition(pos, result.fav_transition)

            if result.exit_signal is not None:
                self._execute_exit(pos, result.exit_signal, elapsed_pct=result.elapsed_pct)
                exits_processed += 1

        if exits_processed > 0:
            self.deps.cycle_manager.signal_exit_happened()

    def _sl_params(self) -> SLParams | None:
        """PLAN-014: config.sl → SLParams. SL disabled veya config yoksa None."""
        cfg = getattr(self.deps.state, "config", None)
        if cfg is None or not hasattr(cfg, "sl"):
            return None
        sl = cfg.sl
        if not getattr(sl, "enabled", False):
            return None
        return SLParams(
            enabled=True,
            price_below=sl.price_below,
            max_loss_usd=sl.max_loss_usd,
        )

    def _basketball_exit_cfg(self):
        """PLAN-NBA: exit_basketball config → BasketballExitConfig. None → monitor default."""
        cfg = getattr(self.deps.state, "config", None)
        if cfg is None or not hasattr(cfg, "exit_basketball"):
            return None
        return cfg.exit_basketball

    def _scale_out_min_realized(self) -> float:
        """PLAN-014b: scale-out min realized USD eşiği (config'den)."""
        cfg = getattr(self.deps.state, "config", None)
        if cfg and hasattr(cfg, "scale_out"):
            return float(getattr(cfg.scale_out, "min_realized_usd", 0.0))
        return 0.0

    def _scale_out_threshold(self) -> float:
        """Config'den scale-out price threshold."""
        cfg = getattr(self.deps.state, "config", None)
        if cfg and hasattr(cfg, "scale_out"):
            return float(getattr(cfg.scale_out, "price_threshold", 0.85))
        return 0.85

    def _scale_out_tiers(self) -> list[dict]:
        """Config'den scale-out tier listesini dict olarak döndür.

        Config path: deps.state.config (AgentDeps.state: RuntimeState; RuntimeState.config: AppConfig).
        """
        cfg = getattr(self.deps.state, "config", None)
        if cfg and hasattr(cfg, "scale_out"):
            return [
                {"threshold": t.threshold, "sell_pct": t.sell_pct}
                for t in cfg.scale_out.tiers
            ]
        return []

    def _apply_fav_transition(self, pos: Position, transition: FavoredTransition) -> None:
        if transition.promote and not pos.favored:
            pos.favored = True
            logger.info("FAV PROMOTED: %s", pos.slug[:40])
        elif transition.demote and pos.favored:
            pos.favored = False
            logger.info("FAV DEMOTED: %s", pos.slug[:40])

    def _execute_exit(self, pos: Position, signal: ExitSignal, elapsed_pct: float = -1.0) -> None:
        """Exit sinyalini execute et — full veya partial.

        Operasyon sırası: trade_logger (disk) → portfolio mutation (in-memory).
        Crash durumunda trade_history güncellenmişse orphan oluşmaz;
        pozisyon hâlâ portfolio'daysa sonraki cycle tekrar exit tetikler.
        """
        if signal.partial:
            self._execute_partial_exit(pos, signal, elapsed_pct)
            return

        self.deps.executor.exit_position(pos, reason=signal.reason.value)
        realized = pos.unrealized_pnl_usdc
        pnl_pct = realized / pos.size_usdc if pos.size_usdc > 0 else 0.0
        exit_price = pos.current_price

        # 1. Disk — trade_logger ÖNCE (crash-safe sıralama)
        exit_data = {
            "exit_price": exit_price,
            "exit_reason": signal.reason.value,
            "exit_pnl_usdc": round(realized, 2),
            "exit_pnl_pct": round(pnl_pct, 4),
            "exit_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if not self.deps.trade_logger.update_on_exit(pos.condition_id, exit_data):
            logger.warning("EXIT record missing for %s — writing fallback entry+exit", pos.slug[:35])
            self._write_fallback_entry(pos, exit_data)

        # Archive — SPEC-009 retrospektif analiz
        self._log_exit_to_archive(pos, signal, realized, exit_price, elapsed_pct)
        self._start_counterfactual(pos, signal.reason.value, exit_price)

        # 2. In-memory — portfolio mutation SONRA
        self.deps.state.portfolio.remove_position(pos.condition_id, realized_pnl_usdc=realized)
        self.deps.state.circuit_breaker.record_exit(pnl_usd=realized)
        self.deps.cooldown.record_outcome(win=(realized >= 0))

        if self.deps.price_feed is not None:
            self.deps.price_feed.unsubscribe([pos.token_id])

        logger.info("EXIT %s: reason=%s realized=$%.2f detail=%s",
                    pos.slug[:35], signal.reason.value, realized, signal.detail)

    def _execute_partial_exit(self, pos: Position, signal: ExitSignal, elapsed_pct: float = -1.0) -> None:
        """Scale-out partial exit.

        Operasyon sırası: hesapla → trade_logger (disk) → pos/portfolio mutation.
        Basis payı (`old_size × sell_pct`) pozisyon küçültülmeden ÖNCE yakalanır
        ve bankroll'a geri kredilenir — identity `bankroll + invested = initial +
        realized_pnl` korunur (TDD §5.7.7).
        """
        shares_to_sell = pos.shares * signal.sell_pct
        realized = pos.unrealized_pnl_usdc * signal.sell_pct
        basis_returned = pos.size_usdc * signal.sell_pct
        tier = signal.tier or pos.scale_out_tier

        # 1. Disk — trade_logger ÖNCE (crash-safe sıralama)
        partial_written = self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=pos.current_price,
        )
        if not partial_written:
            logger.warning("PARTIAL record missing for %s — writing fallback entry", pos.slug[:35])
            self._write_fallback_entry(pos, {})

        # 2. In-memory — pos + portfolio mutation SONRA
        pos.shares -= shares_to_sell
        pos.size_usdc *= (1 - signal.sell_pct)
        pos.scale_out_tier = tier
        pos.scaled_out_50 = True
        pos.scale_out_realized_usdc += realized
        self.deps.state.portfolio.apply_partial_exit(
            pos.condition_id,
            basis_returned_usdc=basis_returned,
            realized_usdc=realized,
        )
        self.deps.state.circuit_breaker.record_exit(pnl_usd=realized)
        logger.info(
            "SCALE-OUT %s: tier=%d sold=%.1f shares realized=$%.2f remaining=$%.2f",
            pos.slug[:35], signal.tier, shares_to_sell, realized, pos.size_usdc,
        )

        # Archive — SPEC-009
        self._log_exit_to_archive(pos, signal, realized, pos.current_price, elapsed_pct)

    def _log_exit_to_archive(
        self, pos: Position, signal: ExitSignal, realized: float,
        exit_price: float, elapsed_pct: float,
    ) -> None:
        """Exit'i arsive yaz — retrospektif analiz icin (SPEC-009)."""
        archive_logger = getattr(self.deps, "archive_logger", None)
        if archive_logger is None:
            return
        record = ArchiveExitRecord(
            slug=pos.slug,
            condition_id=pos.condition_id,
            event_id=getattr(pos, "event_id", "") or "",
            token_id=pos.token_id,
            sport_tag=pos.sport_tag,
            question=pos.question,
            direction=pos.direction,
            entry_price=pos.entry_price,
            entry_timestamp=str(getattr(pos, "entry_timestamp", "")),
            size_usdc=pos.size_usdc,
            shares=pos.shares,
            confidence=pos.confidence,
            anchor_probability=pos.anchor_probability,
            entry_reason=getattr(pos, "entry_reason", ""),
            exit_price=exit_price,
            exit_pnl_usdc=round(realized, 2),
            exit_reason=signal.reason.value,
            exit_timestamp=datetime.now(timezone.utc).isoformat(),
            partial_exits=list(getattr(pos, "partial_exits", [])),
            score_at_exit=pos.match_score or "",
            period_at_exit=pos.match_period or "",
            elapsed_pct_at_exit=elapsed_pct,
        )
        archive_logger.log_exit(record)

    def _start_counterfactual(self, pos: Position, exit_reason: str, exit_price: float) -> None:
        """Exit sonrası counterfactual tracking başlat (Seçenek B: light cycle)."""
        tracker = getattr(self.deps, "counterfactual_tracker", None)
        if tracker is None:
            return
        trade_id = pos.condition_id
        tracker.add(
            trade_id=trade_id,
            token_id=pos.token_id,
            exit_timestamp=datetime.now(timezone.utc).isoformat(),
            exit_price=exit_price,
            exit_reason=exit_reason,
        )

    def _write_fallback_entry(self, pos: Position, exit_data: dict) -> None:
        """Entry kaydı kayıpsa pozisyondan oluştur + varsa exit verisini ekle."""
        cat, league = _split_sport_tag(pos.sport_tag)
        record = TradeRecord(
            slug=pos.slug, condition_id=pos.condition_id,
            event_id=getattr(pos, "event_id", ""),
            token_id=pos.token_id, question=pos.question,
            sport_tag=pos.sport_tag, sport_category=cat, league=league,
            direction=pos.direction, entry_price=pos.entry_price,
            size_usdc=pos.size_usdc, shares=pos.shares,
            confidence=pos.confidence,
            bookmaker_prob=pos.anchor_probability,
            anchor_probability=pos.anchor_probability,
            entry_reason=getattr(pos, "entry_reason", ""),
            entry_timestamp=getattr(pos, "entry_timestamp", ""),
            **exit_data,
        )
        self.deps.trade_logger.log(record)
