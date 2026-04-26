"""Entry processor — heavy cycle entry flow (TDD §4).

Scanner → gate → cap-clip → execute → persist.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.config.sport_rules import _normalize
from src.domain.portfolio import snapshot as portfolio_snapshot
from src.domain.portfolio.exposure import available_under_cap
from src.infrastructure.persistence.trade_logger import TradeRecord, _split_sport_tag
from src.models.market import MarketData
from src.models.position import Position
from src.orchestration import operational_writers

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

        # Gamma scan'den gelen event_live flag'ini açık pozisyonlara yansıt
        # (Odds API maliyeti yok — Gamma ücretsiz).
        self._sync_live_flag(scan_fresh, scan_by_cid)

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
            # Fresh batch match_start ASC sıralı — stock batch ile tutarlı (TDD §F1.5).
            # Önceden scan-order kullanılıyordu: Gamma tennis event'leri önce çektiği
            # için fresh_batch'in ilk N'i tennis qualifier'larla dolup MLB/NHL kuyrukta
            # kalıyordu. Match_start sıralama en yakın maçlara öncelik verir.
            #
            # active_sports filtresi burada uygulanır: inactive sport'lar (soccer, tennis
            # vb.) Avrupa saatiyle erken başladığı için match_start ASC sıralamasında
            # üste çıkıp NBA/MLB gibi active sportları 150 sınırının dışına iter.
            active_normalized = {
                _normalize(s) for s in self.deps.gate.config.active_sports
            }
            fresh_only = [
                m for m in scan_fresh
                if not self.deps.stock.has(m.condition_id)
                and _normalize(m.sport_tag) in active_normalized
            ]
            fresh_only.sort(key=lambda m: m.match_start_iso or "9999-99-99")
            fresh_batch = fresh_only[: still_empty * jit_mult]
            if fresh_batch:
                logger.info("Heavy: fresh batch=%d (still_empty=%d × %d)",
                            len(fresh_batch), still_empty, jit_mult)
                self.process_markets(fresh_batch)

        self.deps.stock.save()
        operational_writers.log_equity_snapshot(self.deps.state.portfolio, self.deps.equity_logger)
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="idle")

    def _sync_live_flag(self, scan_fresh: list[MarketData], scan_by_cid: dict[str, MarketData]) -> None:
        """Gamma scan'den event_live/event_ended → açık pozisyon match_live/match_ended."""
        from collections import defaultdict
        by_event: dict[str, list[MarketData]] = defaultdict(list)
        for m in scan_fresh:
            if m.event_id:
                by_event[m.event_id].append(m)

        for pos in self.deps.state.portfolio.positions.values():
            market = scan_by_cid.get(pos.condition_id)
            if market is not None:
                if market.event_live != pos.match_live:
                    pos.match_live = market.event_live
                if market.event_ended != pos.match_ended:
                    pos.match_ended = market.event_ended

            if pos.event_id and pos.event_id in by_event:
                siblings = [m.yes_price for m in by_event[pos.event_id] if m.condition_id != pos.condition_id]
                pos.event_sibling_bids = siblings

    def process_markets(self, markets: list[MarketData]) -> None:
        """Gate → cap-clip → match_start ASC priority → execute."""
        mode = self.deps.state.config.mode.value
        self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="analyzing")
        results = self.deps.gate.run(markets)
        by_cid = {m.condition_id: m for m in markets}
        max_exposure_pct = self.deps.gate.config.max_exposure_pct
        overflow_pct = self.deps.gate.config.hard_cap_overflow_pct
        min_entry_pct = self.deps.gate.config.min_entry_size_pct
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

        for r in approved_sorted:
            market = by_cid.get(r.condition_id)
            if market is None:
                continue

            pm = self.deps.state.portfolio
            total_portfolio = pm.bankroll + pm.total_invested()
            available = available_under_cap(
                pm.positions, total_portfolio, max_exposure_pct, overflow_pct,
            )
            min_size = pm.bankroll * min_entry_pct
            if available < min_size:
                detail = f"available={available:.2f}, min={min_size:.2f}"
                operational_writers.log_skip(
                    self.deps.skipped_logger, market,
                    "exposure_cap_reached", detail=detail,
                )
                self.deps.stock.add(market, "exposure_cap_reached")
                continue

            final_size = min(r.signal.size_usdc, available)
            clipped_signal = r.signal.model_copy(update={"size_usdc": round(final_size, 2)})

            if not executing_written:
                self.deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="executing")
                executing_written = True
            self._execute_entry(market, clipped_signal)
            self.deps.stock.remove(market.condition_id)

    def _execute_entry(self, market: MarketData, signal) -> None:
        """Sim/live order → position open → trade record."""
        token_id = market.yes_token_id if signal.direction.value == "BUY_YES" else market.no_token_id
        side = "BUY"
        price = market.yes_price if signal.direction.value == "BUY_YES" else market.no_price
        order = self.deps.executor.place_order(
            token_id=token_id, side=side, price=price, size_usdc=signal.size_usdc,
            max_entry_price=self.deps.gate.config.max_entry_price,
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
            match_live=market.event_live,
            question=market.question,
            match_title=market.match_title,
            end_date_iso=market.end_date_iso,
            slug=market.slug,
            bookmaker_prob=signal.bookmaker_prob,
            sports_market_type=signal.sports_market_type,
            spread_line=signal.spread_line,
            total_line=signal.total_line,
            total_side=signal.total_side,
            home_away_side=signal.home_away_side,
        )

        if not self.deps.state.portfolio.add_position(pos):
            logger.warning(
                "BLOCKED add_position: %s (event=%s, cid=%s)",
                pos.slug[:35], pos.event_id, pos.condition_id[:16],
            )
            return

        # Immediate persist: crash sonrası event_guard tutarlılığı için
        # trade_logger'dan ÖNCE positions.json güncellenmeli — aksi halde
        # crash + restart'ta trade_history'de kayıt var ama positions'ta yok
        # → event_guard bypass edilir → duplicate entry (ARCH Kural 8).
        self.deps.state.positions_store.save(
            portfolio_snapshot.to_dict(self.deps.state.portfolio)
        )

        if self.deps.price_feed is not None:
            self.deps.price_feed.subscribe([token_id])

        category, league = _split_sport_tag(market.sport_tag)
        record = TradeRecord(
            slug=market.slug,
            condition_id=market.condition_id,
            event_id=market.event_id or "",
            token_id=pos.token_id,
            question=market.question,
            match_title=market.match_title,
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
