"""EntryProcessor.process_signals helper — sport-agnostic portfolio guards.

Bookmaker enricher CALISMAZ. Caller (örn. tennis_agent) zaten Signal'i
sport-specific sizing'la üretir; burada yalnızca portfolio-level guard'lar
uygulanır, geçenler `_execute_entry` ile execute edilir.

Bu modül entry_processor.py'yi 400 satır limiti altında tutmak için
ayrıştırıldı (ARCH_GUARD Kural 3).

DRY-DEBT: see TODO-TENNIS-DRY — guard predikatları EntryGate._evaluate_one
ile birebir; gate.py refactor'ü olmadan kaldırılamadığı için duplicate.
"""
from __future__ import annotations

import logging
from typing import Callable

from src.domain.portfolio.exposure import available_under_cap
from src.models.market import MarketData
from src.models.position import effective_price
from src.models.signal import Signal
from src.orchestration import operational_writers

logger = logging.getLogger(__name__)


def process_signals(
    deps,
    markets: list[MarketData],
    signals: list[Signal],
    execute_entry: Callable[[MarketData, Signal], None],
) -> None:
    """Sport-agnostic portfolio guard akışı + execute.

    Guards (gate.py ile aynı predikatlar):
      Global (batch-level, hepsini atlar):
        1. circuit_breaker.halt_active
        2. cooldown.active
        3. portfolio.count >= max_positions
      Per-signal:
        4. event_count_per_event_cap
        5. blacklisted (condition_id veya event_id)
        6. manipulation_high_risk
        7. entry_price_cap (effective_price >= max_entry_price)
        8. exposure_cap_reached (available_under_cap < min_size)

    Args:
        deps: AgentDeps benzeri (state, gate, skipped_logger, bot_status_writer).
        markets: signals[i] sinyalinin türetildiği MarketData (parallel).
        signals: Sized Signal listesi (size_usdc dolu).
        execute_entry: (market, clipped_signal) -> None — caller'in
            `_execute_entry` private metodu.
    """
    if len(markets) != len(signals):
        raise ValueError(
            f"process_signals: markets/signals length mismatch "
            f"({len(markets)} vs {len(signals)})",
        )
    if not signals:
        return

    mode = deps.state.config.mode.value
    cfg = deps.gate.config
    pm = deps.state.portfolio

    # ── Global guards ──
    halt, reason = deps.gate.breaker.should_halt_entries()
    if halt:
        detail = reason[len("breaker: "):] if reason.startswith("breaker: ") else reason
        logger.info("process_signals halted: circuit_breaker (%s)", reason)
        for market in markets:
            operational_writers.log_skip(
                deps.skipped_logger, market, "circuit_breaker", detail=detail,
            )
        return

    if deps.gate.cooldown.is_active():
        remaining = deps.gate.cooldown.state.cooldown_remaining
        detail = f"cycles_remaining={remaining}"
        for market in markets:
            operational_writers.log_skip(
                deps.skipped_logger, market, "cooldown_active", detail=detail,
            )
        return

    count = pm.count()
    if count >= cfg.max_positions:
        detail = f"count={count}/{cfg.max_positions}"
        for market in markets:
            operational_writers.log_skip(
                deps.skipped_logger, market, "max_positions_reached", detail=detail,
            )
        return

    # ── Per-signal guards + execute ──
    executing_written = False
    deps.bot_status_writer.write_stage(mode=mode, cycle="heavy", stage="analyzing")

    for market, signal in zip(markets, signals):
        # 4. Event cap (per-iteration: batch race koruması)
        if market.event_id:
            event_count = pm.count_event(market.event_id)
            if event_count >= cfg.max_positions_per_event:
                detail = (
                    f"event_id={market.event_id} "
                    f"count={event_count}/{cfg.max_positions_per_event}"
                )
                operational_writers.log_skip(
                    deps.skipped_logger, market,
                    "event_count_per_event_cap", detail=detail,
                )
                continue

        # 4b. same_market_type per-event guard (correlation cap).
        # Tiered totals/handicaps on the same event are positively correlated
        # (Over 4.5 sets ⊂ Over 3.5 sets). Holding multiple ⇒ concentration,
        # not diversification (Wizard of Odds, correlated-parlay industry rule).
        # Applies to BOTH A and B — A-tier Grand Slam best-of-5 markets can
        # also stack tiers; this guard is logic-based, not data-tier-specific.
        if market.event_id:
            same_type_count = pm.count_event_market_type(
                market.event_id, market.sports_market_type or "",
            )
            if same_type_count >= 1:
                detail = (
                    f"event_id={market.event_id} "
                    f"market_type={market.sports_market_type} "
                    f"already_held={same_type_count}"
                )
                operational_writers.log_skip(
                    deps.skipped_logger, market,
                    "same_market_type_per_event", detail=detail,
                )
                continue

        # 5. Blacklist
        if deps.gate.blacklist.is_blacklisted(condition_id=market.condition_id):
            operational_writers.log_skip(
                deps.skipped_logger, market,
                "blacklisted", detail="match=condition_id",
            )
            continue
        if market.event_id and deps.gate.blacklist.is_blacklisted(event_id=market.event_id):
            operational_writers.log_skip(
                deps.skipped_logger, market,
                "blacklisted", detail="match=event_id",
            )
            continue

        # 6. Manipulation risk
        manip = deps.gate._manip_check(
            question=market.question,
            liquidity=market.liquidity,
        )
        if not manip.safe:
            manip_detail = ", ".join(manip.flags) if manip.flags else "unknown"
            operational_writers.log_skip(
                deps.skipped_logger, market,
                "manipulation_high_risk", detail=manip_detail,
            )
            continue

        # 7. Entry price cap
        entry_eff_price = effective_price(signal.market_price, signal.direction.value)
        if entry_eff_price >= cfg.max_entry_price:
            detail = f"price={entry_eff_price:.3f}, cap={cfg.max_entry_price}"
            operational_writers.log_skip(
                deps.skipped_logger, market,
                "entry_price_cap", detail=detail,
            )
            continue

        # 8. Exposure cap (per-signal — clipping de burada)
        total_portfolio = pm.bankroll + pm.total_invested()
        available = available_under_cap(
            pm.positions, total_portfolio,
            cfg.max_exposure_pct, cfg.hard_cap_overflow_pct,
        )
        min_size = pm.bankroll * cfg.min_entry_size_pct
        if available < min_size:
            detail = f"available={available:.2f}, min={min_size:.2f}"
            operational_writers.log_skip(
                deps.skipped_logger, market,
                "exposure_cap_reached", detail=detail,
            )
            continue

        final_size = min(signal.size_usdc, available)
        clipped_signal = signal.model_copy(update={"size_usdc": round(final_size, 2)})

        if not executing_written:
            deps.bot_status_writer.write_stage(
                mode=mode, cycle="heavy", stage="executing",
            )
            executing_written = True
        execute_entry(market, clipped_signal)

    if not executing_written:
        deps.bot_status_writer.write_stage(
            mode=mode, cycle="heavy", stage="idle",
        )
