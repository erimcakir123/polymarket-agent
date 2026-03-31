# MiroFish Political Bot — Phase 3: Polymarket Integration

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

Phase 2 built the prediction pipeline: market scanner → seed builder → MiroFish simulation → probability → edge. Now we add the ability to actually interact with Polymarket: place orders, track positions, manage risk.

**Read these files first:**
- `docs/pipeline-log.md` — Phase 2 decisions and architecture
- `docs/blind-test-results.md` — Phase 1 prediction quality

**Reference (READ ONLY, do NOT import):**
- `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\src\executor.py` — order execution patterns
- `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\src\portfolio.py` — position tracking patterns
- `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\src\risk_manager.py` — risk management patterns
- `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\src\models.py` — data model patterns
- `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\src\notifier.py` — Telegram notification patterns

## OBJECTIVE

Add Polymarket execution, portfolio tracking, risk management, and notifications. After this phase, the bot can run in DRY_RUN mode (simulated trades, no real money).

## HARD RULES

1. **COPY and ADAPT code from Polymarket Agent — do NOT import from it.**
2. **Do NOT touch Polymarket Agent directory.**
3. **Default mode is DRY_RUN.** Never default to live trading.
4. **Never hardcode API keys, wallet keys, or secrets.**
5. **Simpler is better** — political markets don't need live momentum, scale-outs, upset hunter, or light cycles. Strip those out when copying.
6. **Test after every file.**
7. **Position limits: max 5 concurrent political positions** (conservative start).
8. **Max single position: 3% of bankroll** (conservative start).
9. **Total political exposure: max 12% of bankroll** (won't endanger sports bot profits).

## NEW MODULES

### Module 9: `src/executor.py` (~150 lines)
COPY from Polymarket Agent's executor.py. Simplify:
- Keep: `fetch_order_book()`, `Executor` class, dry_run/paper/live modes
- Keep: limit order and market order logic
- Remove: anything sports-specific
- Adapt: use our config.py, our models.py

### Module 10: `src/portfolio.py` (~200 lines)
COPY from Polymarket Agent's portfolio.py. Simplify:
- Keep: position tracking, add/remove position, bankroll calculation
- Keep: JSON persistence (save positions to disk)
- Remove: sports-specific fields (match_states, esports data)
- Add: `category` field on positions (always "political")

### Module 11: `src/risk_manager.py` (~100 lines)
Simplified risk management for political markets:
- Max 5 concurrent positions
- Max 3% per position
- Max 12% total deployed
- No Kelly criterion (not enough calibration data yet)
- Simple stop-loss: exit if position drops 40% from entry
- Simple take-profit: trailing TP, activate at +25%, trail 10% from peak
- Daily loss limit: if 3 losses in a day, halt for 24 hours

### Module 12: `src/notifier.py` (~80 lines)
COPY from Polymarket Agent's notifier.py:
- Telegram notifications for: new position, exit, daily summary
- Use SAME Telegram bot token and chat ID (reuse existing bot)
- Prefix all messages with "[POLITICAL]" to distinguish from sports bot

### Module 13: `src/political_bot.py` (~250 lines)
Main orchestrator — the equivalent of agent.py but MUCH simpler:
```python
class PoliticalBot:
    def __init__(self, mode: str = "dry_run"):
        self.config = load_config()
        self.scanner = PoliticalScanner()
        self.seed_builder = SeedBuilder()
        self.sim_client = SimulationClient()
        self.probability = ProbabilityExtractor()
        self.edge_calc = EdgeCalculator()
        self.executor = Executor(mode=mode)
        self.portfolio = Portfolio()
        self.risk = RiskManager()
        self.notifier = Notifier()

    async def run_cycle(self):
        """One analysis cycle. Run every 6-12 hours (political markets move slowly)."""
        # 1. Scan for political markets
        # 2. Filter already-held positions
        # 3. Build seed packets for top candidates
        # 4. Run MiroFish simulations (this takes time)
        # 5. Extract probabilities
        # 6. Calculate edges
        # 7. Execute trades above threshold (dry_run)
        # 8. Check exits on existing positions
        # 9. Notify via Telegram
        # 10. Log everything

    async def check_exits(self):
        """Check existing positions for exit conditions."""
        # Stop-loss
        # Take-profit
        # Market resolved

    def run(self):
        """Main loop."""
        while self.running:
            self.run_cycle()
            sleep(6 * 3600)  # 6 hours between cycles
```

No light cycles. No heavy/light distinction. Political markets move slowly — one cycle every 6-12 hours is plenty.

### Module 14: `src/main.py` (~30 lines)
Entry point:
```python
if __name__ == "__main__":
    bot = PoliticalBot(mode="dry_run")
    bot.run()
```

## WHAT TO COPY vs WRITE FRESH

| Component | Source | Action |
|---|---|---|
| executor.py | Polymarket Agent | COPY + simplify |
| portfolio.py | Polymarket Agent | COPY + simplify |
| risk_manager.py | Polymarket Agent | WRITE FRESH (much simpler rules) |
| notifier.py | Polymarket Agent | COPY + add [POLITICAL] prefix |
| political_bot.py | — | WRITE FRESH |
| main.py | — | WRITE FRESH |

**When copying:** Read the ENTIRE source file first. Understand every method. Only copy what's needed. Adapt all imports to our project structure. Do NOT leave dead code or unused methods.

## EXECUTION ORDER

1. `src/executor.py` → test basic order book fetch + dry_run order
2. `src/portfolio.py` → test add/remove position, persistence
3. `src/risk_manager.py` → test all limits and exit conditions
4. `src/notifier.py` → test Telegram message send
5. `src/political_bot.py` → integration test: full cycle in dry_run
6. `src/main.py` → test bot starts and runs one cycle

## TESTING

### Unit tests for each module
- executor: mock CLOB API, test dry_run mode
- portfolio: test CRUD operations, persistence, bankroll calc
- risk_manager: test position limits, stop-loss triggers, daily halt
- notifier: mock Telegram API, test message formatting

### Integration test
- Run one full dry_run cycle with a real political market
- Verify: market found → seed built → simulation queued → probability extracted → edge calculated → dry_run order logged → position recorded → Telegram notified
- This is the most important test

## ANTI-SPAGHETTI CHECKLIST

```bash
# 1. All tests pass
python -m pytest tests/ -v --tb=short

# 2. No imports from Polymarket Agent
grep -rn "from src.agent\|from Polymarket" src/

# 3. No dead code from copying
# Every function in executor.py, portfolio.py must have a caller

# 4. No sports-specific code remaining
grep -rn "esports\|espn\|pandascore\|momentum\|upset" src/

# 5. No hardcoded secrets
grep -rn "api_key\|token.*=.*['\"]" src/ | grep -v "\.env\|config\|test"

# 6. Consistent model usage
# All market data should use PoliticalMarket, not raw dicts

# 7. Mode safety
grep -rn "live\|LIVE" src/
# Verify live mode is never default, always requires explicit flag
```

## SUCCESS CRITERIA

- [ ] All modules created and tested
- [ ] Full dry_run cycle works end-to-end
- [ ] Telegram notifications work (with [POLITICAL] prefix)
- [ ] Portfolio persists to disk correctly
- [ ] Risk limits enforced (test: try to exceed 5 positions, verify rejection)
- [ ] Bot can start, run one cycle, and stop cleanly
- [ ] No imports from Polymarket Agent
- [ ] No dead code from copying
- [ ] `docs/integration-log.md` documents all decisions

## WHAT'S NEXT

Phase 4: Paper trading on live political markets. Bot runs continuously in dry_run mode, we track hypothetical P&L and calibration data over 2 weeks.
