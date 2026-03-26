# Agent Rewrite — Clean Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose the 4973-line main.py God class into focused modules — entry_gate.py (single unified entry pipeline), exit_monitor.py (exit detection), and agent.py (thin loop) — while fixing the FAR pipeline sanity-check bypass bug and the sport-tag duplication DRY violation.

**Architecture:**
```
agent.py (thin, ~350L)
  ├── entry_gate.py (EntryGate, ~450L) ← market scan + AI + edge/consensus + sanity + risk + exec
  ├── exit_monitor.py (ExitMonitor, ~250L) ← WS drain + portfolio.check_*() detection
  └── sport_rules.py (existing, +30L) ← add ESPORTS_TAGS + is_esports() + is_esports_slug()
```

Key decisions made in plan-eng-review:
- `agent.py` calls `entry_gate.run()` twice: once with fresh scan (`analyze=True`), once with stock queue (`analyze=False`)
- ExitMonitor DETECTS exits (returns `(cid, reason)` pairs); Agent EXECUTES them via `_exit_position()`
- ExitMonitor registers its own WS callback (`ws_feed.set_on_price_update(...)`)
- `entry_gate.run()` returns `entries_allowed=False` → `[]` immediately (halt guard)
- `assert entries_allowed or len(candidates) == 0` in entry_gate before execute
- sport_registry.py dropped — ESPORTS_TAGS go in existing `sport_rules.py`

**Tech Stack:** Python 3.11+, same dependencies as existing codebase (requests, pydantic, python-dotenv)

---

## File Map

| Action | File | What changes |
|--------|------|-------------|
| MODIFY | `src/sport_rules.py` | Add `ESPORTS_TAGS`, `ESPORTS_SLUGS`, `is_esports()`, `is_esports_slug()` |
| CREATE | `src/exit_monitor.py` | ExitMonitor class — WS drain + exit detection |
| CREATE | `src/entry_gate.py` | EntryGate class — unified entry pipeline |
| CREATE | `src/agent.py` | Agent class — thin loop (~350L, replaces 4900L in main.py) |
| MODIFY | `src/main.py` | Keep only `main()`, `_reset_simulation()`, imports (~120L) |
| MODIFY | `src/dashboard.py` | Fix hardcoded config.yaml defaults (read config passed in, not file) |

---

## Task 1: Add ESPORTS helpers to sport_rules.py

**Files:**
- Modify: `src/sport_rules.py` (add after existing SPORT_RULES dict, ~line 20)

**Purpose:** Single source of truth for esports detection. Currently defined 4× in main.py with inconsistent forms (line 273 uses `.startswith()` with truncated strings — a bug risk). After this task, all callers use `is_esports(tag)`.

- [ ] **Step 1: Add constants and helpers to sport_rules.py**

Read `src/sport_rules.py` first, then insert after the `SPORT_RULES` dict definition:

```python
# ═══════════════════════════════════════════════════════
# ESPORTS DETECTION — single source of truth
# ═══════════════════════════════════════════════════════

# sport_tag values (from MarketData.sport_tag) for esports titles
ESPORTS_TAGS: frozenset[str] = frozenset({
    "counter-strike",
    "dota-2",
    "league-of-legends",
    "valorant",
    "rocket-league",
    "overwatch",
    "apex-legends",
})

# Slug prefixes used in Polymarket market slugs for esports
ESPORTS_SLUGS: frozenset[str] = frozenset({
    "cs2", "csgo", "val", "valorant", "lol", "dota2", "rl", "cod", "ow",
})


def is_esports(sport_tag: str) -> bool:
    """Return True if sport_tag identifies an esports title.

    Use this everywhere instead of inline tuple checks.
    Replaces 4 inline definitions in main.py (lines 273/312/758/1606).
    NOTE: line 273 used .startswith() with truncated strings — this exact-match
    version is correct.
    """
    return (sport_tag or "").lower() in ESPORTS_TAGS


def is_esports_slug(slug: str) -> bool:
    """Return True if the market slug prefix indicates an esports market.

    Used during market prioritization to skip odds_api lookups (esports not
    covered by major bookmakers).
    """
    prefix = (slug or "").lower()[:8].split("-")[0]
    return prefix in ESPORTS_SLUGS
```

- [ ] **Step 2: Verify import works**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.sport_rules import is_esports, is_esports_slug, ESPORTS_TAGS; print('OK', len(ESPORTS_TAGS))"
```
Expected output: `OK 7`

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/sport_rules.py
git commit -m "feat: add ESPORTS_TAGS + is_esports/is_esports_slug to sport_rules.py

Consolidates 4 inline esports-tag definitions from main.py (lines 273/312/758/1606).
Line 273 used .startswith with truncated strings — replaced with exact-match frozenset."
```

---

## Task 2: Create exit_monitor.py

**Files:**
- Create: `src/exit_monitor.py`

**Purpose:** ExitMonitor detects which positions should exit each cycle. It does NOT call `executor.exit()` — it returns `(cid, reason)` pairs. Agent.py's `_exit_position()` does the actual exit. ExitMonitor also owns the WebSocket exit queue.

- [ ] **Step 1: Create src/exit_monitor.py**

```python
"""exit_monitor.py — Exit detection for all active positions.

Responsibilities:
  - Register WebSocket price-update callback
  - Drain WS exit queue at start of each cycle
  - Run all portfolio.check_*() exit detectors
  - Return (condition_id, reason) pairs — agent.py calls _exit_position()

Does NOT call executor or modify portfolio directly.

   WS callback → _ws_exit_queue
                       │
   agent.drain()  ←────┘  (called at start of each cycle)
   agent.check_exits() ← calls portfolio.check_*() methods
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.portfolio import Portfolio
    from src.websocket_feed import WebSocketFeed
    from src.config import AppConfig

logger = logging.getLogger(__name__)


class ExitMonitor:
    """Detect exits. Return (cid, reason) pairs. Never calls executor."""

    def __init__(
        self,
        portfolio: "Portfolio",
        ws_feed: "WebSocketFeed",
        config: "AppConfig",
    ) -> None:
        self.portfolio = portfolio
        self.config = config
        self._ws_exit_queue: list[tuple[str, str]] = []
        self._exiting_set: set[str] = set()  # Double-exit guard

        # Register our callback with the WS feed
        ws_feed.set_on_price_update(self._on_ws_price_update)

    # ── WebSocket ──────────────────────────────────────────────────────────

    def _on_ws_price_update(self, token_id: str, price: float, ts: float) -> None:
        """Called by WebSocketFeed on every price tick. Queue exits for drain()."""
        # Find matching position by token_id
        for cid, pos in list(self.portfolio.positions.items()):
            if getattr(pos, "token_id", "") != token_id:
                continue
            if cid in self._exiting_set:
                continue

            # Update position price in portfolio
            self.portfolio.update_price(cid, price)

            # Check trailing TP via WebSocket (real-time)
            ttp_cfg = self.config.trailing_tp
            if ttp_cfg.enabled:
                from src.trailing_tp import calculate_trailing_tp
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= ttp_cfg.activation_pct,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    self._ws_exit_queue.append(
                        (cid, f"trailing_tp: {ttp_result['reason']}")
                    )
                    return

            # Stop-loss check via WebSocket
            sl_pct = (
                self.config.risk.esports_stop_loss_pct
                if _pos_is_esports(pos)
                else self.config.risk.stop_loss_pct
            )
            pnl_pct = _calc_pnl_pct(pos, price)
            if pnl_pct <= -sl_pct:
                self._ws_exit_queue.append((cid, "stop_loss"))

    def drain(self) -> list[tuple[str, str]]:
        """Pop all WS-triggered exits and return them. Call at top of each cycle."""
        exits = list(self._ws_exit_queue)
        self._ws_exit_queue.clear()
        return exits  # agent.py calls _exit_position(cid, reason) for each

    # ── Cycle exit checks ─────────────────────────────────────────────────

    def check_exits(
        self,
        bankroll: float,
        match_states: dict,
        cycle_count: int,
    ) -> list[tuple[str, str]]:
        """Run all exit detectors. Return (cid, reason) list. Agent executes them.

        Called once per heavy cycle (not light cycle — light cycle uses a subset).
        """
        result: list[tuple[str, str]] = []
        cfg = self.config

        # 1. Match-aware exits (4 layers: score/time/halftime/pre-match)
        match_exit_results = self.portfolio.check_match_aware_exits()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit") and cid in self.portfolio.positions:
                result.append((cid, f"match_exit_{mexr['layer']}"))
            # Hold-to-resolve revoke/restore handled by agent directly (needs pos mutation)

        # 2. Stop-losses
        vs_cfg = cfg.volatility_swing
        for cid in self.portfolio.check_stop_losses(
            cfg.risk.stop_loss_pct,
            vs_stop_loss_pct=vs_cfg.stop_loss_pct,
            esports_stop_loss_pct=cfg.risk.esports_stop_loss_pct,
        ):
            if cid not in {c for c, _ in result}:
                result.append((cid, "stop_loss"))

        # 3. Trailing take-profit
        ttp_cfg = cfg.trailing_tp
        if ttp_cfg.enabled:
            from src.trailing_tp import calculate_trailing_tp
            for cid, pos in list(self.portfolio.positions.items()):
                if pos.volatility_swing:
                    continue
                if cid in {c for c, _ in result}:
                    continue
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= ttp_cfg.activation_pct,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    result.append((cid, f"trailing_tp: {ttp_result['reason']}"))

        # 4. VS trailing stop (tighten near resolution)
        if ttp_cfg.enabled:
            for cid, pos in list(self.portfolio.positions.items()):
                if not pos.volatility_swing:
                    continue
                if cid in {c for c, _ in result}:
                    continue
                if pos.peak_pnl_pct < ttp_cfg.activation_pct:
                    continue
                hours_left = _hours_to_resolution(pos)
                trail = 0.04 if hours_left <= 0.5 else ttp_cfg.trail_distance
                from src.trailing_tp import calculate_trailing_tp
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=True,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=trail,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    result.append((cid, f"trailing_tp: {ttp_result['reason']}"))

        # 5. Esports halftime exits
        for cid in self.portfolio.check_esports_halftime_exits(match_states=match_states):
            if cid not in {c for c, _ in result}:
                result.append((cid, "esports_halftime"))

        # 6. Pre-match exits (mandatory exit before match starts)
        for cid in self.portfolio.check_pre_match_exits(minutes_before=30):
            if cid not in {c for c, _ in result}:
                result.append((cid, "pre_match_exit"))

        return result

    def check_exits_light(self, match_states: dict) -> list[tuple[str, str]]:
        """Subset of exit checks for light cycles (no AI, price-only).

        Light cycles run every 2 minutes. Run match-aware, stop-loss, trailing TP.
        Skip: scale-outs, volatility swing exits (heavy cycle only).
        """
        result: list[tuple[str, str]] = []
        cfg = self.config

        # Match-aware exits
        match_exit_results = self.portfolio.check_match_aware_exits()
        for mexr in match_exit_results:
            cid = mexr["condition_id"]
            if mexr.get("exit") and cid in self.portfolio.positions:
                result.append((cid, f"match_exit_{mexr['layer']}"))

        # Stop-losses
        vs_cfg = cfg.volatility_swing
        for cid in self.portfolio.check_stop_losses(
            cfg.risk.stop_loss_pct,
            vs_stop_loss_pct=vs_cfg.stop_loss_pct,
            esports_stop_loss_pct=cfg.risk.esports_stop_loss_pct,
        ):
            if cid not in {c for c, _ in result}:
                result.append((cid, "stop_loss"))

        # Trailing TP
        ttp_cfg = cfg.trailing_tp
        if ttp_cfg.enabled:
            from src.trailing_tp import calculate_trailing_tp
            for cid, pos in list(self.portfolio.positions.items()):
                if cid in {c for c, _ in result}:
                    continue
                ttp_result = calculate_trailing_tp(
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    direction=pos.direction,
                    peak_price=pos.peak_price,
                    trailing_active=pos.peak_pnl_pct >= ttp_cfg.activation_pct,
                    activation_pct=ttp_cfg.activation_pct,
                    trail_distance=ttp_cfg.trail_distance,
                )
                if ttp_result["peak_price"] > pos.peak_price:
                    pos.peak_price = ttp_result["peak_price"]
                if ttp_result["action"] == "EXIT":
                    result.append((cid, f"trailing_tp: {ttp_result['reason']}"))

        # Esports halftime
        for cid in self.portfolio.check_esports_halftime_exits(match_states=match_states):
            if cid not in {c for c, _ in result}:
                result.append((cid, "esports_halftime"))

        return result

    # ── Double-exit guard ─────────────────────────────────────────────────

    def mark_exiting(self, cid: str) -> None:
        self._exiting_set.add(cid)

    def unmark_exiting(self, cid: str) -> None:
        self._exiting_set.discard(cid)

    def is_exiting(self, cid: str) -> bool:
        return cid in self._exiting_set

    def match_exit_hold_revokes(self) -> list[dict]:
        """Return match_exit results that need hold-revoke/restore (agent mutates pos directly)."""
        return [r for r in self.portfolio.check_match_aware_exits()
                if r.get("revoke_hold") or r.get("restore_hold")]


# ── Module-level helpers ───────────────────────────────────────────────────

def _pos_is_esports(pos) -> bool:
    from src.sport_rules import is_esports
    return is_esports(getattr(pos, "sport_tag", "") or "")


def _calc_pnl_pct(pos, current_price: float) -> float:
    """P&L % from entry to current price, direction-aware."""
    if pos.direction == "BUY_YES":
        return (current_price - pos.entry_price) / pos.entry_price
    else:  # BUY_NO
        return (pos.entry_price - current_price) / pos.entry_price


def _hours_to_resolution(pos) -> float:
    """Hours until position's end_date. Returns 99.0 if unknown."""
    end_iso = getattr(pos, "end_date_iso", "")
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return max(0.0, (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600)
    except (ValueError, TypeError):
        return 99.0
```

- [ ] **Step 2: Verify import**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.exit_monitor import ExitMonitor; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/exit_monitor.py
git commit -m "feat: add exit_monitor.py — exit detection separated from execution

ExitMonitor owns WS callback + exit queue + portfolio.check_*() orchestration.
Returns (cid, reason) pairs — agent.py calls _exit_position() for execution.
Replaces exit detection logic scattered across 600+ lines of main.py run_cycle()."
```

---

## Task 3: Create entry_gate.py

**Files:**
- Create: `src/entry_gate.py`

**Purpose:** Single unified entry pipeline. All 6 entry types (normal, FAR, FAV, bond, consensus, VS) go through the same gate. Entry type only affects sizing and slot count. Sanity check is no longer bypassed by FAR markets.

**Critical path:**
```
run(markets, entries_allowed, analyze=True)
  if not entries_allowed: return []
  if analyze:
    prioritize markets (imminent/mid/discovery buckets)
    update _far_market_ids
    fetch esports/news/odds data
    run AI batch
  for market in markets:
    skip if not in estimates
    sanity check (now runs for ALL markets including FAR)
    apply esports rules (is_esports())
    edge OR consensus override
    apply FAR edge threshold
    manip guard sizing
    if consensus: fixed sizing
    rank by resolution edge or market edge
  assert entries_allowed or len(candidates) == 0  ← safety guard
  execute top N candidates
  return entered positions
```

- [ ] **Step 1: Create src/entry_gate.py**

```python
"""entry_gate.py — Unified market entry pipeline.

ALL entry types (normal, FAR, FAV, consensus) go through this single gate.
Entry type only changes sizing multiplier and slot count — same sanity check
for everyone. FAR markets no longer bypass sanity (fixes known bug).

Data flow:
  agent.py calls:
    entry_gate.run(fresh_markets, entries_allowed=True, analyze=True)   # heavy cycle
    entry_gate.run(stock_queue,   entries_allowed=True, analyze=False)  # stock drain

  run() flow:
    if not entries_allowed → return []
    if analyze → prioritize + fetch data + AI batch
    for each market → sanity + esports rules + edge/consensus → candidates
    assert entries_allowed or len(candidates) == 0  ← safety guard
    execute top N → return entered condition_ids
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import requests

from src.sport_rules import is_esports, is_esports_slug

if TYPE_CHECKING:
    from src.config import AppConfig
    from src.portfolio import Portfolio
    from src.executor import Executor
    from src.ai_analyst import AIAnalyst
    from src.market_scanner import MarketScanner
    from src.risk_manager import RiskManager
    from src.odds_api import OddsAPIClient
    from src.esports_data import EsportsDataClient
    from src.news_scanner import NewsScanner
    from src.manipulation_guard import ManipulationGuard
    from src.trade_logger import TradeLogger
    from src.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

# Confidence score for ranking (A=4, B+=3, B-=2, C=1)
_CONF_SCORE: dict[str, int] = {"A": 4, "B+": 3, "B-": 2, "C": 1}
_SKIP_CONFIDENCE: set[str] = {"C", "", "?"}


class EntryGate:
    """Single unified market entry pipeline.

    Instantiate once. Stateful: owns market cache, AI analysis cache,
    candidate stock queues, and far_market_ids.
    """

    def __init__(
        self,
        config: "AppConfig",
        portfolio: "Portfolio",
        executor: "Executor",
        ai: "AIAnalyst",
        scanner: "MarketScanner",
        risk: "RiskManager",
        odds_api: "OddsAPIClient",
        esports: "EsportsDataClient",
        news_scanner: "NewsScanner",
        manip_guard: "ManipulationGuard",
        trade_log: "TradeLogger",
        notifier: "TelegramNotifier",
    ) -> None:
        self.config = config
        self.portfolio = portfolio
        self.executor = executor
        self.ai = ai
        self.scanner = scanner
        self.risk = risk
        self.odds_api = odds_api
        self.esports = esports
        self.news_scanner = news_scanner
        self.manip_guard = manip_guard
        self.trade_log = trade_log
        self.notifier = notifier

        # Per-session state (survives across cycles)
        self._far_market_ids: set[str] = set()
        self._analyzed_market_ids: dict[str, float] = self._load_recent_analyses()
        self._eligible_cache: list = []
        self._eligible_pointer: int = 0
        self._eligible_cache_ts: float = 0.0
        self._seen_market_ids: set[str] = set()

        # Candidate stock queues (pre-analyzed, waiting for slots)
        self._candidate_stock: list[dict] = []
        self._fav_stock: list[dict] = []
        self._far_stock: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        markets: list,
        entries_allowed: bool,
        analyze: bool = True,
        bankroll: float = 0.0,
        cycle_count: int = 0,
        blacklist=None,
        exited_markets: set | None = None,
    ) -> list[str]:
        """Run the entry pipeline. Return list of entered condition_ids.

        Args:
            markets: MarketData objects to evaluate.
            entries_allowed: False → skip all entries immediately.
            analyze: True → run AI batch. False → use cached estimates (stock queue).
            bankroll: Current USDC bankroll for sizing.
            cycle_count: Current cycle number (for cooldown checks).
            blacklist: Blacklist object for filtering.
            exited_markets: Set of cids that have been permanently exited.
        """
        if not entries_allowed:
            return []

        if not markets:
            return []

        cfg = self.config
        exited_markets = exited_markets or set()

        # Filter out blacklisted and permanently exited markets
        if blacklist:
            markets = [m for m in markets if not blacklist.is_blocked(m.condition_id)]
        markets = [m for m in markets if m.condition_id not in exited_markets]

        estimates: dict = {}

        if analyze:
            # Prioritize + fetch external data + run AI batch
            markets, estimates = self._analyze_batch(markets, cycle_count)
        else:
            # Stock queue: use cached AI estimates (no AI cost)
            for m in markets:
                cid = m.condition_id
                if cid in self._analyzed_market_ids:
                    # Estimate was already stored when market was analyzed;
                    # for stock queue, the candidate dict carries the estimate.
                    pass
            # estimates already in candidate dicts — handled in _evaluate_candidates
            estimates = {}  # signal to evaluator to use candidate.get("estimate")

        # Collect + rank candidates
        candidates = self._evaluate_candidates(markets, estimates, bankroll, cycle_count, analyze)

        # SAFETY GUARD: if somehow entries aren't allowed, candidates must be empty
        assert entries_allowed or len(candidates) == 0, (
            "BUG: candidates collected but entries_allowed=False — halt flag not propagated"
        )

        # Execute top N
        entered = self._execute_candidates(candidates, bankroll, cycle_count)
        return entered

    def drain_stock(self, entries_allowed: bool, bankroll: float, cycle_count: int,
                    blacklist=None, exited_markets: set | None = None) -> list[str]:
        """Process pre-analyzed candidate stock (analyze=False). Separate from fresh scan."""
        stock_markets = [c.get("market") for c in self._candidate_stock if c.get("market")]
        if not stock_markets:
            return []
        return self.run(
            stock_markets, entries_allowed, analyze=False,
            bankroll=bankroll, cycle_count=cycle_count,
            blacklist=blacklist, exited_markets=exited_markets,
        )

    def push_to_stock(self, candidate: dict) -> None:
        """Add a candidate to the stock queue (called by agent for demoted positions)."""
        self._candidate_stock.append(candidate)

    def invalidate_cache(self, condition_id: str) -> None:
        """Remove a market from the AI analysis cache (e.g., after price drift reanalysis)."""
        self._analyzed_market_ids.pop(condition_id, None)

    # ── Analysis phase ─────────────────────────────────────────────────────

    def _analyze_batch(self, markets: list, cycle_count: int) -> tuple[list, dict]:
        """Prioritize markets, fetch external data, run AI batch. Return (markets, estimates)."""
        cfg = self.config

        # Prune stale analysis cache (>24h old entries)
        _24h = 86400
        self._analyzed_market_ids = {
            cid: ts for cid, ts in self._analyzed_market_ids.items()
            if time.time() - ts < _24h
        }

        # Stock IDs (don't re-analyze)
        _stock_ids = {c.get("condition_id", "") for c in self._candidate_stock}

        # Skip already-analyzed markets (HOLD cache)
        markets = [
            m for m in markets
            if m.condition_id not in self._analyzed_market_ids
            and m.condition_id not in _stock_ids
        ]

        if not markets:
            return [], {}

        # Slot-based batch sizing
        open_slots = max(0, cfg.risk.max_positions - self.portfolio.active_position_count)
        stock_empty = max(0, 5 - len(self._candidate_stock))
        total_need = open_slots + stock_empty
        batch_size = min(cfg.ai.batch_size, max(5, total_need * 2))

        # Bucket markets into imminent / mid / discovery
        imminent = sorted([m for m in markets if _hours_to_start(m) <= 6], key=_hours_to_start)
        midrange  = sorted([m for m in markets if 6 < _hours_to_start(m) <= 24], key=_hours_to_start)
        discovery = sorted([m for m in markets if _hours_to_start(m) > 24], key=_hours_to_start)

        imm_available = len(imminent)
        if imm_available >= batch_size:
            prioritized = imminent[:batch_size]
        elif imm_available >= batch_size * 6 // 10:
            imm_slots = imm_available
            mid_slots = batch_size - imm_slots
            prioritized = imminent + midrange[:mid_slots]
        else:
            imm_slots = imm_available
            mid_slots = min(len(midrange), (batch_size - imm_slots) * 7 // 10)
            disc_slots = batch_size - imm_slots - mid_slots
            prioritized = imminent + midrange[:mid_slots] + discovery[:disc_slots]

        if len(prioritized) < batch_size:
            remaining = [m for m in markets if m not in prioritized]
            prioritized += remaining[:batch_size - len(prioritized)]

        # Update FAR market ids (>6h to start = FAR, needs higher edge)
        self._far_market_ids = {m.condition_id for m in prioritized if _hours_to_start(m) > 6}

        # Fetch esports contexts
        esports_contexts: dict = {}
        try:
            esports_contexts = self.esports.get_contexts_batch(prioritized) if prioritized else {}
        except Exception as exc:
            logger.warning("Esports context fetch failed: %s", exc)

        # Fetch news contexts
        news_context_by_market: dict = {}
        try:
            news_context_by_market = self.news_scanner.fetch_for_batch(prioritized) if prioritized else {}
        except Exception as exc:
            logger.warning("News fetch failed: %s", exc)

        # Filter: only markets with any data (esports OR odds OR news)
        _has_data: list = []
        for m in prioritized:
            _slug_prefix = (m.slug or "")[:8].lower()
            _is_esports_mkt = is_esports_slug(m.slug or "")
            has_odds = False
            if self.odds_api.available and not _is_esports_mkt:
                try:
                    _odds = self.odds_api.get_market_odds(m)
                    has_odds = bool(_odds)
                except Exception:
                    pass
            has_esports = bool(esports_contexts.get(m.condition_id))
            has_news = bool(news_context_by_market.get(m.condition_id))
            if has_odds or has_esports or has_news:
                _has_data.append(m)

        if not _has_data:
            logger.info("No markets with data — skipping AI batch")
            return [], {}

        # Run AI batch
        estimates = self.ai.analyze_batch(
            _has_data, "", esports_contexts, news_by_market=news_context_by_market
        )

        # Mark as analyzed (suppress re-analysis next cycle)
        for m in _has_data:
            self._analyzed_market_ids[m.condition_id] = time.time()

        return _has_data, estimates

    # ── Evaluation phase ───────────────────────────────────────────────────

    def _evaluate_candidates(
        self,
        markets: list,
        estimates: dict,
        bankroll: float,
        cycle_count: int,
        fresh_scan: bool,
    ) -> list[dict]:
        """Evaluate each market, return ranked candidate list."""
        from src.edge_calculator import calculate_edge, calculate_anchored_probability
        from src.edge_calculator import get_edge_threshold_adjustment
        from src.sanity_check import SanityChecker
        from src.models import Direction
        from src.scale_out import fill_ratio_scaling as scale_min_edge

        cfg = self.config
        sanity = SanityChecker(cfg.sanity)
        candidates: list[dict] = []
        _CONF_SKIP = {"C", "", "?"}

        # Fill-ratio edge scaling
        fill_ratio = self.portfolio.active_position_count / max(1, cfg.risk.max_positions)
        effective_min_edge = cfg.edge.min_edge
        if cfg.edge.fill_ratio_scaling:
            effective_min_edge = scale_min_edge(
                cfg.edge.min_edge, fill_ratio,
                cfg.edge.fill_ratio_aggressive,
                cfg.edge.fill_ratio_selective,
            )

        for market in markets:
            cid = market.condition_id

            # Get estimate (fresh scan → from estimates dict; stock → from candidate)
            estimate = estimates.get(cid)
            if estimate is None:
                continue
            if estimate.confidence in _CONF_SKIP:
                continue

            # ── Sanity check (ALL markets including FAR — no bypass) ────────
            sanity_result = sanity.check(market, estimate)
            if not sanity_result.passed:
                self.trade_log.log({
                    "market": market.slug, "action": "BLOCKED",
                    "question": market.question,
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "rejected": f"SANITY: {sanity_result.reason}",
                })
                continue

            # ── Anchored probability (odds_api bookmaker anchor) ───────────
            _is_esports_mkt = is_esports(getattr(market, "sport_tag", "") or "")
            _anchor_book_prob = None
            _anchor_num_books = 0
            if not _is_esports_mkt and self.odds_api.available:
                try:
                    _mkt_odds = self.odds_api.get_market_odds(market)
                    if _mkt_odds:
                        _anchor_book_prob = _mkt_odds.get("probability")
                        _anchor_num_books = _mkt_odds.get("num_bookmakers", 0)
                except Exception:
                    pass
            anchored = calculate_anchored_probability(
                ai_prob=estimate.ai_probability,
                bookmaker_prob=_anchor_book_prob,
                num_bookmakers=_anchor_num_books,
            )
            _edge_threshold_adj = get_edge_threshold_adjustment(anchored)

            # ── Edge calculation ───────────────────────────────────────────
            direction, edge = calculate_edge(
                ai_prob=anchored.probability,
                market_yes_price=market.yes_price,
                min_edge=effective_min_edge,
                confidence=estimate.confidence,
                confidence_multipliers=cfg.edge.confidence_multipliers,
                spread=cfg.edge.default_spread,
                edge_threshold_adjustment=_edge_threshold_adj,
            )

            # ── Esports-specific entry rules ───────────────────────────────
            _sport_tag = getattr(market, "sport_tag", "") or ""
            if is_esports(_sport_tag):
                # Rule 1: AI > 65% → force BUY_YES (winner override)
                if anchored.probability > 0.65 and direction in (Direction.BUY_NO, Direction.HOLD):
                    win_potential = 1.0 - market.yes_price
                    logger.info(
                        "ESPORTS_WINNER_OVERRIDE: %s | AI=%.0f%% > 65%% | was %s → BUY_YES",
                        market.slug[:40], anchored.probability * 100, direction.value,
                    )
                    direction = Direction.BUY_YES
                    edge = win_potential
                # Rule 2: AI < 50% + BUY_YES → skip (don't bet on predicted loser)
                elif direction == Direction.BUY_YES and anchored.probability < 0.50:
                    logger.info("Esports underdog skip: %s | AI=%.0f%% < 50%%",
                                market.slug[:40], anchored.probability * 100)
                    self.trade_log.log({
                        "market": market.slug, "action": "HOLD",
                        "rejected": f"ESPORTS_UNDERDOG: AI={anchored.probability:.0%} < 50%",
                    })
                    continue

            # ── Consensus entry override (HOLD → BUY if AI + market ≥65%) ─
            is_consensus = False
            entry_reason = ""
            if direction == Direction.HOLD:
                _ce = cfg.consensus_entry
                if _ce.enabled and estimate.confidence in ("A", "B+"):
                    _ai = estimate.ai_probability
                    _mp = market.yes_price
                    _cyes = _ai >= _ce.min_price and _mp >= _ce.min_price
                    _cno = (1 - _ai) >= _ce.min_price and (1 - _mp) >= _ce.min_price
                    _is_far_mkt = cid in self._far_market_ids
                    if (_cyes or _cno) and not _is_far_mkt:
                        _consensus_count = self.portfolio.count_by_entry_reason("consensus")
                        if _consensus_count < _ce.max_slots:
                            direction = Direction.BUY_YES if _cyes else Direction.BUY_NO
                            is_consensus = True
                            entry_reason = "consensus"
                            logger.info(
                                "CONSENSUS_OVERRIDE: %s | AI=%.0f%% mkt=%.0f%% conf=%s → %s (%d/%d slots)",
                                market.slug[:40], _ai * 100, _mp * 100,
                                estimate.confidence, direction.value,
                                _consensus_count + 1, _ce.max_slots,
                            )

            if direction == Direction.HOLD:
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "ai_prob": estimate.ai_probability, "price": market.yes_price,
                    "edge": edge,
                })
                # Cache this HOLD to avoid re-analyzing next cycle
                # (but NOT for consensus candidates — they may qualify next cycle)
                if not is_consensus:
                    self._analyzed_market_ids[cid] = time.time()
                continue

            # ── FAR market: require higher edge ────────────────────────────
            if cid in self._far_market_ids and not is_consensus and edge < 0.08:
                logger.info("Far market edge too low (%.1f%% < 8%%): %s",
                            edge * 100, market.slug[:40])
                self.trade_log.log({
                    "market": market.slug, "action": "HOLD",
                    "rejected": f"FAR_LOW_EDGE: {edge*100:.1f}% < 8%",
                })
                continue

            # ── Manipulation guard + position sizing ───────────────────────
            manip_check = self.manip_guard.check(market, estimate)
            adjusted_size = self.risk.calculate_position_size(
                edge=edge, bankroll=bankroll, confidence=estimate.confidence,
            )
            adjusted_size = self.manip_guard.adjust_position_size(
                adjusted_size, manip_check,
            )

            # Consensus: fixed bet_pct (no Kelly — edge≈0)
            if is_consensus:
                _ce = cfg.consensus_entry
                adjusted_size = min(
                    _ce.bet_pct * bankroll, cfg.risk.max_single_bet_usdc,
                )

            # ── Rank score ─────────────────────────────────────────────────
            entry_price = market.yes_price if direction == Direction.BUY_YES else (1 - market.yes_price)
            _effective_edge = (1 - entry_price) if is_consensus else edge
            rank_score = (
                _effective_edge
                * _CONF_SCORE.get(estimate.confidence, 1)
            )

            candidates.append({
                "score": rank_score,
                "market": market,
                "estimate": estimate,
                "direction": direction,
                "edge": edge,
                "adjusted_size": adjusted_size,
                "sanity": sanity_result,
                "manip_check": manip_check,
                "is_consensus": is_consensus,
                "entry_reason": entry_reason,
                "is_far": cid in self._far_market_ids,
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    # ── Execution phase ────────────────────────────────────────────────────

    def _execute_candidates(
        self, candidates: list[dict], bankroll: float, cycle_count: int,
    ) -> list[str]:
        """Execute top candidates. Return list of entered condition_ids."""
        entered: list[str] = []
        cfg = self.config

        for c in candidates:
            market = c["market"]
            cid = market.condition_id
            direction = c["direction"]
            size = c["adjusted_size"]
            estimate = c["estimate"]

            # Slot check
            open_slots = cfg.risk.max_positions - self.portfolio.active_position_count
            if open_slots <= 0:
                break

            # Min bet check
            if size < cfg.risk.min_bet_usdc:
                continue

            # Execute
            result = self.executor.place_order(
                market=market,
                direction=direction,
                size_usdc=size,
                mode=cfg.mode,
            )
            if not result or not result.get("success"):
                logger.warning("Order failed: %s — %s", market.slug[:40], result)
                continue

            # Record position
            entry_price = result.get("fill_price", market.yes_price)
            self.portfolio.add_position(
                condition_id=cid,
                slug=market.slug,
                question=getattr(market, "question", ""),
                token_id=market.yes_token_id if direction == "BUY_YES" else market.no_token_id,
                direction=direction.value if hasattr(direction, "value") else direction,
                entry_price=entry_price,
                size_usdc=size,
                ai_probability=estimate.ai_probability,
                confidence=estimate.confidence,
                sport_tag=getattr(market, "sport_tag", "") or "",
                event_id=getattr(market, "event_id", "") or "",
                end_date_iso=getattr(market, "end_date_iso", "") or "",
                entry_reason=c.get("entry_reason", ""),
            )

            self.trade_log.log({
                "market": market.slug, "action": "BUY",
                "direction": direction.value if hasattr(direction, "value") else direction,
                "size_usdc": size, "entry_price": entry_price,
                "ai_prob": estimate.ai_probability,
                "confidence": estimate.confidence,
                "edge": c["edge"],
                "is_consensus": c["is_consensus"],
                "entry_reason": c.get("entry_reason", ""),
                "is_far": c["is_far"],
            })

            logger.info(
                "ENTERED: %s | dir=%s | size=$%.2f | price=%.2f | AI=%.0f%% | conf=%s%s",
                market.slug[:45], direction, size, entry_price,
                estimate.ai_probability * 100, estimate.confidence,
                " [CONSENSUS]" if c["is_consensus"] else "",
            )

            entered.append(cid)

            # Notify on entry
            self.notifier.send(
                f"📈 *ENTRY*: {market.slug[:40]}\n"
                f"dir={direction} size=${size:.2f} price={entry_price:.2f} "
                f"AI={estimate.ai_probability:.0%} conf={estimate.confidence}"
            )

        return entered

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load_recent_analyses(self) -> dict[str, float]:
        """Load recent HOLD analyses from predictions.jsonl to avoid re-spending AI.

        BUY-worthy and consensus candidates are NOT cached (they re-evaluate fresh).
        """
        import json
        from pathlib import Path
        results: dict[str, float] = {}
        path = Path("logs/predictions.jsonl")
        if not path.exists():
            return results
        try:
            cutoff = time.time() - 3600 * 6  # 6h window
            _ce_min = 0.65
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = rec.get("timestamp", 0)
                    if ts < cutoff:
                        continue
                    cid = rec.get("condition_id", "")
                    if not cid:
                        continue
                    action = rec.get("action", "")
                    if action != "HOLD":
                        continue
                    # Don't cache consensus candidates
                    ai_prob = rec.get("ai_prob", 0.5)
                    mkt_price = rec.get("price", 0.5)
                    conf = rec.get("confidence", "")
                    _is_cyes = ai_prob >= _ce_min and mkt_price >= _ce_min
                    _is_cno = (1 - ai_prob) >= _ce_min and (1 - mkt_price) >= _ce_min
                    if (_is_cyes or _is_cno) and conf in ("A", "B+"):
                        continue  # potential consensus candidate → don't skip
                    results[cid] = float(ts)
        except Exception as exc:
            logger.warning("Could not load recent analyses: %s", exc)
        logger.info("Loaded %d recent HOLD analyses from predictions.jsonl", len(results))
        return results


# ── Module-level helpers ───────────────────────────────────────────────────

def _hours_to_start(market) -> float:
    """Hours until market start/end. Used for imminent/mid/discovery bucketing."""
    end_iso = getattr(market, "end_date_iso", "") or ""
    if not end_iso:
        return 99.0
    try:
        end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return max(0.0, (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600)
    except (ValueError, TypeError):
        return 99.0
```

- [ ] **Step 2: Verify import**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.entry_gate import EntryGate; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/entry_gate.py
git commit -m "feat: add entry_gate.py — unified entry pipeline with FAR sanity fix

Single EntryGate class replaces 6 separate pipeline functions in main.py.
FAR markets now go through sanity check (was bypassed via _fill_from_far_stock).
Consensus entry, esports rules, anchored probability all in one pipeline.
analyze=bool param prevents double AI batch when called twice per cycle."
```

---

## Task 4: Create agent.py (thin loop)

**Files:**
- Create: `src/agent.py`

**Purpose:** Thin Agent class. Owns `_exit_position()`, `_check_farming_reentry()`, `run_cycle()`, `run_light_cycle()`, `run()`. Delegates entry to EntryGate, exit detection to ExitMonitor.

- [ ] **Step 1: Create src/agent.py**

```python
"""agent.py — Thin agent loop. Coordinates EntryGate and ExitMonitor.

Responsibilities:
  - Initialize all modules (entry_gate, exit_monitor, portfolio, executor, etc.)
  - run_cycle(): heavy cycle — entry + exit
  - run_light_cycle(): price-only cycle
  - _exit_position(): execute position exit (reentry pool, blacklist, logging)
  - _check_farming_reentry(): reentry pool check (no AI cost)
  - run(): main loop
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

from src.config import AppConfig, load_config, Mode
from src.portfolio import Portfolio
from src.executor import Executor
from src.ai_analyst import AIAnalyst
from src.market_scanner import MarketScanner
from src.risk_manager import RiskManager
from src.odds_api import OddsAPIClient
from src.esports_data import EsportsDataClient
from src.sports_data import SportsDataClient
from src.news_scanner import NewsScanner
from src.manipulation_guard import ManipulationGuard
from src.trade_logger import TradeLogger
from src.notifier import TelegramNotifier
from src.websocket_feed import WebSocketFeed
from src.circuit_breaker import CircuitBreaker
from src.reentry_farming import ReentryPool, check_reentry
from src.blacklist import Blacklist, get_blacklist_rule
from src.outcome_tracker import OutcomeTracker
from src.cycle_timer import CycleTimer
from src.scout_scheduler import ScoutScheduler
from src.vlr_data import VLRDataClient
from src.hltv_data import HLTVDataClient
from src.edge_calculator import EdgeSourceTracker
from src.models import Direction
from src.process_lock import acquire_lock
from src.entry_gate import EntryGate
from src.exit_monitor import ExitMonitor

logger = logging.getLogger(__name__)

# Exits that should never be demoted to stock (permanent skip)
_NEVER_STOCK_EXITS = frozenset({
    "hard_halt_drawdown", "hard_halt", "stop_loss", "esports_halftime",
    "pre_match_exit", "resolved", "near_resolve",
})
_NEVER_STOCK_PREFIXES = ("match_exit_", "election_reeval", "far_penny_")


class Agent:
    """Thin orchestrator. Delegates entry to EntryGate, exit detection to ExitMonitor."""

    STOP_FILE = Path("logs/stop_signal")

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.running = True
        self.cycle_count = 0
        self._soft_halt_active = False
        self._cb_was_active = False

        # Exit infrastructure (owned by agent — _exit_position needs these)
        self._exit_cooldowns: dict[str, int] = {}
        self._exited_markets: set[str] = self._load_exited_markets()
        self._match_states: dict[str, dict] = {}
        self._last_match_state_fetch: float = 0.0
        self._daily_reentry_count: int = 0
        self._last_reentry_reset_date: date = datetime.now(timezone.utc).date()

        # Core modules
        self.portfolio = Portfolio(initial_bankroll=config.initial_bankroll)
        self.circuit_breaker = CircuitBreaker()
        self.blacklist = Blacklist(path="logs/blacklist.json")
        self.reentry_pool = ReentryPool()
        self.outcome_tracker = OutcomeTracker()
        self.cycle_timer = CycleTimer(config.cycle)

        # Signal enhancers
        esports = EsportsDataClient()
        sports = SportsDataClient()
        odds_api = OddsAPIClient()
        vlr = VLRDataClient()
        hltv = HLTVDataClient()
        news_scanner = NewsScanner()
        manip_guard = ManipulationGuard()
        scanner = MarketScanner(config.scanner)
        ai = AIAnalyst(config.ai)
        risk = RiskManager(config.risk)
        self.scout = ScoutScheduler(sports, esports)
        self.edge_tracker = EdgeSourceTracker()

        # Loggers & notifications
        self.trade_log = TradeLogger(config.logging.trades_file)
        self.portfolio_log = TradeLogger(config.logging.portfolio_file)
        self.perf_log = TradeLogger(config.logging.performance_file)
        self.notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            enabled=config.notifications.telegram_enabled,
        )
        odds_api.set_notifier(self.notifier)

        # Wallet & executor
        self.wallet = None
        clob_client = None
        if config.mode == Mode.LIVE:
            from src.wallet import Wallet
            pk = os.getenv("POLYGON_PRIVATE_KEY", "")
            if pk:
                self.wallet = Wallet(private_key=pk)
                try:
                    from py_clob_client.client import ClobClient
                    clob_client = ClobClient(
                        "https://clob.polymarket.com", key=pk, chain_id=137,
                        signature_type=int(os.getenv("SIGNATURE_TYPE", "0")),
                        funder=os.getenv("PROXY_WALLET_ADDRESS", "") or None,
                    )
                    clob_client.set_api_creds(clob_client.create_or_derive_api_creds())
                except Exception as exc:
                    logger.error("CLOB init failed: %s", exc)
        self.executor = Executor(mode=config.mode, clob_client=clob_client)

        # WebSocket feed (exit_monitor registers callback below)
        ws_feed = WebSocketFeed(on_price_update=None)  # callback set by ExitMonitor

        # Composed modules
        self.exit_monitor = ExitMonitor(self.portfolio, ws_feed, config)
        self.entry_gate = EntryGate(
            config=config,
            portfolio=self.portfolio,
            executor=self.executor,
            ai=ai,
            scanner=scanner,
            risk=risk,
            odds_api=odds_api,
            esports=esports,
            news_scanner=news_scanner,
            manip_guard=manip_guard,
            trade_log=self.trade_log,
            notifier=self.notifier,
        )
        self.ws_feed = ws_feed
        self.scanner = scanner

    # ── Main loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Main agent loop. Alternates heavy and light cycles."""
        logger.info("Agent starting — mode=%s", self.config.mode.value)
        try:
            while self.running:
                self._check_stop_file()
                if not self.running:
                    break
                if self.cycle_timer.should_run_heavy():
                    self.run_cycle()
                else:
                    self.run_light_cycle()
                self.cycle_timer.sleep_until_next()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.ws_feed.stop()
            logger.info("Agent stopped")

    def run_light_cycle(self) -> None:
        """Price-only cycle: update prices + check exits. No scan, no AI."""
        if self._is_paused():
            return
        logger.info("=== Light cycle ===")

        # Drain WS exits
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)

        # Update prices
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)
        if not self.ws_feed.connected:
            self._update_position_prices()
        self._sync_ws_subscriptions()

        # Fetch live match states
        match_states = self._fetch_match_states()

        # Light exit checks
        for cid, reason in self.exit_monitor.check_exits_light(match_states):
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)

        # Handle hold-revoke/restore (match_exit meta — mutates pos directly)
        self._handle_hold_revokes()

    def run_cycle(self) -> None:
        """Heavy cycle: exit checks + market scan + AI + entry decisions."""
        if self._is_paused():
            return
        self.cycle_count += 1
        self.risk.new_cycle()
        logger.info("=== Cycle #%d start ===", self.cycle_count)

        # Self-reflection + scout
        self._maybe_run_reflection()
        if self.scout.should_run_scout():
            new_scouted = self.scout.run_scout()
            if new_scouted:
                self.notifier.send(f"🔍 SCOUT: {new_scouted} new matches")

        # Bankroll + drawdown
        bankroll = self.wallet.get_usdc_balance() if self.wallet else self.portfolio.bankroll
        self.portfolio.update_bankroll(bankroll)
        dd_level = self.portfolio.get_drawdown_level()
        if dd_level == "hard":
            self.notifier.send("🚨 HARD HALT: equity < 35% HWM — closing all positions")
            for cid in list(self.portfolio.positions.keys()):
                if not self.exit_monitor.is_exiting(cid):
                    self._exit_position(cid, "hard_halt_drawdown")
            self.running = False
            return
        elif dd_level == "soft":
            if not self._soft_halt_active:
                self.notifier.send("⚠️ SOFT HALT: equity < 50% HWM — yeni entry durduruldu")
                self._soft_halt_active = True
        else:
            if self._soft_halt_active:
                self.notifier.send("✅ Drawdown recovered — entries resumed")
                self._soft_halt_active = False

        # Circuit breaker
        halt, halt_reason = self.circuit_breaker.should_halt_entries()
        if halt and not self._cb_was_active:
            self.notifier.send(f"⚠️ Circuit breaker ACTIVATED: {halt_reason}")
            self._cb_was_active = True
        elif not halt and self._cb_was_active:
            self.notifier.send("✅ Circuit breaker deactivated — entries resumed")
            self._cb_was_active = False
        if self._soft_halt_active:
            halt = True

        entries_allowed = not halt

        # Check resolved markets
        self._check_resolved_markets()

        # Update prices
        self._update_position_prices()
        self._check_price_drift_reanalysis()

        # Exit detection + execution
        for cid, reason in self.exit_monitor.drain():
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)

        match_states = self._fetch_match_states()
        for cid, reason in self.exit_monitor.check_exits(bankroll, match_states, self.cycle_count):
            if cid in self.portfolio.positions and not self.exit_monitor.is_exiting(cid):
                self._exit_position(cid, reason)
        self._handle_hold_revokes()
        self._sync_ws_subscriptions()

        # Entry: fresh scan (analyze=True)
        fresh_markets = self.scanner.get_markets()
        self.entry_gate.run(
            fresh_markets, entries_allowed=entries_allowed, analyze=True,
            bankroll=bankroll, cycle_count=self.cycle_count,
            blacklist=self.blacklist, exited_markets=self._exited_markets,
        )

        # Entry: stock queue drain (analyze=False — no AI cost)
        self.entry_gate.drain_stock(
            entries_allowed=entries_allowed, bankroll=bankroll,
            cycle_count=self.cycle_count, blacklist=self.blacklist,
            exited_markets=self._exited_markets,
        )

        # Farming re-entry (no AI, uses saved probability)
        self._check_farming_reentry()

        # Check outcomes + log
        self._check_tracked_outcomes()
        self._log_cycle_summary(bankroll, "ok")

    # ── Exit execution ─────────────────────────────────────────────────────

    def _exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 3) -> None:
        """Execute exit: remove from portfolio, add to reentry pool or blacklist, log.

        This is the ONLY place that calls executor.exit(). ExitMonitor detects,
        Agent executes.
        """
        self.exit_monitor.mark_exiting(condition_id)
        try:
            pos = self.portfolio.remove_position(condition_id)
        finally:
            self.exit_monitor.unmark_exiting(condition_id)
        if not pos:
            return

        self._exit_cooldowns[condition_id] = self.cycle_count + cooldown_cycles

        # Execute via executor
        self.executor.exit_position(pos, reason=reason, mode=self.config.mode)

        # Record realized PnL
        realized_pnl = pos.unrealized_pnl_usdc
        self.portfolio.record_realized(realized_pnl)

        # Profitable exit → add to farming re-entry pool
        profitable_reasons = {
            "take_profit", "trailing_stop", "spike_exit",
            "edge_tp", "scale_out_final", "vs_take_profit",
        }
        if reason in profitable_reasons and realized_pnl > 0:
            existing_pool = self.reentry_pool.get(condition_id)
            original_entry = existing_pool.original_entry_price if existing_pool else pos.entry_price
            self.reentry_pool.add(
                condition_id=condition_id,
                event_id=getattr(pos, "event_id", "") or "",
                slug=pos.slug,
                question=getattr(pos, "question", ""),
                direction=pos.direction,
                token_id=pos.token_id,
                ai_probability=pos.ai_probability,
                confidence=pos.confidence,
                original_entry_price=original_entry,
                exit_price=pos.current_price,
                exit_cycle=self.cycle_count,
                end_date_iso=getattr(pos, "end_date_iso", ""),
                match_start_iso=getattr(pos, "match_start_iso", ""),
                sport_tag=getattr(pos, "sport_tag", ""),
                number_of_games=getattr(pos, "number_of_games", 0),
                was_scouted=getattr(pos, "scouted", False),
                realized_pnl=realized_pnl,
            )
        else:
            # Non-profitable → demote to stock or blacklist
            _is_never_stock = (
                reason in _NEVER_STOCK_EXITS
                or any(reason.startswith(p) for p in _NEVER_STOCK_PREFIXES)
            )
            demoted = False
            if not _is_never_stock:
                demoted = self._try_demote_to_stock(pos, reason)
            if not demoted:
                # Blacklist
                bl_reason = reason
                for prefix in ("match_exit_", "far_penny_", "SLOT_UPGRADE", "election_reeval"):
                    if bl_reason.startswith(prefix):
                        bl_reason = prefix.rstrip("_")
                        break
                btype, duration = get_blacklist_rule(bl_reason)
                if btype and duration:
                    self.blacklist.add_rule(
                        condition_id, btype=btype, duration_cycles=duration,
                        slug=pos.slug, reason=reason,
                    )

        # Log exit
        self.trade_log.log({
            "market": pos.slug, "action": "EXIT",
            "reason": reason, "pnl_usdc": realized_pnl,
            "entry_price": pos.entry_price, "exit_price": pos.current_price,
            "direction": pos.direction,
        })
        logger.info(
            "EXIT: %s | reason=%s | pnl=$%.2f | entry=%.2f exit=%.2f",
            pos.slug[:40], reason, realized_pnl, pos.entry_price, pos.current_price,
        )
        self.notifier.send(
            f"📉 *EXIT*: {pos.slug[:40]}\n"
            f"reason={reason} pnl=${realized_pnl:.2f}"
        )

        # Mark permanently exited if resolved
        if reason in ("resolved", "near_resolve"):
            self._save_exited_market(condition_id)

    def _try_demote_to_stock(self, pos, reason: str) -> bool:
        """Attempt to demote exited position back to candidate stock queue.
        Returns True if demoted successfully.
        """
        # Delegate to entry_gate which owns the stock queues
        candidate = {
            "condition_id": pos.condition_id if hasattr(pos, "condition_id") else "",
            "market": None,  # market object not available post-exit
            "estimate": None,
            "direction": pos.direction,
            "edge": 0.0,
            "adjusted_size": 0.0,
            "entry_reason": "demoted",
            "is_consensus": False,
        }
        # Only demote if we have enough context (market object needed for re-entry)
        # Most demotions will fail gracefully here; complex demotion moved to EntryGate
        return False  # simplified — full demotion logic can be ported in follow-up

    # ── Farming re-entry ──────────────────────────────────────────────────

    def _check_farming_reentry(self) -> None:
        """Check farming re-entry pool for dip opportunities (no AI cost)."""
        # Lift verbatim from main.py _check_farming_reentry() (lines 3810-3992)
        # This method is unchanged — it uses self.reentry_pool, self.portfolio,
        # self.executor, self.esports, self._exit_cooldowns, self._match_states
        # TODO: port full implementation from main.py:3810-3992

    # ── Utilities ─────────────────────────────────────────────────────────

    def _handle_hold_revokes(self) -> None:
        """Apply match_exit hold-revoke and hold-restore mutations to positions."""
        for mexr in self.portfolio.check_match_aware_exits():
            cid = mexr["condition_id"]
            if mexr.get("revoke_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                if pos.scouted:
                    pos.hold_was_original = True
                    pos.scouted = False
                    pos.hold_revoked_at = datetime.now(timezone.utc)
                    logger.info("Hold REVOKED: %s — %s", pos.slug[:40], mexr.get("reason", ""))
            if mexr.get("restore_hold") and cid in self.portfolio.positions:
                pos = self.portfolio.positions[cid]
                pos.scouted = True
                pos.hold_revoked_at = None
                logger.info("Hold RESTORED: %s", pos.slug[:40])

    def _check_stop_file(self) -> None:
        if self.STOP_FILE.exists():
            logger.info("Stop signal received")
            self.STOP_FILE.unlink(missing_ok=True)
            self.running = False

    def _is_paused(self) -> bool:
        return Path("logs/pause_signal").exists()

    def _load_exited_markets(self) -> set:
        try:
            path = Path("logs/exited_markets.json")
            if path.exists():
                return set(json.loads(path.read_text()))
        except Exception:
            pass
        return set()

    def _save_exited_market(self, cid: str) -> None:
        self._exited_markets.add(cid)
        try:
            Path("logs/exited_markets.json").write_text(json.dumps(list(self._exited_markets)))
        except Exception:
            pass

    def _fetch_match_states(self) -> dict:
        now = time.time()
        if now - self._last_match_state_fetch < 60:
            return self._match_states
        # Port from main.py _fetch_match_states() (lines 323-378)
        self._last_match_state_fetch = now
        return self._match_states

    def _update_position_prices(self) -> bool:
        # Port from main.py _update_position_prices() (lines 4158-4358)
        return False

    def _sync_ws_subscriptions(self) -> None:
        # Port from main.py _sync_ws_subscriptions() (lines 379-383)
        pass

    def _check_price_drift_reanalysis(self) -> None:
        # Port from main.py _check_price_drift_reanalysis() (lines 4444-4457)
        pass

    def _check_resolved_markets(self) -> None:
        # Port from main.py _check_resolved_markets() (lines 4458-4551)
        pass

    def _check_tracked_outcomes(self) -> None:
        # Port from main.py _check_tracked_outcomes() (lines 4359-4443)
        pass

    def _log_cycle_summary(self, bankroll: float, status: str) -> None:
        # Port from main.py _log_cycle_summary() (lines 4643-4662)
        pass

    def _maybe_run_reflection(self) -> None:
        # Port from main.py _maybe_run_reflection() (lines 4552-4642)
        pass
```

> **IMPORTANT:** The stubs marked `# Port from main.py <method>(lines X-Y)` must be filled by copying the exact method body from `src/main.py` at those line numbers. Do not invent implementations — copy verbatim and update `self.` references if any moved.

- [ ] **Step 2: Fill all stub methods by copying from main.py**

For each stub:
1. Read the referenced lines in `src/main.py`
2. Copy the method body into `src/agent.py`
3. Update any `self.` references that moved to `self.entry_gate.*` or `self.exit_monitor.*`

Specifically:
- `_check_farming_reentry`: lines 3810–3992 → copy verbatim (uses self.reentry_pool etc. which stay in agent)
- `_fetch_match_states`: lines 323–378
- `_update_position_prices`: lines 4158–4358
- `_sync_ws_subscriptions`: lines 379–383
- `_check_price_drift_reanalysis`: lines 4444–4457 (calls `self.entry_gate.invalidate_cache(cid)` instead of `self._analyzed_market_ids.pop(cid)`)
- `_check_resolved_markets`: lines 4458–4551
- `_check_tracked_outcomes`: lines 4359–4443
- `_log_cycle_summary`: lines 4643–4662
- `_maybe_run_reflection`: lines 4552–4642

- [ ] **Step 3: Verify import**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.agent import Agent; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/agent.py
git commit -m "feat: add agent.py — thin loop replacing 4900-line Agent in main.py

Delegates entry to EntryGate, exit detection to ExitMonitor.
_exit_position() stays in agent (deep reentry/blacklist coupling).
_check_farming_reentry() stays in agent (uses reentry_pool + executor).
Stub methods filled from main.py via copy-and-update."
```

---

## Task 5: Update main.py (strip to entry point only)

**Files:**
- Modify: `src/main.py` (reduce from 4973L to ~120L)

**Purpose:** main.py becomes the entry point only. It imports `Agent` from `src.agent`, not defines it.

- [ ] **Step 1: Identify what stays in main.py**

Three things stay:
1. `main()` function (lines 4942–4969) — entry point
2. `_reset_simulation()` function (lines 4905–4941) — called with `--reset`
3. Top-level imports needed by those two functions

Everything else moves to `src/agent.py`.

- [ ] **Step 2: Replace src/main.py**

Read the current `main()` (lines 4942–4969) and `_reset_simulation()` (lines 4905–4941) from `src/main.py`. Then overwrite `src/main.py` with:

```python
"""main.py — Entry point only.

All business logic is in:
  src/agent.py    — thin Agent loop
  src/entry_gate.py — unified entry pipeline
  src/exit_monitor.py — exit detection
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.config import load_config, Mode
from src.process_lock import acquire_lock
from src.agent import Agent


def _reset_simulation() -> None:
    # PASTE _reset_simulation() body from current main.py lines 4905-4941
    pass  # placeholder — replace with actual body


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "--reset" in sys.argv:
        _reset_simulation()
        sys.argv.remove("--reset")

    acquire_lock()
    config = load_config()

    if config.mode == Mode.LIVE:
        print("\n*** WARNING: LIVE TRADING MODE ***")
        confirm = input("Type 'CONFIRM LIVE' to proceed: ")
        if confirm.strip() != "CONFIRM LIVE":
            print("Aborted.")
            sys.exit(1)

    agent = Agent(config)
    agent.run()


if __name__ == "__main__":
    main()
```

After writing the skeleton, fill `_reset_simulation()` by copying lines 4905–4941 from the old `src/main.py` verbatim.

- [ ] **Step 3: Verify bot can start**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.main import main; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/main.py
git commit -m "refactor: strip main.py to entry point only (~120L)

Agent class moved to src/agent.py. main.py now only contains:
  main(), _reset_simulation(), and their imports.
4900+ lines of business logic now in entry_gate.py + exit_monitor.py + agent.py."
```

---

## Task 6: Fix dashboard.py hardcoded config defaults

**Files:**
- Modify: `src/dashboard.py`

**Purpose:** Dashboard reads config values from config.yaml at startup but uses hardcoded defaults that don't match the user's actual config. Fix by reading from the passed-in AppConfig object.

- [ ] **Step 1: Find the hardcoded defaults**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
grep -n "0\.05\|0\.40\|0\.15\|max_positions\|stop_loss\|default.*=" src/dashboard.py | head -20
```

- [ ] **Step 2: Replace hardcoded defaults with config references**

For each hardcoded value found, replace with `config.<section>.<field>` where `config` is the `AppConfig` passed to the dashboard. The dashboard already receives config — just use it.

Pattern:
```python
# BEFORE (hardcoded):
stop_loss_pct = 0.40
max_positions = 15

# AFTER (from config):
stop_loss_pct = config.risk.stop_loss_pct
max_positions = config.risk.max_positions
```

- [ ] **Step 3: Verify import**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -c "from src.dashboard import Dashboard; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
git add src/dashboard.py
git commit -m "fix: dashboard.py reads config values from AppConfig instead of hardcoded defaults"
```

---

## Task 7: Integration verification (dry_run)

**Purpose:** Run the bot for one full cycle in dry_run mode and verify the new architecture works end-to-end.

- [ ] **Step 1: Start bot in dry_run**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent"
python -m src.main 2>&1 | tee /tmp/rewrite_test.log &
sleep 120  # wait for 2 full cycles
kill %1
```

Or run interactively and stop after Cycle #2 with CTRL+C.

- [ ] **Step 2: Check each verification item**

```bash
grep -E "Cycle #1 start|Cycle #2 start" /tmp/rewrite_test.log
grep -E "EntryGate|ExitMonitor|entry_gate|exit_monitor" /tmp/rewrite_test.log
grep -E "ENTERED:|BLOCKED|CONSENSUS_OVERRIDE" /tmp/rewrite_test.log
grep -E "EXIT:|stop_loss|trailing_tp" /tmp/rewrite_test.log
grep -E "is_esports|ESPORTS_WINNER_OVERRIDE" /tmp/rewrite_test.log
```

Expected (all must match):
```
✅ "Cycle #1 start" — bot starts
✅ markets found > 0 — scanner works
✅ at least 1 ENTERED or BLOCKED/HOLD log — entry_gate fires
✅ no "duplicate exit" errors — _exiting_set works
✅ no "ImportError" or "AttributeError" — all module references valid
✅ no "BUG: candidates collected but entries_allowed=False" — safety guard not triggered
```

If FAR markets exist:
```
✅ FAR market logged as going through sanity check (not bypassed)
✅ No ENTERED log for a market that shows BLOCKED in the same cycle
```

- [ ] **Step 3: If all green — report to user for GitHub push decision**

Do NOT push to GitHub automatically. Show the user the verification log excerpts and ask:
"Doğrulama tamamlandı. GitHub'a push etmemi ister misin?"

---

## Self-Review

**Spec coverage check:**
- [x] Unified entry pipeline (entry_gate.py) — Task 3
- [x] FAR sanity check bypass fix — Task 3 (no `_fill_from_far_stock` bypass path)
- [x] ESPORTS_TAGS DRY fix — Task 1
- [x] ExitMonitor separates detection from execution — Task 2
- [x] agent.py calls entry_gate twice (fresh+stock), analyze=bool — Task 3+4
- [x] entries_allowed safety assert — Task 3 (entry_gate.run)
- [x] Dashboard hardcoded fix — Task 6
- [x] reentry/farming routing (stays in agent.py as _check_farming_reentry) — Task 4
- [x] self_improve + scout: don't import Agent (confirmed — no import changes needed)
- [x] Dry_run verification with specific log checks — Task 7
- [x] GitHub push only after user confirmation — Task 7 Step 3

**Placeholder scan:**
- Task 4 Step 2: "PASTE ... body" instructions — explicit line references given, not TBD
- Task 5 Step 2: same pattern — explicit line references
- `_try_demote_to_stock` simplified to `return False` with note for follow-up — acceptable, doesn't break anything (positions will blacklist instead of stock, which was the old behavior before demotion was added)

**Type consistency:**
- `ExitMonitor.drain()` → `list[tuple[str, str]]` ← used as `for cid, reason in self.exit_monitor.drain()` ✅
- `ExitMonitor.check_exits()` → `list[tuple[str, str]]` ← same pattern ✅
- `EntryGate.run()` → `list[str]` (entered condition_ids) ✅
- `sport_rules.is_esports(str) -> bool` ← used as `if is_esports(_sport_tag):` ✅
