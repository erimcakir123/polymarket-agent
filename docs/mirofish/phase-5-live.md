# MiroFish Political Bot — Phase 5: Live Trading (Cautious)

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

Phase 4 paper trading showed positive results. MiroFish generates profitable signals on political markets. Now we go live with MINIMUM risk.

**Read these files first:**
- `docs/paper-trading-tracker.md` — Phase 4 full trade log
- `docs/optimization-notes.md` — improvements identified during paper trading
- `docs/daily-journal.md` — operational learnings

## OBJECTIVE

1. Implement optimizations from Phase 4 notes
2. Switch to live trading with TINY positions
3. Monitor closely for 2 weeks
4. Scale up gradually if profitable

## HARD RULES

1. **Start with 1% max position size** (not the 3% from Phase 3).
2. **Max 3 concurrent positions** initially (not 5).
3. **Max 5% total political exposure** initially.
4. **Never touch Polymarket Agent** — sports bot runs independently.
5. **Daily monitoring is MANDATORY** — if you miss a day, halt the bot.
6. **Kill switch always available** — bot must stop cleanly on Ctrl+C or stop file.
7. **Never increase limits without 1 week of profitable data.**
8. **NEVER go all-in on a single prediction.**

## PHASE 5a: IMPLEMENT OPTIMIZATIONS (3-5 days)

Before going live, implement the improvements noted in Phase 4:

1. Review `docs/optimization-notes.md`
2. Implement changes one at a time
3. Test each change: `python -m pytest tests/ -v --tb=short`
4. Run ONE dry_run cycle after all changes to verify nothing broke
5. Document changes in `docs/optimization-changelog.md`

## PHASE 5b: GO LIVE (minimum risk)

### Switch to live mode
Update config:
```
MODE=live  # or paper if you want one more safety layer
MAX_POSITION_PERCENT=1.0
MAX_POSITIONS=3
MAX_TOTAL_EXPOSURE_PERCENT=5.0
```

### First week (days 1-7): Observe
- Max 2 new trades
- After each trade, manually verify on Polymarket UI that the order was placed correctly
- Check: correct market, correct direction, correct size
- Monitor daily: position values, market movements, bot logs

### Second week (days 8-14): Cautious scaling
- If week 1 has no losses from bugs/errors:
  - Increase to max 3 positions
  - Keep 1% position size
- If week 1 has bug-related losses:
  - HALT, fix bugs, return to dry_run for 3 days

### Third week+: Gradual scale
- If 2 weeks profitable and no bugs:
  - Increase position size to 2%
  - Increase max positions to 4
  - Increase total exposure to 8%
- Never increase more than one parameter at a time
- Wait 1 week between increases

## SCALING LADDER

| Week | Position Size | Max Positions | Max Exposure | Criteria to Advance |
|------|-------------|---------------|-------------|-------------------|
| 1 | 1% | 2 | 3% | No bugs, orders execute correctly |
| 2 | 1% | 3 | 5% | Week 1 profitable or breakeven |
| 3-4 | 2% | 4 | 8% | 2 weeks profitable |
| 5-8 | 3% | 5 | 12% | 4 weeks profitable, calibration holds |
| 9+ | 3% | 5 | 15% | Proven track record |

**Never exceed 15% total political exposure.** The sports bot is the primary revenue source.

## DAILY MONITORING (MANDATORY)

```
Morning check (5 min):
□ Bot running?
□ Docker services healthy?
□ MiroFish engine responsive?
□ Any overnight Telegram alerts?
□ Open position prices — any at stop-loss?
□ How many light cycles ran overnight? (should be ~8-10)
□ Any positions flagged for re-evaluation?

Evening check (10 min):
□ Any new trades today?
□ Any re-evaluation exits today? (volatility swings)
□ P&L for today (including swing trades)
□ Running total P&L
□ Sports bot still running fine?
□ Any catalyst alerts that were missed?
□ Update daily journal
```

## EMERGENCY PROCEDURES

### Bot crashes
1. Check logs for error
2. Restart bot
3. Verify all positions are still tracked
4. If positions out of sync → manually reconcile with Polymarket UI

### MiroFish engine crashes
1. `docker compose restart`
2. Verify Neo4j data intact
3. Bot should auto-retry simulations

### Wrong trade executed
1. Immediately manual-exit on Polymarket UI
2. Halt bot
3. Debug what happened
4. Fix and test before restarting

### Sports bot affected
1. **IMMEDIATELY halt political bot**
2. Check sports bot logs
3. They should be independent — if they're interfering, there's a bug
4. Do NOT restart political bot until root cause found

## KILL CRITERIA (even in live)

Stop and return to dry_run if:
- 3 consecutive losses
- Total political P&L drops below -5% of invested capital
- Any bug causes an incorrect order
- Sports bot is affected in any way
- LLM costs exceed budget

## ANTI-SPAGHETTI RULES

- Do NOT add new features while live trading
- Bug fixes only — and test thoroughly before deploying
- If a major change is needed, halt bot, return to dry_run, implement, test, then go live again

## AUDIT (Weekly)

Every Friday:
1. Trade log updated
2. P&L calculated
3. Calibration check: predictions matching outcomes?
4. Cost check: LLM spend within budget?
5. Sports bot check: unaffected?
6. Scaling decision: advance/hold/retreat on the ladder?

## SUCCESS DEFINITION

After 8 weeks of live trading:
- Positive total P&L
- Win rate > 50%
- Calibration within 10% of predictions
- No bugs affecting sports bot
- Sustainable LLM costs
- Political bot is a NET POSITIVE addition to the trading operation
