"""Entry processor — heavy cycle entry flow (DECISIONS §4).

Scanner → gate → cap-clip → execute → persist.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.portfolio.exposure import at_or_over_cap
from src.infrastructure.persistence.trade_logger import TradeRecord, _split_sport_tag
from src.models.market import MarketData
from src.models.position import Position
from src.models.signal import Signal
from src.orchestration import operational_writers
from src.orchestration.notifier_hooks import notify_entry_safe
from src.orchestration.entry_guards import (
    check_correlated_bet,
    check_duplicate_condition,
    check_exclude_combo,
    resolve_market_meta,
)
from src.orchestration.portfolio_guards import check_global_halts, check_per_market_guards
from src.orchestration.scanner import collect_model_signals

logger = logging.getLogger(__name__)


class EntryProcessor:
    """Heavy cycle entry: scan → stock → gate → clip → execute."""

    def __init__(self, deps) -> None:
        self.deps = deps

    def run_heavy(self) -> None:
        """Stock-first heavy cycle."""
        mode = self.deps.state.config.mode.value
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="scanning")

        scan_fresh = self.deps.scanner.scan()
        scan_by_cid = {m.condition_id: m for m in scan_fresh}

        # Model-anchor path (SPEC-R MLB submarket). Engine None ise no-op.
        model_markets, model_signals = collect_model_signals(
            candidates=scan_fresh, engine=self.deps.mlb_submarket_engine,
        )
        if model_markets:
            self.process_signals(markets=model_markets, signals=model_signals)
            # Model-path market'leri bookmaker akışından çıkar (çift trade yok)
            model_cids = {m.condition_id for m in model_markets}
            scan_fresh = [m for m in scan_fresh if m.condition_id not in model_cids]
            scan_by_cid = {m.condition_id: m for m in scan_fresh}

        open_event_ids = frozenset(
            p.event_id for p in self.deps.state.portfolio.positions.values() if p.event_id
        )
        self.deps.stock.refresh_from_scan(scan_by_cid)
        self.deps.stock.evict_expired(open_event_ids=open_event_ids)

        max_positions = self.deps.gate.config.max_positions
        empty_slots = max_positions - self.deps.state.portfolio.count()
        if empty_slots <= 0:
            self.deps.stock.save()
            operational_writers.log_equity_snapshot(self.deps.state.portfolio, self.deps.equity_logger)
            self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="idle")
            return

        jit_mult = self.deps.stock.config.jit_batch_multiplier

        stock_batch = self.deps.stock.top_n_by_match_start(empty_slots * jit_mult)
        if stock_batch:
            logger.info("Heavy: stock batch=%d (empty_slots=%d × %d)",
                        len(stock_batch), empty_slots, jit_mult)
            self.process_markets(stock_batch)

        still_empty = max_positions - self.deps.state.portfolio.count()
        if still_empty > 0:
            fresh_only = [m for m in scan_fresh if not self.deps.stock.has(m.condition_id)]
            fresh_batch = fresh_only[: still_empty * jit_mult]
            if fresh_batch:
                logger.info("Heavy: fresh batch=%d (still_empty=%d × %d)",
                            len(fresh_batch), still_empty, jit_mult)
                self.process_markets(fresh_batch)

        self.deps.stock.save()
        operational_writers.log_equity_snapshot(self.deps.state.portfolio, self.deps.equity_logger)
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="idle")

    def process_markets(self, markets: list[MarketData]) -> None:
        """Gate → soft-cap re-check (batch race) → match_start ASC priority → execute."""
        mode = self.deps.state.config.mode.value
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="analyzing")
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}
        max_exposure_pct = self.deps.gate.config.max_exposure_pct
        executing_written = False

        for r in results:
            if r.signal is not None:
                continue
            market = by_cid.get(r.condition_id)
            if market is not None:
                operational_writers.log_skip(
                    self.deps.skipped_logger, market,
                    r.skipped_reason, detail=r.skip_detail,
                )
                self.deps.stock.add(market, r.skipped_reason)

        def _priority_key(r):
            market = by_cid.get(r.condition_id)
            if market is None:
                return ("9999-99-99", 0.0)
            return (market.match_start_iso or "9999-99-99", -market.volume_24h)

        approved_sorted = sorted(
            [r for r in results if r.signal is not None],
            key=_priority_key,
        )

        max_per_event = self.deps.gate.config.max_positions_per_event

        for r in approved_sorted:
            market = by_cid.get(r.condition_id)
            if market is None:
                continue

            pm = self.deps.state.portfolio

            # Per-iteration event_count enforcement (batch race fix):
            # Gate evaluates event_count BEFORE any add_position runs, so N markets
            # of the same event can all pass. Here we re-check after each open,
            # ensuring max_positions_per_event is honored within a single batch.
            if market.event_id:
                event_count = pm.count_event(market.event_id)
                if event_count >= max_per_event:
                    detail = f"event_id={market.event_id} count={event_count}/{max_per_event}"
                    operational_writers.log_skip(
                        self.deps.skipped_logger, market,
                        "event_count_per_event_cap", detail=detail,
                    )
                    self.deps.stock.add(market, "event_count_per_event_cap")
                    continue

            # SPEC-P: yumuşak cap re-check (batch race fix).
            # Exposure ≥ cap → skip. Altındaysa tam sabit-tier boyutu girer (clipping yok).
            total_portfolio = pm.bankroll + pm.total_invested()
            if at_or_over_cap(pm.positions, total_portfolio, max_exposure_pct):
                invested = pm.total_invested()
                cap = total_portfolio * max_exposure_pct
                detail = f"invested={invested:.2f}, cap={cap:.2f}"
                operational_writers.log_skip(
                    self.deps.skipped_logger, market,
                    "exposure_cap_reached", detail=detail,
                )
                self.deps.stock.add(market, "exposure_cap_reached")
                continue

            if not executing_written:
                self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="executing")
                executing_written = True
            self._execute_entry(market, r.signal)
            self.deps.stock.remove(market.condition_id)

    def _execute_entry(self, market: MarketData, signal) -> None:
        """Sim/live order → position open → trade record.

        Pre-flight guards (entry_guards modülü):
          - duplicate_condition: 2026-05-30 KRİTİK fix — aynı condition_id wallet/defter çelişkisi
          - exclude_combo: 2026-05-31 negatif-EV kombinasyonları
          - correlated_bet: 2026-05-31 aynı event+market+direction (chain loss)
        """
        if check_duplicate_condition(self.deps, market):
            return
        if check_exclude_combo(self.deps, market, signal):
            return
        if check_correlated_bet(self.deps, market, signal):
            return

        token_id = market.yes_token_id if signal.direction.value == "BUY_YES" else market.no_token_id
        side = "BUY"
        price = market.yes_price if signal.direction.value == "BUY_YES" else market.no_price
        order = self.deps.executor.place_order(
            token_id=token_id, side=side, price=price, size_usdc=signal.size_usdc,
        )
        # 2026-05-29 (Phase 3 follow-up): tennis-paper-lab parity.
        # Paper mode gerçek fill simulator FILLED/PARTIAL_FILL döner (başarı).
        if order.get("status") not in ("simulated", "placed", "FILLED", "PARTIAL_FILL"):
            logger.warning("Order rejected: %s", order.get("reason", "?"))
            return

        fill_price = order.get("price", price)
        shares = signal.size_usdc / fill_price if fill_price > 0 else 0.0

        # NBA totals exit (SPEC-J) için total_line/total_side market.question'dan
        # parse edilip Position'a yazılır. Moneyline/spreads market'lerinde hepsi None kalır.
        sports_market_type, total_line, total_side = resolve_market_meta(market)

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
            match_live=market.event_live,
            question=market.question,
            end_date_iso=market.end_date_iso,
            slug=market.slug,
            bookmaker_prob=signal.bookmaker_prob,
            source=signal.source,
            sports_market_type=sports_market_type,
            total_line=total_line,
            total_side=total_side,
        )

        category, league = _split_sport_tag(market.sport_tag)
        record = TradeRecord(
            slug=market.slug,
            condition_id=market.condition_id,
            event_id=market.event_id or "",
            token_id=pos.token_id,
            question=market.question,
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
            source=signal.source,
            entry_reason=signal.entry_reason.value,
            entry_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if not self._persist_filled_position(pos, record):
            return

        if self.deps.price_feed is not None:
            self.deps.price_feed.subscribe([token_id])

    def process_signals(
        self,
        markets: list[MarketData],
        signals: list[Signal],
    ) -> None:
        """Model-anchor entry path (SPEC-R). Bookmaker bypass.

        Signal'lar zaten model'den gelir, edge ve direction belirlenmiştir.
        Bu metod sport-agnostic portfolio guard'larını çalıştırır ve geçen
        signal'lar için pozisyon açar. Bookmaker enrichment ve no_edge yok.

        Args:
            markets: Source market listesi.
            signals: Aynı sırada Signal listesi (markets[i] ↔ signals[i]).

        Raises:
            ValueError: markets ve signals uzunlukları farklıysa.
        """
        if len(markets) != len(signals):
            raise ValueError(
                f"process_signals: markets/signals length mismatch "
                f"({len(markets)} vs {len(signals)})"
            )
        if not markets:
            return

        global_skip = check_global_halts(
            breaker=self.deps.circuit_breaker,
            cooldown=self.deps.cooldown,
            portfolio=self.deps.state.portfolio,
            max_positions=self.deps.gate.config.max_positions,
        )
        if global_skip is not None:
            logger.info(
                "process_signals halted: %s (%s)",
                global_skip.reason, global_skip.detail,
            )
            return

        max_per_event = self.deps.gate.config.max_positions_per_event
        for market, signal in zip(markets, signals):
            per_market_skip = check_per_market_guards(
                market=market,
                portfolio=self.deps.state.portfolio,
                blacklist=self.deps.blacklist,
                max_positions_per_event=max_per_event,
            )
            if per_market_skip is not None:
                logger.info(
                    "process_signals skip %s: %s (%s)",
                    market.condition_id, per_market_skip.reason,
                    per_market_skip.detail,
                )
                continue

            result = self.deps.executor.execute(market, signal)
            if not getattr(result, "filled", False):
                logger.info(
                    "process_signals execute not filled: %s", market.condition_id,
                )
                continue

            self._persist_model_entry(market, signal, result)

    def _persist_model_entry(self, market: MarketData, signal: Signal, result) -> None:
        """Model-anchor entry sonrası pozisyon aç + trade kaydı yaz (SPEC-R)."""
        token_id = getattr(market, "token_id", "")
        fill_price = result.avg_price
        shares = result.size_usdc / fill_price if fill_price > 0 else 0.0

        pos = Position(
            condition_id=market.condition_id,
            token_id=token_id,
            direction=signal.direction.value,
            entry_price=fill_price,
            size_usdc=result.size_usdc,
            shares=shares,
            current_price=fill_price,
            anchor_probability=signal.anchor_probability,
            entry_reason=signal.entry_reason.value,
            confidence=signal.confidence,
            source=signal.source,
            sport_tag=signal.sport_tag,
            event_id=market.event_id or "",
            match_start_iso=getattr(market, "match_start_iso", "") or "",
            match_live=getattr(market, "event_live", False),
            question=market.question,
            end_date_iso=getattr(market, "end_date_iso", "") or "",
            slug=getattr(market, "slug", ""),
        )

        sport_category, league = _split_sport_tag(signal.sport_tag)
        record = TradeRecord(
            slug=getattr(market, "slug", ""),
            condition_id=market.condition_id,
            event_id=market.event_id or "",
            token_id=token_id,
            question=market.question,
            sport_tag=signal.sport_tag,
            sport_category=sport_category,
            league=league,
            direction=signal.direction.value,
            entry_price=fill_price,
            size_usdc=result.size_usdc,
            shares=shares,
            confidence=signal.confidence,
            bookmaker_prob=0.0,
            anchor_probability=signal.anchor_probability,
            num_bookmakers=0.0,
            has_sharp=False,
            source=signal.source,
            entry_reason=signal.entry_reason.value,
            entry_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._persist_filled_position(pos, record, blocked_label="model entry")

    def _persist_filled_position(
        self,
        position: Position,
        trade_record: TradeRecord,
        blocked_label: str = "",
    ) -> bool:
        """Pozisyonu portfolio'ya ekle + trade kaydını yaz (her entry path'inin ortak adımı).

        Returns:
            True → başarıyla eklendi; False → portfolio tarafından bloklandı.
        """
        if not self.deps.state.portfolio.add_position(position):
            label = f" ({blocked_label})" if blocked_label else ""
            logger.warning(
                "BLOCKED add_position%s: %s (event=%s, cid=%s)",
                label, position.slug[:35], position.event_id, position.condition_id[:16],
            )
            return False
        self.deps.trade_logger.log(trade_record)
        # SPEC-Z17: append-only event log (paralel yazım; Task 12'de legacy temizlenecek)
        if getattr(self.deps, "trade_event_log", None) is not None:
            self.deps.trade_event_log.append_entry(
                condition_id=trade_record.condition_id,
                slug=trade_record.slug,
                question=trade_record.question,
                sport_tag=trade_record.sport_tag,
                source=trade_record.source,
                direction=trade_record.direction,
                entry_price=trade_record.entry_price,
                entry_timestamp=trade_record.entry_timestamp,
                size_usdc=trade_record.size_usdc,
                shares=trade_record.shares,
                confidence=trade_record.confidence,
                bookmaker_prob=trade_record.bookmaker_prob,
                anchor_probability=trade_record.anchor_probability,
                num_bookmakers=trade_record.num_bookmakers,
                has_sharp=trade_record.has_sharp,
                entry_reason=trade_record.entry_reason,
            )
        notify_entry_safe(self.deps, position, trade_record)
        return True

# entry_guards.py'a taşındı (ARCH_GUARD §3 split) — geri uyumluluk re-export:
_resolve_market_meta = resolve_market_meta
