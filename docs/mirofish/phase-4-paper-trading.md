# MiroFish Political Bot — Phase 4: Paper Trading

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

Phase 3 built the full bot with Polymarket integration. It can scan markets, run simulations, calculate edges, and execute dry_run trades. Now we run it on LIVE political markets with NO real money for 2 weeks to collect calibration data.

**Read these files first:**
- `docs/integration-log.md` — Phase 3 architecture
- `docs/blind-test-results.md` — Phase 1 prediction quality baseline

## OBJECTIVE

Run the bot in dry_run mode for 2 weeks on live political markets. Track every prediction, every hypothetical trade, every outcome. Build calibration data to answer: "Is MiroFish profitable on political markets?"

## LLM UPGRADE DECISION

This is the first phase where upgrading to a PAID LLM makes sense.
Paper trading needs to reflect real production quality — running 2 weeks of tests with a bad model wastes time.

**Decision tree:**
- If Phase 1-3 used free LLM and results were promising → **upgrade to Gemini Flash paid (~$9/month)** for accurate paper trading
- If Phase 1b already used Gemini Flash → keep using it
- If you want to test free LLM for paper trading first → run 1 week free, then decide

Update `.env` if upgrading:
```env
LLM_API_KEY=<Gemini Flash paid API key>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL_NAME=gemini-2.0-flash
```

## HARD RULES

1. **DRY_RUN ONLY.** Do NOT switch to live or paper mode. No real money.
2. **Do NOT touch Polymarket Agent** — it's running live, do not interfere.
3. **Log EVERYTHING** — every prediction, every trade signal, every market price at time of signal.
4. **Do NOT optimize mid-test** — resist the urge to tweak parameters during the 2-week test. Tweaking invalidates the test. Note desired changes in `docs/optimization-notes.md` but do NOT implement them.
5. **Run the bot continuously** — it should cycle every 6-12 hours automatically.
6. **Monitor daily** — check Telegram notifications, review logs, verify bot is running.

## SETUP

### 1. Configure for continuous running
- Verify Docker (Neo4j) stays running after system restart
- Set up bot as a background process or scheduled task
- Ensure logs rotate (don't fill disk)
- Ensure MiroFish engine stays running
- **Verify light cycles run every hour** (price checks + catalyst scan)
- **Verify heavy cycles run every 6-12 hours** (new discovery + re-evaluation)
- Both cycle types should be visible in logs with clear labels

### 2. Create tracking spreadsheet
Create `docs/paper-trading-tracker.md`:

```markdown
# Paper Trading Tracker

## Trade Log

| # | Date | Market | Question | MiroFish Prob | Market Price | Direction | Edge | Signal Size | Outcome | P&L (hypothetical) |
|---|------|--------|----------|--------------|-------------|-----------|------|-------------|---------|-------------------|
| 1 | | | | | | | | | | |
```

### 3. Create daily journal
Create `docs/daily-journal.md`:

```markdown
# Daily Journal

## Day 1 — [Date]
- Markets scanned: X
- Signals generated: X
- New positions: X
- Exits: X
- Bot status: Running/Error
- Notes:

## Day 2 — [Date]
...
```

## DAILY MONITORING CHECKLIST

Every day, check:
1. Bot is still running (`docker compose ps`, check bot process)
2. Review Telegram notifications from last 24h
3. Update trade log with any new signals or exits
4. Note market price changes on open positions
5. Check for errors in bot logs
6. Total running cost (LLM API usage)
7. Update daily journal

## METRICS TO COLLECT

### Per trade:
- Market question
- MiroFish ensemble probability
- Ensemble standard deviation
- Market price at signal time
- Direction (BUY_YES/BUY_NO)
- Edge at signal time
- Hypothetical entry price
- Current market price (daily)
- Outcome (if resolved)
- Hypothetical P&L
- **Trade type: NEW_ENTRY / RE-ENTRY / EXIT_REEVAL / EXIT_SL / EXIT_TP**
- **Trigger: DISCOVERY (heavy cycle) / CATALYST (re-evaluation) / PRICE_DRIFT (light cycle)**

### Per market (volatility swing tracking):
- How many times did the bot enter/exit this market?
- Total hypothetical P&L across all swings on this market
- Did active monitoring (re-evaluation exits) outperform buy-and-hold?

### Aggregate (calculated at end):
- Total signals generated
- Signals that would have been profitable
- Win rate
- Average edge at entry
- Average P&L per trade
- Sharpe ratio (if enough data)
- MiroFish calibration curve (predicted X% → actual outcome Y% of the time)
- Comparison: MiroFish probability vs final resolution
- **Re-evaluation accuracy: how often did re-eval exits avoid losses?**
- **Swing profit: total P&L from volatility swings vs hypothetical buy-and-hold P&L**
- **Light cycle value: how many urgent exits were triggered by hourly monitoring?**

## KILL/CONTINUE CRITERIA (evaluated at day 7 and day 14)

### Day 7 Mid-Test Review

**KILL if:**
- Bot hasn't generated any signals (scanner broken or no political markets meet criteria)
- All signals are in the same direction (systematic bias)
- MiroFish simulations failing > 30% of the time
- LLM costs exceeding $20 for the week

**CONTINUE if:**
- At least 5 signals generated
- Mix of BUY_YES and BUY_NO signals
- Simulations completing reliably
- Costs within budget

### Day 14 Final Review

**KILL if:**
- Win rate < 35% (worse than random after fees)
- Average edge < 3% (not enough to overcome spread + slippage)
- Calibration is terrible (70% predictions resolve YES only 40% of the time)
- Total hypothetical P&L is deeply negative

**SCALE UP (Phase 5) if:**
- Win rate > 50%
- Average edge > 5%
- Calibration is reasonable (predictions roughly match outcomes)
- Total hypothetical P&L is positive
- No systematic bugs or failures

**GRAY ZONE:**
- Win rate 35-50% or edge 3-5%: extend test by 1 more week for more data
- Good calibration but small sample: extend for more data

## WHAT NOT TO DO

- Do NOT change simulation parameters mid-test
- Do NOT cherry-pick which signals to include
- Do NOT manually override bot decisions
- Do NOT start live trading early because "it looks promising"
- Do NOT tune the model based on early results

## OPTIMIZATION NOTES

Keep a running list in `docs/optimization-notes.md` of things you WANT to change but are NOT changing during the test:

```markdown
# Optimization Notes (DO NOT IMPLEMENT DURING PHASE 4)

## Seed Packet Improvements
- [note what you'd improve]

## Simulation Settings
- [agent count, round count changes]

## Edge Threshold
- [should it be higher/lower?]

## Scanner Filters
- [too aggressive? too loose?]

## Risk Limits
- [position size, total exposure]
```

These notes become the input for Phase 5 optimization.

## ANTI-SPAGHETTI RULES

- Do NOT write new features during this phase
- Do NOT refactor code during this phase
- Only fix bugs that prevent the bot from running
- If you fix a bug, document it in `docs/bugfixes-phase4.md` with before/after

## AUDIT AT END OF PHASE

1. `docs/paper-trading-tracker.md` — complete trade log
2. `docs/daily-journal.md` — 14 days of entries
3. `docs/optimization-notes.md` — list of desired improvements
4. Kill/continue decision with supporting data
5. Total LLM cost for the 2 weeks
6. Comparison: MiroFish predictions vs actual outcomes (calibration table)
7. Polymarket Agent still running correctly, untouched

## WHAT'S NEXT

- If KILL: Archive project, document learnings
- If CONTINUE: Phase 5 — implement optimizations from notes, then go live with minimum positions
