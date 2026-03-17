# Polymarket Trading Agent — Design Spec

## Overview

Automated prediction market trading agent for Polymarket. Starts with ~$60 USDC (2K TL), grows the bankroll through AI-driven edge detection with compound growth. No portfolio cap — grows uncapped.

## Core Decisions

| Parameter | Value |
|---|---|
| Starting bankroll | ~$60 USDC |
| Growth model | Uncapped compound — no portfolio ceiling |
| Frequency | Medium — 30 min cycles, smart API calls only when needed |
| Architecture | Single Python process, single Claude Sonnet call per cycle |
| Wallet | New EOA wallet (sifirdan) |
| Platform | Local Windows (user's machine) |
| Market focus | Politics + Geopolitics (Claude's strongest domain) |
| AI model | Claude Sonnet (cost-efficient, ~$0.20/day) |

## Why Politics/Geopolitics

1. Claude's training data is heavily weighted toward politics/news — strong base rate knowledge
2. High volume + liquidity on Polymarket — low slippage risk for small bets
3. Information asymmetry — most traders are emotional, calibrated AI finds edge
4. Slow-moving markets — 30 min cycle is sufficient (unlike crypto)
5. Multi-outcome arbitrage opportunities are frequent in election markets

## Architecture

```
┌─────────────────────────────────────────────┐
│              MAIN LOOP (30 min)             │
│                                             │
│  1. Market Scanner (Gamma API, no auth)     │
│     └─ Filter: politics/geopolitics tag     │
│     └─ Min volume: $50K, min liquidity: $5K │
│                                             │
│  2. Portfolio Monitor (CLOB, no auth)       │
│     └─ Update midpoints                    │
│     └─ Check stop-loss (30% loss on entry) │
│     └─ Check take-profit (40% gain)        │
│     └─ Detect resolved markets → claim     │
│     └─ Reconcile local state vs on-chain   │
│                                             │
│  2b. Order Manager                          │
│     └─ Check pending GTC fill status       │
│     └─ Cancel stale orders (>2 cycles old) │
│                                             │
│  3. AI Analyst (SINGLE Sonnet call)         │
│     └─ Batch top 5 markets                 │
│     └─ Probability + confidence JSON       │
│     └─ ~2K token input, ~500 output        │
│     └─ ONLY called when filtered markets   │
│       pass volume/liquidity thresholds     │
│                                             │
│  4. Edge Calculator                         │
│     └─ AI prob vs market price             │
│     └─ Min edge: 6% (medium confidence)    │
│     └─ Min edge: 9% (low confidence)       │
│     └─ Min edge: 4.5% (high confidence)    │
│                                             │
│  5. Risk Manager (VETO POWER)               │
│     └─ Half-Kelly sizing                   │
│     └─ Max single bet: $75 or 15% bankroll │
│     └─ No portfolio cap                    │
│     └─ Max concurrent positions: 5         │
│     └─ Max correlated exposure: 30%        │
│     └─ Cool-down: 3 losses → pause 2 cycle │
│                                             │
│  6. Executor                                │
│     └─ dry_run → paper → live              │
│     └─ GTC limit orders (entry)            │
│     └─ FOK market orders (exit)            │
│     └─ JSONL trade log                     │
│                                             │
│  7. Dashboard Log (terminal)                │
│     └─ Portfolio summary, PnL, edge stats  │
└─────────────────────────────────────────────┘
```

## Risk Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Portfolio cap | **None** — uncapped growth | Let compound work |
| Max single bet | $75 or 15% of bankroll (whichever is smaller) | Diversification |
| Kelly fraction | 0.50 (half-Kelly) | ~75% growth rate, manageable drawdowns |
| Stop-loss | 30% loss on entry value (current_value < 0.70 * entry_cost) | Wide enough to avoid noise exits |
| Take-profit | 40% gain on entry value (current_value > 1.40 * entry_cost) | Asymmetric risk/reward |
| Min edge | 6% (medium), 9% (low), 4.5% (high) | Only trade when AI has real edge |
| Min liquidity | $5,000 | Avoid slippage |
| Min volume 24h | $50,000 | Only liquid markets |
| Max positions | 5 concurrent | Focus over diversification |
| Correlation cap | 30% in same category | Avoid concentrated exposure |
| Cool-down | 3 consecutive losses → skip 2 cycles | Tilt protection |
| Drawdown breaker | Bankroll < 50% of high-water mark → halt + notify | Catastrophic loss protection |
| Cache invalidation | Invalidate AI cache if market price moves >5% since last analysis | Stale probability protection |
| Cycle interval | 30 minutes | Token-efficient for political markets |
| API hit rate assumption | ~25-30% of cycles find qualifying markets | Explains 12-15 calls/day |

## Cost Structure

| Item | Daily | Monthly |
|---|---|---|
| Claude API (Sonnet, ~12-15 smart calls/day) | ~$0.20 | ~$6 |
| Polygon gas fees | ~$0.05 | ~$1.50 |
| **Total** | **~$0.25** | **~$7.50** |

## Growth Projection (Moderate — 1.5%/day target)

| Day | Bankroll | Note |
|---|---|---|
| 0 | $60 | Starting |
| 30 | $95 | Compound kicking in |
| 60 | $150 | 2.5x |
| 90 | $240 | API cost now negligible |
| 180 | $940 | ~16x |
| 365 | $14,500+ | ~240x (liquidity dependent) |

User can add more USDC at any time — Half-Kelly auto-adjusts position sizes to new bankroll.

## Project Structure

```
polymarket-agent/
├── config.yaml              # All tunable parameters
├── .env                     # Secrets (never committed)
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point, main loop, graceful shutdown
│   ├── config.py            # Pydantic config model
│   ├── market_scanner.py    # Gamma API integration
│   ├── ai_analyst.py        # Claude Sonnet signal engine
│   ├── edge_calculator.py   # Edge detection + direction
│   ├── risk_manager.py      # Kelly sizing, veto logic
│   ├── portfolio.py         # Position tracking, PnL, resolution
│   ├── executor.py          # Order execution (dry/paper/live)
│   ├── order_manager.py     # Pending order tracking, stale cancellation
│   ├── wallet.py            # On-chain ops: balance, allowances, gas
│   ├── trade_logger.py      # JSONL trade logging
│   └── models.py            # Pydantic data models
├── logs/
│   ├── trades.jsonl         # Trade history
│   └── portfolio.jsonl      # Portfolio snapshots
├── tests/
│   ├── test_edge_calculator.py
│   ├── test_risk_manager.py
│   ├── test_kelly.py
│   └── test_market_scanner.py
├── docs/
│   └── superpowers/specs/   # This spec
├── requirements.txt
└── README.md
```

## Module Responsibilities

### market_scanner.py
- Fetch active markets from Gamma API (no auth)
- Filter by tag (politics, geopolitics), volume, liquidity
- Parse JSON string fields (outcomePrices, clobTokenIds)
- Return list of MarketData models

### ai_analyst.py
- Single Claude Sonnet call per cycle with batch of top 5 markets
- Calibrated superforecaster system prompt
- Returns probability + confidence for each market
- Only called when scanner finds qualifying markets (smart call optimization)
- Cache results for 15-30 min to avoid redundant calls

### edge_calculator.py
- Compare AI probability vs market price
- Apply confidence-adjusted thresholds (6%/9%/4.5%)
- Return direction (BUY_YES / BUY_NO / HOLD) + raw edge value

### risk_manager.py
- Half-Kelly position sizing (kelly_fraction=0.50)
- Enforce all Iron Rules: position limits, correlation, cool-down
- Veto power — can reject or downsize any trade
- Track consecutive losses for cool-down trigger

### portfolio.py
- Track open positions with entry price, current price, PnL
- Update midpoints from CLOB API each cycle
- Check stop-loss: trigger when current_value < 0.70 * entry_cost
- Check take-profit: trigger when current_value > 1.40 * entry_cost
- Detect resolved markets (via Gamma API closed status) and claim winnings
- Reconcile local state vs on-chain USDC balance each cycle
- Track high-water mark for drawdown circuit breaker
- Persist to portfolio.jsonl

### order_manager.py
- Track pending GTC orders and their fill status
- Cancel stale unfilled orders after 2 cycles (60 min)
- On FOK exit failure: retry at 2% worse price, then alert user
- Check actual USDC balance before submitting new orders

### wallet.py
- Check on-chain USDC balance (Polygon)
- Monitor MATIC balance for gas
- Set token allowances (USDC, CTF, Exchange contracts)
- Phase 1 setup: generate wallet, guide user through funding

### executor.py
- Three modes: dry_run (log only), paper (simulate with limit fill when price crosses), live (real orders)
- GTC limit orders for entry, FOK market orders for exits
- Never execute real orders in dry_run/paper mode

### trade_logger.py
- Log every decision to trades.jsonl
- Fields: timestamp, market, direction, size, price, edge, confidence, mode, status

### main.py — Lifecycle
- Graceful shutdown on SIGINT/Ctrl+C: finish current cycle, cancel pending orders, save state
- On transient API errors: skip cycle, log error, continue next cycle
- On 3 consecutive API failures: pause 5 min, then retry

## Operating Phases

| Phase | What happens |
|---|---|
| Phase 1: Infrastructure | Project setup, config, wallet generation + funding guide, USDC bridge to Polygon, token allowances, Gamma API connection |
| Phase 2: AI Signal | Claude Sonnet integration, batch analysis, edge calculation |
| Phase 3: Risk Engine | Kelly sizing, portfolio tracker, stop-loss/take-profit |
| Phase 4: Executor | Order engine (dry_run mode), trade logging, main loop |
| Phase 5: Paper Trading | 1-2 weeks simulated trading, validate strategy, track PnL |
| Phase 6: Live | User's explicit approval required. Start with minimum bets. |

## Non-Negotiable Rules

1. Risk manager has absolute veto power — no trade bypasses risk checks
2. Default mode is always dry_run — never auto-switch to live
3. Never hardcode secrets — all credentials via .env
4. Type hints on all functions, Pydantic models for data
5. Log every decision (trade or skip) with reasoning
6. User must explicitly confirm before any live trading begins
7. Drawdown circuit breaker: halt all trading if bankroll drops below 50% of high-water mark
8. Always check on-chain USDC balance before placing orders — never trust local state alone
