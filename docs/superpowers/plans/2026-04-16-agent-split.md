# Agent.py God Object Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `agent.py` (420 satır, 13 method) → 3 dosya, her biri <200 satır ve <10 method.

**Architecture:** Pure refactoring — composition split. Agent lifecycle'ı tutar, entry/exit flow'u delegate eder. Davranış değişikliği YOK. Mevcut testler aynen geçmeli.

**Tech Stack:** Python 3.12, dataclass, pytest.

**Spec:** [docs/superpowers/specs/2026-04-16-agent-split-design.md](../specs/2026-04-16-agent-split-design.md)

---

## File Structure

| Dosya | Rol | Tip |
|---|---|---|
| `src/orchestration/entry_processor.py` | Heavy cycle entry flow | Create |
| `src/orchestration/exit_processor.py` | Light cycle exit flow | Create |
| `src/orchestration/agent.py` | Lifecycle + delegation (slim) | Modify |
| `tests/unit/orchestration/test_agent.py` | Mevcut testler — import uyumu | Modify (gerekirse) |
| `tests/unit/orchestration/test_agent_heavy_stages.py` | Mevcut testler | Modify (gerekirse) |

---

## Task 1 — Create `entry_processor.py`

**Files:**
- Create: `src/orchestration/entry_processor.py`

- [ ] **Step 1.1 — Dosyayı oluştur**

`src/orchestration/entry_processor.py` — agent.py satır 134-328'den çıkarılır:

```python
"""Entry processor — heavy cycle entry flow (TDD §4).

Scanner → gate → cap-clip → execute → persist.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

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
                operational_writers.log_skip(self.deps.skipped_logger, market, r.skipped_reason)
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
                operational_writers.log_skip(self.deps.skipped_logger, market, "exposure_cap_reached")
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
            logger.warning(
                "BLOCKED add_position: %s (event=%s, cid=%s)",
                pos.slug[:35], pos.event_id, pos.condition_id[:16],
            )
            return

        if self.deps.price_feed is not None:
            self.deps.price_feed.subscribe([token_id])

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
            entry_reason=signal.entry_reason.value,
            entry_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.deps.trade_logger.log(record)
```

NOT: `_log_trade_entry` ayrı method yerine `_execute_entry` içine inline edildi (tek caller, DRY).

- [ ] **Step 1.2 — Commit**

```bash
git add src/orchestration/entry_processor.py
git commit -m "refactor: extract EntryProcessor from agent.py (heavy cycle)"
```

---

## Task 2 — Create `exit_processor.py`

**Files:**
- Create: `src/orchestration/exit_processor.py`

- [ ] **Step 2.1 — Dosyayı oluştur**

`src/orchestration/exit_processor.py` — agent.py satır 332-420'den çıkarılır:

```python
"""Exit processor — light cycle exit flow (TDD §4).

Pozisyon state tick + exit monitor → full/partial exit execute.
Agent bu class'ı composition ile kullanır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.portfolio.lifecycle import tick_position_state
from src.models.position import Position
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
        """Scale-out partial exit."""
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
```

- [ ] **Step 2.2 — Commit**

```bash
git add src/orchestration/exit_processor.py
git commit -m "refactor: extract ExitProcessor from agent.py (light cycle)"
```

---

## Task 3 — Slim down `agent.py` to lifecycle + delegation

**Files:**
- Modify: `src/orchestration/agent.py`

- [ ] **Step 3.1 — agent.py'yi yeniden yaz (sadece lifecycle)**

`src/orchestration/agent.py` tamamını şununla değiştir:

```python
"""Ana agent döngüsü — katmanları bağlayan orchestrator (TDD §4).

Heavy cycle: EntryProcessor'a delegate edilir.
Light cycle: ExitProcessor'a delegate edilir.

Bu dosya sadece lifecycle koordinasyonu yapar — iş mantığı
entry_processor/exit_processor + domain/strategy'de, I/O infrastructure'da.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.domain.risk.cooldown import CooldownTracker
from src.infrastructure.executor import Executor
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.skipped_trade_logger import SkippedTradeLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.infrastructure.websocket.price_feed import PriceFeed
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleManager
from src.orchestration.entry_processor import EntryProcessor
from src.orchestration.exit_processor import ExitProcessor
from src.orchestration.scanner import MarketScanner
from src.orchestration.startup import RuntimeState, persist
from src.orchestration.stock_queue import StockQueue
from src.strategy.entry.gate import EntryGate

logger = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    """Dependency injection container — test için mock'lanabilir."""
    state: RuntimeState
    scanner: MarketScanner
    cycle_manager: CycleManager
    executor: Executor
    odds_client: object
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
        self._entry = EntryProcessor(deps)
        self._exit = ExitProcessor(deps)
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
                    self._entry.run_heavy()
                if tick.run_light:
                    self._exit.run_light()
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

    def _start_ws_if_needed(self) -> None:
        if self._ws_started or self.deps.price_feed is None:
            return
        tokens = [p.token_id for p in self.deps.state.portfolio.positions.values() if p.token_id]
        if tokens:
            self.deps.price_feed.subscribe(tokens)
        self.deps.price_feed.start_background()
        self._ws_started = True

    def _on_price_update(self, token_id: str, yes_price: float, bid_price: float, _ts: float) -> None:
        try:
            self.deps.state.portfolio.update_position_price(token_id, yes_price, bid_price)
        except Exception as e:
            logger.error("WS price update error: %s", e)
```

- [ ] **Step 3.2 — Satır sayısı kontrolü**

```bash
wc -l src/orchestration/agent.py src/orchestration/entry_processor.py src/orchestration/exit_processor.py
```

Expected: agent ~110, entry ~180, exit ~100. Hepsi <400.

- [ ] **Step 3.3 — Commit**

```bash
git add src/orchestration/agent.py
git commit -m "refactor: slim agent.py to lifecycle — delegates to EntryProcessor + ExitProcessor"
```

---

## Task 4 — Fix tests

**Files:**
- Modify: `tests/unit/orchestration/test_agent.py` (gerekirse)
- Modify: `tests/unit/orchestration/test_agent_heavy_stages.py` (gerekirse)

- [ ] **Step 4.1 — Full test suite çalıştır**

```bash
pytest -q 2>&1 | tail -10
```

Olası sorunlar:
- Test'ler `Agent._process_markets` veya `Agent._run_heavy` gibi internal method'lara doğrudan erişiyorsa → artık `Agent._entry.process_markets` veya `Agent._entry.run_heavy` olmalı
- Mock'lar `agent._execute_entry` patch ediyorsa → `agent._entry._execute_entry` olmalı

- [ ] **Step 4.2 — Fail eden testleri düzelt**

Her fail:
1. Hatayı oku (AttributeError, ImportError vs)
2. Internal method referanslarını `_entry.X` veya `_exit.X` olarak güncelle
3. Import path'leri düzelt (eğer test doğrudan `from src.orchestration.agent import _process_markets` yapıyorsa)

- [ ] **Step 4.3 — Full suite tekrar**

```bash
pytest -q
```

Expected: 662/662 PASS.

- [ ] **Step 4.4 — God object + line count kontrolü**

```bash
echo "--- Satır sayıları ---"
wc -l src/orchestration/agent.py src/orchestration/entry_processor.py src/orchestration/exit_processor.py
echo "--- Method sayıları ---"
grep -cE "^    def " src/orchestration/agent.py src/orchestration/entry_processor.py src/orchestration/exit_processor.py
```

Expected: her dosya <400 satır, her class <10 method.

- [ ] **Step 4.5 — Commit**

```bash
git add -u tests/
git commit -m "test: update orchestration tests for agent split (entry/exit processor)"
```

---

## Self-Review

**Spec coverage:**
- ✓ Agent → lifecycle 5 method — Task 3
- ✓ EntryProcessor → heavy 4 method — Task 1
- ✓ ExitProcessor → light 5 method — Task 2
- ✓ _log_trade_entry inline into _execute_entry — Task 1
- ✓ AgentDeps unchanged — Task 3
- ✓ Existing tests pass — Task 4
- ✓ Line count < 400, method count < 10 — Task 4.4

**Placeholder scan:** Yok — tüm code blokları tam.

**Type consistency:** `deps` parametresi tüm class'larda `AgentDeps` tipi (duck-typed, `deps` olarak geçiyor). `EntryProcessor.run_heavy()` argümansız (eski `prefer_eligible_queue` kaldırıldı — agent.py'de zaten `del` ile siliniyor).

---

## Execution Handoff

Plan `docs/superpowers/plans/2026-04-16-agent-split.md`'e kaydedildi. Subagent-driven execution öneriyorum.
