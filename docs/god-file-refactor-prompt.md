# Agent.py God File Refactor — Complete Prompt

> **Paste this entire prompt into a NEW Claude Code conversation.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent`

---

## OBJECTIVE

Refactor `src/agent.py` (2293 lines, god file) into 4 focused modules using **extract & delegate** strategy. Agent.py must become a ~400-500 line thin orchestrator. Zero new bugs, zero dead code, zero spaghetti. All 285 tests must pass after every single file change.

## HARD RULES — VIOLATING ANY OF THESE IS A FAILURE

1. **Read CLAUDE.md first** — `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\CLAUDE.md` contains project rules. Follow them.
2. **Read EVERY method you plan to move BEFORE moving it** — understand all `self.*` dependencies.
3. **Test after EVERY file change** — run `python -m pytest tests/ -v --tb=short` after each module extraction. If tests break, fix before proceeding. Never batch multiple extractions.
4. **Zero dead code** — after moving a method, DELETE it from agent.py. After finishing all moves, grep the entire codebase to verify no orphaned imports, no unused parameters, no unreachable code.
5. **Zero duplication** — never copy-paste logic. If two modules need the same helper, put it in one place and import.
6. **Zero new files beyond the 4 specified** — do not create utility files, helper files, or "common" modules. Only create the 4 modules listed below.
7. **Preserve exact behavior** — this is a MOVE refactor, not a rewrite. Do not change any logic, thresholds, log messages, or control flow. The bot's trading behavior must be byte-for-byte identical.
8. **No correlation risk system** — user explicitly does not want one. Do not add or suggest it.
9. **Never restart/kill the bot** — do not touch any running processes.
10. **Use `effective_price()` from `src/models.py`** — never inline `(1 - price)` calculations.

## ARCHITECTURE: AgentContext Pattern

Create a shared context dataclass that all extracted modules receive. This replaces `self.*` access.

```python
# Add to src/agent.py (top of file, after imports)
from dataclasses import dataclass, field

@dataclass
class AgentContext:
    """Shared state passed to all orchestrator modules."""
    config: AppConfig
    portfolio: Portfolio
    executor: Executor
    blacklist: Blacklist
    circuit_breaker: CircuitBreaker
    reentry_pool: ReentryPool
    outcome_tracker: OutcomeTracker
    trade_log: TradeLogger
    portfolio_log: TradeLogger
    perf_log: TradeLogger
    notifier: TelegramNotifier
    exit_monitor: ExitMonitor
    entry_gate: EntryGate
    scanner: MarketScanner
    ai: AIAnalyst
    risk: RiskManager
    esports: EsportsDataClient
    odds_api: OddsAPIClient
    scout: ScoutScheduler
    edge_tracker: EdgeSourceTracker
    ws_feed: WebSocketFeed
    wallet: object  # Optional[Wallet]
    cycle_timer: CycleTimer

    # Mutable shared state
    cycle_count: int = 0
    light_cycle_count: int = 0
    running: bool = True
    exited_markets: set = field(default_factory=set)
    exit_cooldowns: dict = field(default_factory=dict)
    match_states: dict = field(default_factory=dict)
    last_match_state_fetch: float = 0.0
    daily_reentry_count: int = 0
    last_reentry_reset_date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    bets_since_approval: int = 0
    pre_match_prices: dict = field(default_factory=dict)
    light_cooldowns: dict = field(default_factory=dict)
    soft_halt_active: bool = False
    cb_was_active: bool = False
    consecutive_api_failures: int = 0
    last_cycle_has_live_clob: bool = False
    last_candidate_count: int = 0
```

Agent.__init__ creates this context object and passes it to each module.

## THE 4 NEW MODULES

### Module 1: `src/exit_executor.py` (~250 lines)

**Methods to MOVE from agent.py:**
- `_exit_position()` (line 507-672) — the core exit execution logic
- `_process_scale_outs()` (line 674-749) — scale-out processing
- `_try_demote_to_stock()` (line 751-831) — demote position to stock strategy
- `_handle_hold_revokes()` (line 1515-1530) — match_exit hold revoke mutations
- `_save_exited_market()` (line 1550-1556) — persist exited market ID

**Also move these constants:**
- `_NEVER_STOCK_EXITS` (line 54)
- `_NEVER_STOCK_PREFIXES` (line 58)

**Class structure:**
```python
class ExitExecutor:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    def exit_position(self, condition_id: str, reason: str, cooldown_cycles: int = 1) -> None: ...
    def process_scale_outs(self) -> None: ...
    def try_demote_to_stock(self, pos, reason: str) -> bool: ...
    def handle_hold_revokes(self) -> None: ...
    def save_exited_market(self, cid: str) -> None: ...
```

**Agent.py calls change from:**
- `self._exit_position(cid, reason)` → `self.exit_executor.exit_position(cid, reason)`
- `self._process_scale_outs()` → `self.exit_executor.process_scale_outs()`
- etc.

---

### Module 2: `src/live_strategies.py` (~500 lines)

**Methods to MOVE from agent.py:**
- `_check_farming_reentry()` (line 858-1048) — reentry pool scanning
- `_check_live_dip()` (line 1052-1197) — live dip entry strategy
- `_check_live_momentum()` (line 1199-1346) — live momentum entry strategy
- `_check_upset_hunter()` (line 1350-1511) — upset hunter strategy

**Also move:**
- `_light_cooldown_ready()` (line 834) — cooldown check helper
- `_set_light_cooldown()` (line 838) — cooldown set helper
- `_get_held_event_ids()` (line 843) — helper to get held event IDs
- `_check_exposure_limit()` (line 849-854) — exposure limit check
- `_LIGHT_COOLDOWNS` constant (line 61-66)

**Class structure:**
```python
class LiveStrategies:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    def check_farming_reentry(self) -> bool: ...
    def check_live_dip(self, held_events=None, fresh_markets=None) -> int: ...
    def check_live_momentum(self, held_events=None, fresh_markets=None, match_states=None) -> bool: ...
    def check_upset_hunter(self, fresh_markets: list, bankroll: float) -> None: ...
    def light_cooldown_ready(self, strategy: str) -> bool: ...
    def set_light_cooldown(self, strategy: str) -> None: ...
    def get_held_event_ids(self) -> set[str]: ...
    def check_exposure_limit(self, candidate_size: float) -> bool: ...
```

---

### Module 3: `src/price_updater.py` (~250 lines)

**Methods to MOVE from agent.py:**
- `_update_position_prices()` (line 1614-1830) — update all position prices from CLOB/API
- `_sync_ws_subscriptions()` (line 1832-1835) — sync WebSocket subscriptions
- `_get_clob_midpoint()` (line 2211-2225) — get midpoint from CLOB
- `_fetch_match_states()` (line 1558-1612) — fetch match states from Gamma API

**Class structure:**
```python
class PriceUpdater:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    def update_position_prices(self) -> bool: ...
    def sync_ws_subscriptions(self) -> None: ...
    def get_clob_midpoint(self, token_id: str) -> float | None: ...
    def fetch_match_states(self) -> dict[str, dict]: ...
```

---

### Module 4: `src/cycle_logic.py` (~300 lines)

**Methods to MOVE from agent.py:**
- `_check_price_drift_reanalysis()` (line 1837-1849) — check if positions need re-analysis
- `_check_resolved_markets()` (line 1851-1943) — check for resolved markets
- `_check_tracked_outcomes()` (line 1945-2028) — check tracked outcomes
- `_log_cycle_summary()` (line 2030-2048) — log cycle summary
- `_write_status()` (line 2050-2067) — write status file
- `_log_performance()` (line 2069-2116) — log performance metrics
- `_maybe_run_reflection()` (line 2118-2207) — AI self-reflection
- `_match_duration()` (line 2227-2259) — static helper
- `_estimate_match_live()` (line 2261-2293) — static helper
- `_check_stop_file()` (line 1532-1536) — check stop signal
- `_is_paused()` (line 1538-1539) — check pause state
- `_load_exited_markets()` (line 1541-1548) — load exited markets from disk

**Class structure:**
```python
class CycleLogic:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    def check_price_drift_reanalysis(self) -> None: ...
    def check_resolved_markets(self) -> None: ...
    def check_tracked_outcomes(self) -> None: ...
    def log_cycle_summary(self, bankroll: float, status: str) -> None: ...
    def write_status(self, state: str, step: str, **kwargs) -> None: ...
    def log_performance(self) -> None: ...
    def maybe_run_reflection(self) -> None: ...
    def check_stop_file(self) -> None: ...
    def is_paused(self) -> bool: ...
    def load_exited_markets(self) -> set: ...

    @staticmethod
    def match_duration(slug: str, question: str) -> float: ...
    @staticmethod
    def estimate_match_live(slug: str, question: str, end_date_iso: str, ...) -> tuple: ...
```

---

## WHAT STAYS IN agent.py (~400-500 lines)

After all extractions, agent.py keeps ONLY:
- `AgentContext` dataclass
- `Agent.__init__()` — creates context, instantiates 4 modules
- `Agent.run()` — main loop
- `Agent.run_light_cycle()` — light cycle orchestration (calls LiveStrategies, ExitMonitor, PriceUpdater)
- `Agent.run_cycle()` — heavy cycle orchestration (calls EntryGate, ExitMonitor, CycleLogic, PriceUpdater)

These methods become thin orchestrators that call into the 4 modules.

## EXECUTION ORDER — DO THESE ONE AT A TIME

1. **Create `AgentContext` dataclass** in agent.py → run tests
2. **Extract `src/exit_executor.py`** → update agent.py calls → run tests
3. **Extract `src/live_strategies.py`** → update agent.py calls → run tests
4. **Extract `src/price_updater.py`** → update agent.py calls → run tests
5. **Extract `src/cycle_logic.py`** → update agent.py calls → run tests
6. **Final cleanup** — remove unused imports from agent.py → run tests
7. **Final audit** — grep for dead code, unused params, orphaned imports across ALL src/ files

## CRITICAL SELF-REFERENCE PATTERNS TO WATCH

These `self.*` usages in moved methods must become `self.ctx.*`:

| Old pattern | New pattern |
|---|---|
| `self.config` | `self.ctx.config` |
| `self.portfolio` | `self.ctx.portfolio` |
| `self.executor` | `self.ctx.executor` |
| `self.blacklist` | `self.ctx.blacklist` |
| `self._exited_markets` | `self.ctx.exited_markets` |
| `self._exit_cooldowns` | `self.ctx.exit_cooldowns` |
| `self._match_states` | `self.ctx.match_states` |
| `self._pre_match_prices` | `self.ctx.pre_match_prices` |
| `self._daily_reentry_count` | `self.ctx.daily_reentry_count` |
| `self.trade_log` | `self.ctx.trade_log` |
| `self.notifier` | `self.ctx.notifier` |
| `self.cycle_count` | `self.ctx.cycle_count` |
| `self.light_cycle_count` | `self.ctx.light_cycle_count` |
| `self.bets_since_approval` | `self.ctx.bets_since_approval` |
| `self.reentry_pool` | `self.ctx.reentry_pool` |
| `self.circuit_breaker` | `self.ctx.circuit_breaker` |
| `self.outcome_tracker` | `self.ctx.outcome_tracker` |
| `self.esports` | `self.ctx.esports` |
| `self.odds_api` | `self.ctx.odds_api` |
| `self.ai` | `self.ctx.ai` |
| `self.risk` | `self.ctx.risk` |
| `self.scout` | `self.ctx.scout` |
| `self.edge_tracker` | `self.ctx.edge_tracker` |
| `self.ws_feed` | `self.ctx.ws_feed` |
| `self.exit_monitor` | `self.ctx.exit_monitor` |
| `self.entry_gate` | `self.ctx.entry_gate` |

**CRITICAL**: Some methods call OTHER methods that are being moved to different modules. Map these cross-references BEFORE moving:

- `_exit_position()` calls `_save_exited_market()` → both go to `exit_executor.py` ✓
- `_exit_position()` calls `_try_demote_to_stock()` → both go to `exit_executor.py` ✓
- `_check_farming_reentry()` calls `_exit_position()` → must call `self.ctx.exit_executor.exit_position()` (cross-module)
- `_check_live_dip()` calls `_exit_position()` indirectly → verify
- `_check_live_momentum()` calls `_check_exposure_limit()` → both go to `live_strategies.py` ✓
- `_check_resolved_markets()` calls `_exit_position()` → must call `self.ctx.exit_executor.exit_position()` (cross-module)
- `run_light_cycle()` and `run_cycle()` call methods across all 4 modules → stays in agent.py as orchestrator

**For cross-module calls**: The ExitExecutor instance must be available on the context. Add it in Agent.__init__ AFTER creating the module:
```python
self.ctx = AgentContext(...)
self.exit_executor = ExitExecutor(self.ctx)
self.live_strategies = LiveStrategies(self.ctx)
self.price_updater = PriceUpdater(self.ctx)
self.cycle_logic = CycleLogic(self.ctx)
# Make modules accessible from context for cross-module calls
self.ctx.exit_executor = self.exit_executor
self.ctx.live_strategies = self.live_strategies
```

## ANTI-SPAGHETTI CHECKLIST (run after EVERY module extraction)

```bash
# 1. Tests pass
python -m pytest tests/ -v --tb=short

# 2. No orphaned imports in agent.py
# After moving _exit_position, if nothing else uses scale_out, remove that import

# 3. No dead methods in agent.py
# grep for "def _" in agent.py — every method must have a caller

# 4. No duplicate logic
# grep for common patterns like "1.0 - " or "effective_price" to verify single source
```

## FINAL VERIFICATION

After all 4 modules extracted:
1. `python -m pytest tests/ -v --tb=short` → 285 passed
2. `wc -l src/agent.py` → should be ~400-500 lines
3. `grep -rn "def " src/exit_executor.py src/live_strategies.py src/price_updater.py src/cycle_logic.py` → verify all methods present
4. `grep -rn "from src.agent import\|from src import agent" src/` → should be ZERO (no circular imports)
5. `grep -rn "1\.0 - \|1 - " src/exit_executor.py src/live_strategies.py src/price_updater.py src/cycle_logic.py` → should be ZERO (use effective_price)
6. Count total lines: agent.py + 4 modules ≈ 2293 (nothing lost, nothing duplicated)

## EXISTING MODULES — DO NOT TOUCH

These modules already exist and work correctly. Do NOT modify them during this refactor:
- `src/exit_monitor.py` — exit detection (already extracted)
- `src/entry_gate.py` — entry evaluation (already extracted)
- `src/portfolio.py` — position management
- `src/risk_manager.py` — risk evaluation
- `src/models.py` — data models + effective_price()
- All other src/*.py files

Only modify them if a moved method's import path changes and they import from agent.py (which they shouldn't — verify with grep first).
