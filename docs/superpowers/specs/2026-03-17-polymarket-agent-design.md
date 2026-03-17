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
│  2c. News Scanner                            │
│     └─ Fetch recent headlines (RSS/NewsAPI)│
│     └─ Match to open positions + top mkts  │
│     └─ Breaking news → force AI re-analyze │
│                                             │
│  2d. Whale Tracker (Data API)                │
│     └─ Monitor large positions (>$50K)     │
│     └─ Whale enters → strong signal boost  │
│     └─ Track whale win rate over time      │
│                                             │
│  3. AI Analyst (DUAL Sonnet calls)          │
│     └─ Batch top 5 markets + news context  │
│     └─ Call A: "Why YES?" → pro-probability│
│     └─ Call B: "Why NO?" → anti-probability│
│     └─ Final: weighted average of A and B  │
│     └─ ~4K token input, ~1K output total   │
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
│  6b. Liquidity Provider (idle mode)          │
│     └─ Activates when no edge signals      │
│     └─ Places bid+ask around midpoint      │
│     └─ Earns spread (1-2 cent/share)       │
│     └─ Auto-cancels if price moves >2%     │
│                                             │
│  7. Performance Tracker (self-improving)     │
│     └─ Track win rate, edge accuracy        │
│     └─ Category-level performance           │
│     └─ Auto-adjust: Kelly, min_edge, focus  │
│     └─ Weekly calibration report            │
│                                             │
│  8. Telegram Notifier                        │
│     └─ Trade opened/closed                  │
│     └─ Stop-loss / take-profit triggered    │
│     └─ Drawdown breaker activated           │
│     └─ Daily PnL summary                   │
│                                             │
│  9. Dashboard (web UI)                       │
│     └─ Live portfolio view                  │
│     └─ PnL chart, trade history             │
│     └─ Edge accuracy over time              │
│     └─ Category breakdown                   │
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
| Claude API (Sonnet, ~24-30 dual calls/day) | ~$0.40 | ~$12 |
| Polygon gas fees | ~$0.05 | ~$1.50 |
| **Total** | **~$0.45** | **~$13.50** |

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
│   ├── news_scanner.py      # RSS/NewsAPI headline fetcher
│   ├── whale_tracker.py     # Large position monitoring
│   ├── liquidity_provider.py # Spread earning in idle mode
│   ├── event_cluster.py     # Correlated market grouping
│   ├── trade_logger.py      # JSONL trade logging
│   ├── performance_tracker.py # Win rate, edge accuracy, auto-tuning
│   ├── notifier.py          # Telegram bot notifications
│   ├── dashboard.py         # Flask/FastAPI web dashboard
│   └── models.py            # Pydantic data models
├── logs/
│   ├── trades.jsonl         # Trade history
│   ├── portfolio.jsonl      # Portfolio snapshots
│   └── performance.jsonl    # Edge accuracy, calibration data
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

### news_scanner.py
- Fetch headlines from RSS feeds (Google News, Reuters, AP) and/or NewsAPI
- Match headlines to open positions and top scanned markets by keyword
- On breaking news match: invalidate AI cache for that market, force re-analysis
- News context is passed to AI analyst for enriched probability estimation
- Rate limit: max 1 fetch per cycle (30 min), cache headlines between cycles

### ai_analyst.py (Adversarial Dual-Prompt)
- TWO Claude Sonnet calls per cycle with batch of top 5 markets + news context
- Call A (Pro): "Analyze why this market should resolve YES. Be thorough."
- Call B (Con): "Analyze why this market should resolve NO. Be thorough."
- Final probability: weighted average of both calls, adjusted by argument strength
- Returns probability + confidence for each market
- Only called when scanner finds qualifying markets (smart call optimization)
- Cache results for 15-30 min, invalidate if market price moves >5% or breaking news

### whale_tracker.py
- Query Polymarket Data API for large recent positions (>$50K in a single market)
- Track known whale addresses and their historical win rate
- When a whale opens a position: boost AI confidence in that direction
- Signal weight: whale_signal = 0.15 (blended into final probability)
- Only follow whales with >55% historical win rate
- Log whale movements to trades.jsonl for later analysis

### event_cluster.py
- Group related markets into clusters using event_id from Gamma API
- Example: "Trump wins 2028", "Republicans win House", "Democrats win Senate" → one cluster
- AI analyst receives cluster context: analyze conditional probabilities together
- Edge calculator checks cross-market consistency within cluster
- Arbitrage detection: if sum of all outcomes in a cluster ≠ 1.00 → flag opportunity
- Feed cluster tags to risk_manager for smarter correlation tracking

### liquidity_provider.py (Idle Mode)
- Activates only when edge calculator returns HOLD for all markets in a cycle
- Places symmetric limit orders around midpoint: bid at mid-1cent, ask at mid+1cent
- Max exposure per market: 5% of bankroll (small, spread-earning only)
- Auto-cancel all LP orders if market price moves >2% from placement price
- Auto-cancel all LP orders when edge signals appear (priority to edge trading)
- Track LP profit separately in trade logs (mode: "liquidity_provider")
- Only operates on markets with spread > 3 cents (otherwise not worth it)

### edge_calculator.py
- Compare AI probability vs market price
- Apply confidence-adjusted thresholds (6%/9%/4.5%)
- Blend in whale signal if available (15% weight)
- Use event cluster context for cross-market consistency
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

### performance_tracker.py (Self-Improving)
- Track per-trade outcomes: did AI probability match actual resolution?
- Calculate rolling win rate, edge accuracy, Brier score
- Category-level breakdown: politics vs geopolitics vs other
- Auto-tuning (weekly): if win rate < 50% in a category → raise min_edge for that category
- Auto-tuning: if edge accuracy is consistently off by X% → adjust Kelly fraction
- Generate weekly calibration report to logs/performance.jsonl
- If a category underperforms for 2+ weeks → auto-exclude from scanning

### notifier.py (Telegram Bot)
- Send notifications via Telegram Bot API (free, requires bot token + chat_id in .env)
- Events: trade opened, trade closed, stop-loss triggered, take-profit hit
- Alerts: drawdown breaker activated, 3 consecutive losses, API failures
- Daily summary: PnL, open positions, win rate, bankroll
- User can reply /status to get current portfolio snapshot

### dashboard.py (Web UI)
- Lightweight Flask/FastAPI app serving on localhost
- Live portfolio view: open positions, unrealized PnL, current prices
- **Bankroll line graph**: toggleable daily/weekly/monthly view with compound growth curve overlay
  - X axis: time, Y axis: bankroll value
  - Overlay: projected growth line (1.5%/day target) vs actual
  - Drawdown periods highlighted in red
  - Deposit events marked as vertical markers
- Trade history table: sortable, filterable by market/direction/outcome
- Edge accuracy chart: AI predicted probability vs actual resolution over time
- Category breakdown: win rate and PnL by politics/geopolitics/other
- Read-only — no trading actions from dashboard

### main.py — Lifecycle
- Graceful shutdown on SIGINT/Ctrl+C: finish current cycle, cancel pending orders, save state
- On transient API errors: skip cycle, log error, continue next cycle
- On 3 consecutive API failures: pause 5 min, then retry

## Operating Phases

| Phase | What happens |
|---|---|
| Phase 1: Infrastructure | Project setup, config, wallet generation + funding guide, USDC bridge to Polygon, token allowances, Gamma API connection |
| Phase 2: AI Signal | Dual-prompt Claude Sonnet, news scanner, whale tracker, event clustering, edge calculation |
| Phase 3: Risk Engine | Kelly sizing, portfolio tracker, stop-loss/take-profit, drawdown breaker |
| Phase 3b: Liquidity Provider | Idle-mode spread earning, symmetric orders, auto-cancel logic |
| Phase 4: Executor | Order engine (dry_run mode), order manager, trade logging, main loop |
| Phase 5: Notifications | Telegram bot setup, trade alerts, daily PnL summary |
| Phase 6: Paper Trading | 1-2 weeks simulated trading, validate strategy, track PnL |
| Phase 7: Performance Tracker | Self-improving calibration, auto-tuning, category analysis |
| Phase 8: Dashboard | Web UI for portfolio monitoring, PnL charts, edge accuracy |
| Phase 9: Live | User's explicit approval required. Start with minimum bets. |

## Non-Negotiable Rules

1. Risk manager has absolute veto power — no trade bypasses risk checks
2. Default mode is always dry_run — never auto-switch to live
3. Never hardcode secrets — all credentials via .env
4. Type hints on all functions, Pydantic models for data
5. Log every decision (trade or skip) with reasoning
6. User must explicitly confirm before any live trading begins
7. Drawdown circuit breaker: halt all trading if bankroll drops below 50% of high-water mark
8. Always check on-chain USDC balance before placing orders — never trust local state alone
