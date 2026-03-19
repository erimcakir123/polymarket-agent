# Polymarket Bot — Self-Improvement Program

> Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).
> An autonomous experiment loop that optimizes the betting strategy by
> analyzing real performance data and tuning ONE parameter at a time.

## Philosophy

Like autoresearch modifies `train.py` and measures `val_bpb`, we modify
`config.yaml` and measure **win rate + Brier score + simulated PnL**.

The bot runs continuously, collecting predictions and calibration data.
This program is invoked periodically (by Claude Code skill or manually)
to analyze results and propose improvements.

**Golden rule: ONE change per experiment.** Never change two parameters
at once — you won't know which one helped.

## What You CAN Modify

- `config.yaml` — any parameter in the search space (see below)
- Category filters via tags list
- Cycle timing parameters

## What You CANNOT Modify

- `src/` code files (only config tuning, not logic changes)
- `logs/` data files (read-only — these are ground truth)
- API keys or secrets
- Budget limits (these are user-set constraints)

## The Experiment Loop

```
LOOP (triggered every N resolved predictions):

1. Run analysis:
   cd "Polymarket Agent" && python -m src.self_improve

2. Read the report:
   cat logs/self_improve_report.md

3. Evaluate the PREVIOUS experiment (if any):
   - Check experiments.tsv for the last "pending" experiment
   - Compare metrics BEFORE vs AFTER the change
   - Update status: "keep" or "discard"
   - If "discard": revert config.yaml to previous value

4. Apply the PROPOSED experiment:
   - The report suggests ONE parameter change
   - Review the reasoning — does it make sense?
   - If yes: modify config.yaml, log to experiments.tsv
   - If no: skip and try next parameter
   - git commit -m "experiment: {description}"

5. Restart the bot:
   - Kill existing bot process
   - Start new bot with updated config
   - Verify it starts successfully (check agent.log)

6. WAIT for data:
   - Need 15+ new resolved predictions before next evaluation
   - Typically 2-3 days depending on market volume
```

## Evaluation Criteria

### Primary Metric: Win Rate
- Target: > 57% (profitable after fees)
- Critical: < 50% means losing money
- Current threshold for action: any experiment that drops win rate
  below 50% should be immediately reverted

### Secondary Metric: Brier Score
- Good: < 0.20 (well-calibrated)
- Acceptable: 0.20 - 0.25
- Poor: > 0.25 (predictions are poorly calibrated)

### Tertiary: Simulated PnL
- Track portfolio.jsonl unrealized + realized PnL
- An experiment that improves win rate but shrinks PnL
  (e.g., by being too conservative) is not necessarily good

## Parameter Search Space

| Parameter | Range | Effect |
|-----------|-------|--------|
| edge.min_edge | 0.03 - 0.15 | Lower = more bets but riskier |
| edge.confidence_multipliers.* | 0.5 - 2.0 | Edge scaling by confidence |
| risk.kelly_fraction | 0.10 - 0.40 | Position size aggressiveness |
| risk.stop_loss_pct | 0.15 - 0.50 | When to cut losses |
| risk.take_profit_pct | 0.20 - 0.60 | When to take profits |
| scanner.max_duration_days | 3 - 21 | Market time horizon |
| scanner.min_liquidity | 2000 - 15000 | Market quality filter |
| cycle.default_interval_min | 15 - 45 | Scan frequency |

## Decision Heuristics

1. **Win rate < 55%** → Raise min_edge (filter out bad bets)
2. **Win rate > 60%** → Lower min_edge (capture more opportunities)
3. **Category X underperforming** → Add to tags exclusion list
4. **Confidence level X miscalibrated** → Adjust its multiplier
5. **Small-edge bets losing** → Raise min_edge
6. **Large-edge bets winning** → System is working, try more volume
7. **Brier score high** → Focus on confidence multiplier tuning

## Experiment Logging Format

`logs/experiments.tsv` — tab-separated, append-only:

```
timestamp	parameter	old_value	new_value	status	win_rate	brier	description
2026-03-22T10:00	edge.min_edge	0.06	0.08	keep	0.62	0.21	Raised min_edge: filtered 30% of low-quality bets
2026-03-25T10:00	risk.kelly_fraction	0.25	0.30	discard	0.58	0.23	More aggressive sizing didn't help
```

Status values:
- `baseline` — initial measurement, no change made
- `pending` — experiment applied, waiting for data
- `keep` — experiment improved metrics, keeping the change
- `discard` — experiment worsened metrics, reverted

## Safety Rails

- NEVER change `monthly_budget_usd` or `sprint_budget_usd`
- NEVER switch mode from `dry_run` to `live` or `paper`
- NEVER modify risk.drawdown_halt_pct below 0.30
- NEVER set max_single_bet_usdc above 100
- If 3 consecutive experiments are "discard", STOP and ask the human
- Always verify bot restarts successfully after config change

## Optimal Timing

The self-improvement loop should run when enough NEW data exists:
- Minimum: 15 newly resolved predictions since last experiment
- Optimal: 25-30 resolved predictions (stronger signal)
- Maximum wait: 5 days (even with less data, run analysis for monitoring)

With current bot volume (~15-20 predictions/day including HOLDs),
expect to run every 2-3 days.
