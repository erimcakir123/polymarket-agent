# Product Requirements Document (PRD)
# Optimus Claudeus — Polymarket Prediction Market Trading Agent

**Version:** 2.0
**Date:** 2026-03-25
**Status:** In Testing (Dry-Run → Paper → Live pipeline)
**Goal:** Passive income via automated prediction market trading on Polymarket

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Product Vision & Goals](#3-product-vision--goals)
4. [System Architecture](#4-system-architecture)
5. [Core Agent Loop](#5-core-agent-loop)
6. [Market Discovery & Filtering](#6-market-discovery--filtering)
7. [AI Probability Engine](#7-ai-probability-engine)
8. [Edge Detection & Entry Logic](#8-edge-detection--entry-logic)
9. [Risk Management](#9-risk-management)
10. [Position Sizing (Kelly Criterion)](#10-position-sizing-kelly-criterion)
11. [Exit System (4-Layer Match-Aware)](#11-exit-system-4-layer-match-aware)
12. [Re-Entry Farming](#12-re-entry-farming)
13. [Scouting & Pre-Game Analysis](#13-scouting--pre-game-analysis)
14. [Special Strategies (FAR/FAV/VS)](#14-special-strategies-farfavvs)
15. [Data Sources & API Integration](#15-data-sources--api-integration)
16. [Real-Time Systems](#16-real-time-systems)
17. [Self-Improvement Engine](#17-self-improvement-engine)
18. [Dashboard & Monitoring](#18-dashboard--monitoring)
19. [Testing & Go-Live Pipeline](#19-testing--go-live-pipeline)
20. [Configuration Reference](#20-configuration-reference)
21. [File & Module Inventory](#21-file--module-inventory)
22. [Known Limitations & Open Questions](#22-known-limitations--open-questions)
23. [Future Roadmap](#23-future-roadmap)
24. [Appendix: API Cost Analysis](#24-appendix-api-cost-analysis)

---

## 1. Executive Summary

**Optimus Claudeus** is a Python-based autonomous trading agent for Polymarket — a decentralized prediction market platform on Polygon. The bot discovers sports/esports markets, estimates event probabilities using Claude AI (dual-prompt framework), compares them against market prices to find edges, and executes trades via the CLOB (Central Limit Order Book) API.

### Key Differentiators
- **AI-powered probability estimation** — Claude Sonnet with sport-specific prompts, not just odds scraping
- **4-layer match-aware exit system** — Exits adapt to match progress, score, momentum, and entry price
- **3-tier re-entry farming** — Harvests additional profit from price dips after profitable exits
- **Multi-source data cascade** — PandaScore → HLTV/VLR → ESPN → The Odds API with graceful fallback
- **Real-time WebSocket price feed** — Sub-second price updates for critical positions
- **Self-improvement loop** — Auto-calibration after each testing checkpoint
- **Budget-controlled AI spend** — Monthly/sprint budgets with hard caps ($48/month)

### Current Numbers
| Metric | Value |
|--------|-------|
| Codebase | ~13,600 lines Python |
| Test suite | ~2,300 lines, 30+ files |
| Source modules | 45+ |
| Max concurrent positions | 5 (standard) + 5 (volatility swing) + 2 (FAR) |
| Initial bankroll | $60 USDC |
| AI model | Claude Sonnet 4 |
| Supported markets | Sports (NBA, NFL, MLB, NHL, soccer, tennis) + Esports (CS2, LoL, Dota2, Valorant) |

---

## 2. Problem Statement

Prediction markets offer persistent mispricings, especially in:
1. **Esports tier-2/3 matches** — Low analyst coverage, amateur bookmaker lines
2. **Live sports with score context** — Market reacts slowly to in-game developments
3. **Volatile pre-match periods** — Price swings 2-4 hours before match start
4. **Penny tokens ($0.01-$0.02)** — Overlooked by large traders, 2-5x upside

Manual trading is:
- Time-intensive (markets run 24/7 across timezones)
- Emotionally biased (tilt after losses, FOMO after wins)
- Slow to react (position management requires constant monitoring)

**Solution:** An autonomous agent that runs 24/7, makes data-driven decisions, manages risk systematically, and continuously self-improves.

---

## 3. Product Vision & Goals

### Primary Goal
Generate consistent passive income from Polymarket prediction markets with controlled risk.

### Success Criteria (Testing Phase)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Win rate | >57% | Resolved trades (win/loss) |
| Brier score | <0.22 | |AI_prob - actual|² averaged |
| Max drawdown | <-20% | Peak-to-trough equity |
| Monthly ROI | >15% | Net PnL / initial bankroll |
| AI budget | <$48/month | Claude API cost tracking |

### Go-Live Decision Gate
At Day 19-20 of testing (Checkpoint 6): If win rate >57% and Brier score <0.22, transition from dry-run to paper to live.

### Non-Goals (Explicit Exclusions)
- **NOT** high-frequency trading — cycle time 5-60 min, not milliseconds
- **NOT** market making — no providing liquidity, only taking positions
- **NOT** multi-platform — Polymarket CLOB only (no Kalshi, Metaculus, etc.)
- **NOT** non-moneyline bets — no spreads, totals, props, only match winner/series winner
- **NOT** political/crypto markets — sports and esports only (for now)

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAIN AGENT LOOP                         │
│                          (main.py)                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Heavy    │  │  Light   │  │  Scout   │  │  Self-       │   │
│  │  Cycle    │  │  Cycle   │  │  Sched.  │  │  Improve     │   │
│  │  (~4h)    │  │  (~30m)  │  │  (4x/d)  │  │  (checkpt)   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │              │              │               │           │
│       ▼              ▼              ▼               ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    DECISION ENGINE                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │   │
│  │  │ AI       │ │ Edge     │ │ Risk     │ │ Liquidity │  │   │
│  │  │ Analyst  │ │ Calc     │ │ Manager  │ │ Check     │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │              │              │               │           │
│       ▼              ▼              ▼               ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    EXECUTION LAYER                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │   │
│  │  │ Executor │ │ Portfolio│ │ Scale-   │ │ Match     │  │   │
│  │  │ (CLOB)   │ │ Tracker  │ │ Out/In   │ │ Exit (4L) │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │              │              │               │           │
│       ▼              ▼              ▼               ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    DATA LAYER                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │   │
│  │  │ Gamma    │ │ PandaS.  │ │ ESPN     │ │ Odds API  │  │   │
│  │  │ API      │ │ + HLTV   │ │ (free)   │ │ (fallback)│  │   │
│  │  │          │ │ + VLR    │ │          │ │           │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐               │   │
│  │  │ WebSocket│ │ News     │ │ Manip.   │               │   │
│  │  │ Feed     │ │ Scanner  │ │ Guard    │               │   │
│  │  └──────────┘ └──────────┘ └──────────┘               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│  Flask Dashboard │          │  Telegram Alerts  │
│  localhost:5050  │          │  (optional)       │
└──────────────────┘          └──────────────────┘
```

### Tech Stack
| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| AI | Claude Sonnet 4 (Anthropic API) |
| Configuration | YAML + Pydantic v2 |
| Blockchain | Polygon (eth-account, py-clob-client) |
| Dashboard | Flask 3.0 |
| Real-time | websockets (async) |
| HTTP | httpx (async), requests |
| News parsing | feedparser, trafilatura |
| Testing | pytest 8.0 |

---

## 5. Core Agent Loop

### Cycle Types

#### Heavy Cycle (Full Analysis) — ~every 4 hours
1. **Discover** — Fetch eligible markets from Gamma API (max 20/batch)
2. **Pre-filter** — Remove impossible/manipulated/dead markets
3. **Analyze** — Claude AI dual-prompt probability estimation per market
4. **Edge detect** — Compare AI probability vs market price (min 6% edge)
5. **Risk check** — Kelly sizing, correlation cap, cooldown, drawdown halt
6. **Execute** — Place order via CLOB (or simulate in dry_run/paper mode)
7. **Exit check** — All open positions through 4-layer exit system
8. **Re-entry** — Scan re-entry pool for dip opportunities
9. **Scout** — Pre-game analysis for upcoming matches

#### Light Cycle (Fast Polling) — every 30 min (5 min when positions are live)
1. **Price update** — Poll CLOB for current prices (supplemented by WebSocket)
2. **Stop-loss/Take-profit** — Check all positions against SL/TP triggers
3. **Scale-out** — Check if any position hit partial exit tiers
4. **Match state** — Fetch live scores from PandaScore
5. **Halftime exit** — Check if losing at halftime for early exit
6. **Pending resolution** — Detect markets about to resolve

#### Dynamic Cycle Interval
| Condition | Interval |
|-----------|----------|
| Default | 30 min |
| Live positions on CLOB | 5 min |
| Breaking news detected | 10 min |
| Position near stop-loss | 15 min |
| Scout approaching (pre-game) | 5 min |
| Night mode (00:00-06:00 UTC) | 60 min |

### State Persistence
All state is JSON-persisted to survive restarts:
- `logs/positions.json` — Open positions
- `logs/realized_pnl.json` — Closed trades
- `logs/reentry_pool.json` — Re-entry candidates
- `logs/scout_queue.json` — Pre-analyzed matches
- `logs/ai_budget.json` — API cost tracking
- `logs/blacklist.json` — Tiered ban system
- `logs/candidate_stock.json` — AI-analyzed candidates
- `logs/bot_status.json` — Current cycle state

---

## 6. Market Discovery & Filtering

### Gamma API Integration
- **Endpoint:** `https://gamma-api.polymarket.com/events`
- **Auth:** None (free, ~10K req/month)
- **Query modes:**
  - Tag-based: Sports (tag_id=1), Esports (tag_id=64)
  - Volume-sorted: Top volume across all categories
  - Pagination: offset/limit for large result sets

### Pre-Filters (Applied Before AI Analysis)
| Filter | Threshold | Reason |
|--------|-----------|--------|
| Min volume 24h | $1,000 | Dead markets (note: esports exempt — volume spikes only ~2h before match) |
| Min liquidity | $1,000 | Can't exit without slippage |
| Max duration | 14 days | Long-dated markets have stale analysis |
| Moneyline only | Pattern match | No spreads, totals, props — only match/series winner |
| Live on CLOB | Required | Market must be actively trading |
| Not self-resolving | Pattern match | Politicians, celebrities who can influence outcome |
| Not resolved/closed | Status check | Skip already-settled markets |

### Supported Market Categories

#### Sports (via ESPN + The Odds API)
NBA, NFL, MLB, NHL, College Basketball, Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, MLS, A-League, Tennis (ATP/WTA), UFC/MMA

#### Esports (via PandaScore + HLTV + VLR)
CS2, League of Legends, Dota 2, Valorant, Overwatch, PUBG, R6 Siege, Rocket League, Mobile Legends, Wild Rift, StarCraft 2

---

## 7. AI Probability Engine

### Model
- **Primary:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- **Max tokens:** 1,024 per call
- **Budget:** $48/month ($24 per 2-week sprint)
- **Cost tracking:** Input @ $3/MTok, Output @ $15/MTok

### Dual-Prompt Framework

The AI receives a structured system prompt that forces two-sided analysis:

```
1. Build strongest case FOR the event (Pro argument)
2. Build strongest case AGAINST the event (Con argument)
3. Synthesize into a probability estimate (0.00-1.00)
4. Assign confidence grade (C / B- / B+ / A)
```

### Sport-Specific Prompt Rules
| Category | Rules Included |
|----------|---------------|
| Sports | Team form (last 5), H2H, home/away, injury reports, tournament tier, playoff pressure |
| Esports | BO format (BO1 volatile, BO3 standard), map pool, roster changes, online vs LAN, tier-2/3 data scarcity |
| Politics | Base rates, precedent, voter stability, incumbent bias, polling aggregation |

### Confidence Tiers
| Grade | Meaning | Edge Multiplier | Kelly Base |
|-------|---------|-----------------|------------|
| C | Low confidence (uncertain) | 1.5× (higher edge required) | 8% |
| B- | Moderate confidence | 1.0× (standard) | 12% |
| B+ | High confidence | 0.85× (lower edge ok) | 20% |
| A | Very high confidence (rare) | 0.75× (most aggressive) | 25% |

### Caching & Budget Protection
- **Cache TTL:** 15 minutes per market
- **Invalidation:** >5% price move OR timeout
- **Pool-full skip:** If all position slots are filled, skip AI analysis (save budget) — *planned, not yet implemented*
- **Sprint budget alert:** Warnings at 50%, 75%, 100% of sprint budget

### AI Output (AIEstimate)
```python
{
    "probability": 0.72,          # AI's estimated probability
    "confidence": "B+",           # Confidence grade
    "reasoning_pro": "...",       # Case for event
    "reasoning_con": "...",       # Case against event
    "key_evidence_for": [...],    # Supporting evidence
    "key_evidence_against": [...]  # Counter-evidence
}
```

---

## 8. Edge Detection & Entry Logic

### Edge Calculation
```
raw_edge = ai_probability - market_yes_price   (for BUY_YES)
raw_edge = market_yes_price - ai_probability   (for BUY_NO)

adjusted_min_edge = base_min_edge × confidence_multiplier
```

### Entry Decision Matrix
| Condition | Action |
|-----------|--------|
| raw_edge > adjusted_min_edge | BUY_YES signal |
| raw_edge < -adjusted_min_edge | BUY_NO signal |
| Otherwise | HOLD (no trade) |

### Default Thresholds
| Parameter | Value |
|-----------|-------|
| Base min edge | 6% |
| Min edge for BUY_NO (swap) | 8.5% |
| Confidence C multiplier | 1.5× → 9% edge required |
| Confidence B- multiplier | 1.0× → 6% edge required |
| Confidence B+ multiplier | 0.85× → 5.1% edge required |
| Confidence A multiplier | 0.75× → 4.5% edge required |

### Bookmaker Calibration (Optional Enhancement)
When bookmaker odds are available (via The Odds API):
- Compare AI probability vs bookmaker implied probability
- If both agree → boost confidence by 1 tier
- If they diverge significantly → flag for review (wider edge needed)

### Edge Decay
For positions held long-term: AI probability decays toward 50% (market consensus) over time, preventing stale analyses from justifying hold decisions indefinitely.

---

## 9. Risk Management

### Hierarchy of Risk Controls

```
Level 1: Signal Validation (sanity_check.py)
    └── AI probability in [0,1]? Confidence valid? Edge makes sense?

Level 2: Risk Manager Veto (risk_manager.py)
    └── Cooldown active? Max positions? Already in market? Correlation cap?

Level 3: Circuit Breaker (circuit_breaker.py)
    └── Daily loss >-8%? Hourly loss >-5%? Consecutive losses >4?

Level 4: Liquidity Validation (liquidity_check.py)
    └── Order book deep enough? Size >20% of book? Slippage?

Level 5: Manipulation Guard (manipulation_guard.py)
    └── Self-resolving? Single-source news? Low-liquidity pump?

Level 6: Match Exit System (match_exit.py)
    └── 4-layer graduated exit based on match progress
```

### Portfolio Constraints
| Constraint | Value | Reason |
|------------|-------|--------|
| Max positions | 5 | Concentration risk |
| Max per-match exposure | 15% of bankroll | Correlation protection |
| Max single bet | $75 or 5% of bankroll | Kelly cap |
| Min bet size | $5 | Polymarket minimum |
| Drawdown halt | -50% | Circuit breaker |
| Daily loss halt | -8% | Circuit breaker |
| Hourly loss halt | -5% | Circuit breaker |
| Consecutive loss cooldown | 3 losses → 2 cycle pause | Tilt prevention |

### Blacklist System (3-Tier)
| Tier | Duration | Scope | Trigger |
|------|----------|-------|---------|
| Soft | 1-2 days | Category-level | Category Brier score drops |
| Hard | 1-5 days | Market-specific | Lost 2× in a row on same market |
| Permanent | Forever | Market-specific | User exclusion, external event |

---

## 10. Position Sizing (Kelly Criterion)

### Formula
```
Full Kelly = (p × b - q) / b
where:
    p = AI probability of winning
    q = 1 - p
    b = (1 - market_price) / market_price  (implied odds)

Fractional Kelly = Full_Kelly × kelly_fraction
Position Size = min(
    Fractional_Kelly × bankroll,
    max_single_bet_usdc,
    bankroll × max_bet_pct
)
```

### Adaptive Kelly (Dynamic Fraction)
| Factor | Adjustment |
|--------|------------|
| Base by confidence | C=8%, B-=12%, B+=20%, A=25% |
| High conviction (AI >80%) | +5% |
| Esports | ×0.90 (more volatile) |
| Re-entry | ×0.80 (capital already at risk) |
| FAR position | ×0.70 (locked for hours/days) |
| Final range | Clamped to [5%, 30%] |

### Scale-In (Tranched Entry)
For high-conviction trades:
1. Enter with 60% of intended size
2. After 3 cycles + position profitable (>2% PnL) → add remaining 40%
3. If position drops before tranche 2 → stay at 60% (smaller loss)

### Scale-Out (Partial Exit)
| Tier | Trigger | Action |
|------|---------|--------|
| 1 (Risk-Free) | +25% PnL | Sell 40% of position |
| 2 (Profit-Lock) | +50% PnL | Sell 50% of remaining |
| 3 (Final) | Exit trigger | Sell all remaining |

---

## 11. Exit System (4-Layer Match-Aware)

This is the most complex and critical subsystem. Each layer operates independently; the first triggered layer exits the position.

### Layer 1: Catastrophic Floor
- **Trigger:** current_price < entry_price × 0.50
- **Exemption:** Underdog entries (<25¢) — already high-risk by design
- **Purpose:** Hard stop to prevent total loss

### Layer 2: Progress-Based Graduated Stop-Loss
Adjusts SL threshold based on match elapsed time:

| Match Progress | SL Threshold | Rationale |
|----------------|-------------|-----------|
| 0-25% | -40% | Early game: high volatility normal |
| 25-50% | -30% | Thesis should be playing out |
| 50-75% | -20% | Strong directional signal expected |
| 75-100% | -15% | Late game: limited recovery time |

**Entry-price-adjusted multiplier:**
| Entry Price | Multiplier | Effect |
|-------------|-----------|--------|
| <15¢ | 0.70× | Much wider SL (underdog) |
| 15-30¢ | 0.85× | Wider SL |
| 30-50¢ | 1.00× | Standard |
| 50-70¢ | 1.20× | Tighter SL |
| >70¢ | 1.50× | Very tight SL (expensive entry) |

### Layer 3: Never-In-Profit Guard
For positions that have **never** been profitable:
- Activates at 70% match elapsed
- Thresholds:
  - Standard: exit if current < entry × 0.90
  - Cheap entries (<25¢): exit if current < entry × 0.75

### Layer 4: Hold-to-Resolve Revocation
For scouted positions with "hold to resolve" flag:
- **Revoke hold** if:
  - Losing by 2+ maps/sets AND match >60% elapsed
  - Price dropped >40% from entry
  - Momentum: 5+ consecutive down cycles
- **Restore hold** if:
  - Price recovers to within 10% of entry
  - Score equalizes
  - Temporary revocation (< 3 cycles since revoke)

### Additional Exit Mechanisms
| Mechanism | Trigger | Action |
|-----------|---------|--------|
| Ultra-low guard | Entry <9¢, elapsed >90%, current <5¢ | Immediate exit |
| Momentum tightening | 3+ down cycles + 5¢ drop | SL × 0.75 |
| Extreme momentum | 5+ down cycles + 10¢ drop | SL × 0.60 |
| Pending resolution | Price near $0.95 or $0.05 | Hold (likely resolving) |
| Match ended | Event marked ended | Check final state, exit if losing |

### Game-Specific Duration Table
Used to calculate `elapsed_pct` for match-aware exits:

| Game | BO1 | BO3 | BO5 |
|------|-----|-----|-----|
| CS2 | 40 min | 130 min | 200 min |
| Valorant | 50 min | 140 min | 220 min |
| LoL | 35 min | 100 min | 160 min |
| Dota 2 | 45 min | 130 min | 210 min |

| Sport | Duration |
|-------|----------|
| Soccer | 95 min |
| Basketball (NBA) | 150 min |
| Football (NFL) | 180 min |
| Baseball | 180 min |
| Tennis | 90-180 min (varies) |
| Hockey | 150 min |

### σ-Trailing Stop (Volatility-Based)
- Tracks peak price reached for each position
- Uses rolling price history to calculate volatility (standard deviation)
- Trailing stop: peak_price - (N × σ), where N scales with position age
- Only activates if position was ever in profit (prevents false triggers)

---

## 12. Re-Entry Farming

After a profitable exit, the system watches for price dips to re-enter the same market at a lower price.

### 3-Tier Dip Detection
| Tier | Dip Required | Re-entry Size | Stabilization |
|------|-------------|---------------|---------------|
| 1 | 4¢ drop OR 6% drop | 80% of original | 2 cycles |
| 2 | 7¢ drop OR 10% drop | 60% of original | 3 cycles |
| 3 | 11¢ drop OR 15% drop | 40% of original | 3 cycles |

### Guardrails
- **Thesis broken:** If price drops below (original_entry - 5¢), block re-entry (thesis invalid)
- **Price extremes:** No re-entry if token >85¢ or <15¢
- **Profit protection:** Max re-entry risk = 50% of realized profit from original trade
- **Stale analysis:** Block if original AI analysis >240 cycles old (~4 hours)
- **Daily limit:** Max 5 re-entries per day across all markets
- **Per-market limit:** Max 2 re-entries per market

### Score-Aware Re-Entry (New)
When PandaScore live match state is available:
- **Map break pause:** If match is between maps (halftime/side swap), WAIT — don't re-enter during uncertainty
- **Score adjustment:** Apply ±5% per map difference to AI probability
  - Example: AI estimated 65% for Team A, but Team A is down 0-1 in BO3 → adjusted to 60%
  - Direction-aware: BUY_NO positions flip the adjustment

### Re-Entry Pool Lifecycle
```
Profitable Exit → Add to Pool → Monitor Price → Dip Detected?
    ├── YES → Check guardrails → Place re-entry order → Track
    └── NO → Age out (240 cycles) → Remove from pool
```

---

## 13. Scouting & Pre-Game Analysis

### Scout Scheduler
- Runs 4× daily (00:00, 06:00, 12:00, 18:00 UTC)
- Looks 24 hours ahead for upcoming matches
- Pre-analyzes via Claude AI at lower urgency (can use cache)
- Results saved to `logs/scout_queue.json`

### Scouted Entry Flow
1. Scout detects upcoming NBA game at 01:00 UTC
2. AI analyzes: "Lakers 72% to win, B+ confidence"
3. At 23:00 UTC, Polymarket lists "Lakers vs Warriors" market
4. Scanner matches market to scout queue → instant entry
5. Position flagged as `scouted = True` → hold-to-resolve behavior

### Scouted Position Behavior
- **Hold-to-resolve:** Don't exit early unless thesis breaks (Layer 4 revocation)
- **Confidence gate:** Only scouted entries with B+ or higher get hold-to-resolve
- **AI certainty gate:** AI probability must be >60% (not a coin flip)

---

## 14. Special Strategies (FAR/FAV/VS)

### FAR (Far-Advance) Strategy
Targets markets 6-336 hours before match start:
- **Edge requirement:** 10% (higher than standard 6%)
- **Confidence floor:** B- or higher
- **Dedicated slots:** 2 (separate from main 5)
- **SL/TP:** -30% / +40%

**Penny Alpha:** Specifically targets $0.01-$0.02 tokens:
- $0.01 tokens → hold for 5× ($0.05)
- $0.02 tokens → hold for 2× ($0.04)
- 5% bankroll allocation

### FAV (Favorite) Strategy
Standard moneyline bets with clear favorite (AI >65%):
- Normal slot allocation (part of main 5)
- Standard SL/TP and exit rules
- Enhanced with bookmaker calibration when available

### VS (Volatility Swing) Strategy
Targets volatile pre-match period:
- **Token price range:** $0.10-$0.50
- **Time to match:** <24 hours
- **Dedicated slots:** 5
- **SL/TP:** -20% / +60% (tight SL, wide TP)
- **Polling interval:** 5 min (fast)
- Separate from main positions — own slot reservation

---

## 15. Data Sources & API Integration

### API Cascade Architecture
```
Primary Source          Fallback 1          Fallback 2
───────────────        ──────────          ──────────
PandaScore (esports) → HLTV/VLR scraper → Manual (no data)
ESPN (trad. sports)  → The Odds API      → Manual (no data)
Gamma API (markets)  → (none)            → (none)
Tavily (news)        → NewsAPI           → GNews → RSS feeds
```

### API Inventory

| API | Purpose | Auth | Free Tier | Monthly Cost | Status |
|-----|---------|------|-----------|-------------|--------|
| **Anthropic Claude** | Probability estimation | API key | $5 free credits | ~$48/mo budget | ✅ Active |
| **Gamma API** | Market discovery, events | None | ~10K req/mo | Free | ✅ Active |
| **Polymarket CLOB** | Order execution, books | API creds | Unlimited | Free | ✅ Active |
| **CLOB WebSocket** | Real-time prices | None | Unlimited | Free | ✅ Active |
| **ESPN** | Traditional sports stats | None | Unlimited | Free | ✅ Active |
| **PandaScore** | Esports data, live scores | API key | 1000 req/hr | €150/mo (paid) | ✅ Active |
| **The Odds API** | Bookmaker odds | API key | 500 credits/mo | $30/mo (20K) | ✅ Active (free tier) |
| **Tavily** | LLM-optimized news search | API key | 1000 credits/mo | Free tier | ✅ Active |
| **NewsAPI** | News aggregation | API key | 500 req/day | $29/mo | ✅ Active (free tier) |
| **GNews** | Google News API | API key | 150 req/day | Free tier | ✅ Active (free tier) |
| **RSS Feeds** | News fallback | None | Unlimited | Free | ✅ Active |
| **HLTV scraper** | CS2 tier-2/3 data | None | Unlimited | Free | ✅ Active (scrape risk) |
| **VLR scraper** | Valorant tier-2/3 data | None | Unlimited | Free | ✅ Active (scrape risk) |
| **SportsGameOdds** | Traditional sports odds | API key | 2500 obj/mo | $99/mo | 🔲 Key exists, not integrated |
| **Riot Games API** | LoL/Valorant official | None | Unlimited | Free | 🔲 Planned |
| **OpenDota API** | Dota 2 data | None | 60 req/min | Free | 🔲 Planned |

### Data Flow Per Market
```
Gamma API
  └── MarketData (question, prices, volume, slug, event metadata)
        │
        ├── ESPN/PandaScore
        │     └── Team stats, form, H2H, seeding
        │
        ├── The Odds API
        │     └── Bookmaker implied probability
        │
        ├── News Scanner (Tavily → NewsAPI → GNews → RSS)
        │     └── Breaking news, injury reports
        │
        └── Claude AI
              └── AIEstimate (probability, confidence, reasoning)
```

---

## 16. Real-Time Systems

### WebSocket Price Feed
- **URL:** `wss://ws-subscriptions-clob.polymarket.com/ws/market`
- **Protocol:** JSON messages over WebSocket
- **Subscribes to:** All active position token_ids
- **Updates:** Price changes, order book snapshots
- **Reconnect:** Exponential backoff (2s → 60s max)
- **Heartbeat:** 30s ping/pong
- **Stale detection:** 120s no message → reconnect

**Message Types:**
| Type | Data | Action |
|------|------|--------|
| `price_change` | token_id, price | Update position current_price |
| `book` | bids[], asks[] | Update bid/ask spread |

### PandaScore Live Match State
- **Endpoint:** `/{game_slug}/matches/running`
- **Cache:** 45 seconds
- **Data returned:**
  ```python
  {
      "match_id": "...",
      "status": "running",
      "map_number": 2,
      "total_maps": 3,
      "map_score": {"team_a": 1, "team_b": 0},
      "is_break": false,        # Between maps?
      "break_type": null,       # "halftime" | "tactical" | null
      "current_game_status": "running",
      "team_a_score": 1,
      "team_b_score": 0
  }
  ```
- **Uses:**
  - Match-aware exits (actual score vs time-based guess)
  - Halftime exit decisions (actual map score)
  - Re-entry pause during map breaks
  - Score-aware probability adjustment

---

## 17. Self-Improvement Engine

### Overview
After each testing checkpoint, the bot analyzes its own performance and proposes ONE parameter change.

### Process
1. **Collect** — All resolved trades from outcome tracker
2. **Analyze** — Win rate, Brier score, by category/confidence/edge range
3. **Identify weakness** — Categories with <50% win rate, miscalibrated confidence
4. **Propose** — Single parameter change (e.g., "increase min_edge for esports from 6% to 8%")
5. **Log** — Record to `logs/experiments.tsv` for tracking

### Metrics Tracked
| Metric | Formula | Target |
|--------|---------|--------|
| Win rate | wins / total_resolved | >57% |
| Brier score | mean(|AI_prob - actual|²) | <0.22 |
| Calibration | P(event \| AI says 70%) ≈ 70% | Perfect = 45° line |
| Category breakdown | Win rate per sport/esports | Identify weak categories |
| Edge efficiency | Realized PnL / theoretical edge | >60% |

### Experiment Format
```tsv
date    parameter    old_value    new_value    reasoning    result
2026-03-15    esports_min_edge    0.06    0.08    Low win rate on tier-2 esports    pending
```

---

## 18. Dashboard & Monitoring

### Flask Dashboard (localhost:5050)
| Route | Data |
|-------|------|
| `/` | Main dashboard HTML |
| `/api/positions` | Open positions with live prices |
| `/api/trades` | Trade history |
| `/api/portfolio` | Equity snapshots |
| `/api/performance` | Win rate, PnL, Brier score |
| `/api/budget` | AI API cost tracking |
| `/api/slots` | Slot allocation (main/FAR/VS) |

### Dashboard Features
- Real-time position monitoring (auto-refresh every 10s)
- Live match scores and countdown timers
- PnL tracking (realized + unrealized)
- AI budget consumption (bar charts)
- Slot visualization (filled/empty/reserved)
- Trade history with entry/exit reasons

### Telegram Notifications (Optional)
- Trade entry alerts
- Trade exit alerts (with PnL)
- Circuit breaker triggers
- Milestone achievements
- Requires `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in .env

---

## 19. Testing & Go-Live Pipeline

### 28-Day Testing Roadmap

| Day | Checkpoint | Action | Gate |
|-----|-----------|--------|------|
| 1 | Start | Bot launched in dry_run | — |
| 3 | CP1 | First data review | Continue |
| 5 | CP2 | Baseline complete | **BOT PAUSES** for review |
| 5-7 | Optimization | Self-improve runs | Apply 1 change |
| 8-9 | CP3 | Post-optimization data | Continue |
| 11-12 | CP4 | Comparison (pre vs post) | **BOT PAUSES** for review |
| 12-14 | Fine-tuning | Second optimization | Apply 1 change |
| 15-16 | CP5 | Stability check | Continue |
| 19-20 | CP6 | **GO/NO-GO DECISION** | Win rate >57%? |
| 21+ | Live | Transition to paper → live | Manual approval |

### Mode Progression
```
DRY_RUN (simulated execution, no real orders)
    ↓ (after CP6 approval)
PAPER (tracked execution, no real USDC)
    ↓ (after 1 week paper with consistent results)
LIVE (real USDC on Polygon)
```

### Approval Mechanism
- Bot automatically pauses after N bets (`bets_since_approval` counter)
- Writes `AWAITING_APPROVAL` flag file
- User reviews positions, approves in dashboard
- Counter resets, bot resumes

---

## 20. Configuration Reference

### config.yaml Structure
```yaml
mode: dry_run                    # dry_run | paper | live
initial_bankroll: 60.0           # Starting USDC

cycle:
  default_interval_min: 30       # Main cycle interval
  breaking_news_interval_min: 10 # During breaking news
  near_stop_loss_interval_min: 15 # Near SL positions
  night_interval_min: 60         # 00:00-06:00 UTC
  night_hours: [0, 1, 2, 3, 4, 5, 6]

scanner:
  min_volume_24h: 1000           # Low (esports volume spikes 2h before match)
  min_liquidity: 1000
  max_markets_per_cycle: 20
  max_duration_days: 14
  prefer_short_duration: true
  allowed_categories: []          # Empty = all; ["sports", "esports"]

ai:
  model: claude-sonnet-4-20250514
  max_tokens: 1024
  cache_ttl_min: 15
  cache_invalidate_price_move_pct: 0.05
  batch_size: 5
  monthly_budget_usd: 48.0
  sprint_budget_usd: 24.0

edge:
  min_edge: 0.06                 # 6% minimum
  confidence_multipliers:
    C: 1.5
    B-: 1.0
    B+: 0.85
    A: 0.75
  min_edge_swap: 0.085           # Higher for BUY_NO

risk:
  kelly_fraction: 0.25
  max_single_bet_usdc: 75
  max_bet_pct: 0.05
  max_positions: 5
  correlation_cap_pct: 0.30
  stop_loss_pct: 0.30
  take_profit_pct: 0.40
  consecutive_loss_cooldown: 3
  drawdown_halt_pct: 0.50
  esports_stop_loss_pct: 0.50
  max_daily_reentries: 5
  max_market_reentries: 2

volatility_swing:
  enabled: true
  stop_loss_pct: 0.20
  take_profit_pct: 0.60
  reserved_slots: 5
  max_concurrent: 5
  max_token_price: 0.50
  min_token_price: 0.10
  max_hours_to_start: 24.0

far:
  enabled: true
  max_slots: 2
  min_edge: 0.10
  min_ai_probability: 0.55
  min_confidence: B-
  penny_max_price: 0.02
  penny_1c_target_multiplier: 5.0
  penny_2c_target_multiplier: 2.0

notifications:
  telegram_enabled: false

dashboard:
  host: 127.0.0.1
  port: 5050
```

---

## 21. File & Module Inventory

### Core Orchestration
| File | Lines | Purpose |
|------|-------|---------|
| `src/main.py` | ~4,305 | Agent loop, cycle orchestration |
| `src/config.py` | 172 | Pydantic config models, YAML loading |
| `src/models.py` | 117 | MarketData, Position, Signal, Direction |

### AI & Analysis
| File | Lines | Purpose |
|------|-------|---------|
| `src/ai_analyst.py` | 397 | Claude dual-prompt probability |
| `src/edge_calculator.py` | 73 | Edge detection (AI vs market) |
| `src/adaptive_kelly.py` | 28 | Dynamic Kelly fraction |
| `src/edge_decay.py` | 22 | Probability decay over time |
| `src/sanity_check.py` | 67 | AI output validation |

### Risk Management
| File | Lines | Purpose |
|------|-------|---------|
| `src/risk_manager.py` | 109 | Kelly sizing, veto authority |
| `src/circuit_breaker.py` | 115 | Portfolio drawdown halts |
| `src/correlation.py` | 48 | Match-level exposure cap |

### Market Discovery
| File | Lines | Purpose |
|------|-------|---------|
| `src/market_scanner.py` | 331 | Gamma API market fetch |
| `src/pre_filter.py` | 101 | Impossible market removal |
| `src/liquidity_check.py` | 109 | CLOB order book depth |
| `src/manipulation_guard.py` | 142 | Anti-manipulation filters |

### Data Sources
| File | Lines | Purpose |
|------|-------|---------|
| `src/sports_data.py` | 471 | ESPN free API |
| `src/esports_data.py` | 508 | PandaScore + live match state |
| `src/odds_api.py` | 472 | Bookmaker odds |
| `src/vlr_data.py` | 244 | Valorant scraper |
| `src/hltv_data.py` | 179 | CS2 scraper |
| `src/news_scanner.py` | 413 | Multi-source news |

### Execution & Position Management
| File | Lines | Purpose |
|------|-------|---------|
| `src/executor.py` | 95 | CLOB order placement |
| `src/portfolio.py` | 695 | Position tracking, PnL |
| `src/trade_logger.py` | 59 | JSONL trade logging |
| `src/wallet.py` | 67 | Polygon wallet |

### Exit & Scale Logic
| File | Lines | Purpose |
|------|-------|---------|
| `src/match_exit.py` | 371 | 4-layer match-aware exit |
| `src/scale_out.py` | 138 | Partial exit (3-tier) |
| `src/trailing_sigma.py` | 51 | Volatility trailing stop |
| `src/vs_spike.py` | 68 | Volatility swing TP/SL |
| `src/price_history.py` | 65 | CLOB price snapshots |

### Re-Entry & Scouting
| File | Lines | Purpose |
|------|-------|---------|
| `src/reentry_farming.py` | 420 | 3-tier dip re-entry |
| `src/reentry.py` | 310 | Blacklist, eligibility |
| `src/scout_scheduler.py` | 382 | Pre-game analysis |
| `src/live_dip_entry.py` | 254 | Live dip buying |
| `src/esports_early_entry.py` | 295 | Esports early entry |

### Utilities & Monitoring
| File | Lines | Purpose |
|------|-------|---------|
| `src/dashboard.py` | 216 | Flask web dashboard |
| `src/notifier.py` | 167 | Telegram notifications |
| `src/websocket_feed.py` | 266 | CLOB real-time prices |
| `src/cycle_timer.py` | 80 | Dynamic cycle interval |
| `src/process_lock.py` | 75 | Single-instance guard |
| `src/api_usage.py` | 109 | API call tracking |

### Self-Improvement & Tracking
| File | Lines | Purpose |
|------|-------|---------|
| `src/self_improve.py` | 706 | Auto-optimization |
| `src/outcome_tracker.py` | 233 | Post-exit market tracking |

### Test Suite
| Pattern | Count | Lines |
|---------|-------|-------|
| `tests/test_*.py` | 30+ | ~2,300 |

**Total:** ~13,600 lines source + ~2,300 lines tests

---

## 22. Known Limitations & Open Questions

### Current Limitations

| # | Limitation | Impact | Potential Solution |
|---|-----------|--------|-------------------|
| 1 | **AI pool-full waste** — Claude API called even when all slots full | Unnecessary API cost | Skip AI analysis when 0 open slots |
| 2 | **Pending resolution bypass** — Pending positions skip some exit checks | Could miss exit opportunity | Apply exit logic to pending (hold if winning, exit if losing) |
| 3 | **No partial exit on CLOB** — Scale-out system prepared but binary exit only | Can't lock partial profits | Implement CLOB partial sell orders |
| 4 | **Time estimation for non-ESPN markets** — Uses unreliable endDate | Match-aware exit inaccurate for some markets | Add more sport-specific duration APIs |
| 5 | **HLTV/VLR scraping fragility** — Cloudflare may block | Lose tier-2/3 data | Implement proxy rotation, or use official APIs |
| 6 | **No Bayesian calibration yet** — Confidence levels are static | AI may be over/under-confident by category | Implement after 30+ sample trades |
| 7 | **Single model risk** — All probability comes from one Claude model | Single point of failure | Multi-model ensemble (GPT-4o, Gemini as second opinion) |
| 8 | **No portfolio-level Kelly** — Each position sized independently | Correlated bets may exceed total risk | Implement portfolio-wide Kelly optimization |

### Open Design Questions

| # | Question | Options | Current Choice |
|---|----------|---------|---------------|
| 1 | **Bet types** — Should we expand beyond moneyline? | Spreads, totals, props | Moneyline only (simpler, easier to analyze) |
| 2 | **Multi-model ensemble** — Use GPT + Claude for probability? | Single (cheaper) vs Multi (more robust) | Single Claude (cost) |
| 3 | **Market maker mode** — Should bot provide liquidity? | Taker only vs Maker+Taker | Taker only (simpler) |
| 4 | **Political markets** — Should we trade politics? | Sports only vs All categories | Sports only (for now) |
| 5 | **API upgrades** — When to go paid? | At profitability vs Now | At profitability (controlled spend) |
| 6 | **Circuit breaker sensitivity** — Daily -8% too tight or loose? | -5% / -8% / -12% | -8% (moderate) |
| 7 | **Kelly fraction** — 25% too aggressive or conservative? | 10% / 25% / 50% | 25% (standard) |
| 8 | **Re-entry depth** — 3 tiers enough or too many? | 2 / 3 / 4 tiers | 3 tiers |
| 9 | **Max positions** — 5 enough for $60 bankroll? | 3 / 5 / 8 | 5 |
| 10 | **Tennis focus** — Community says "free money" — prioritize? | Equal weight vs Tennis boost | Equal (no data yet) |

---

## 23. Future Roadmap

### Phase 1: Testing & Calibration (Current)
- [x] Complete 4-layer match-aware exit system
- [x] WebSocket real-time price feed
- [x] PandaScore live match state
- [x] HLTV + VLR scraper cascade
- [ ] Complete 28-day testing cycle
- [ ] Bayesian calibration (post 30 samples)
- [ ] Portfolio circuit breaker fine-tuning

### Phase 2: Pre-Live Enhancements
- [ ] Partial exit on CLOB (split orders)
- [ ] Kelly rebalance mid-match
- [ ] Liquidity check on exit (not just entry)
- [ ] EMA trend overlay for momentum
- [ ] ATR-based dynamic catastrophic floor
- [ ] Momentum → position sizing (3+ down → -20% next bet)
- [ ] Adaptive duration (update estimates mid-match)

### Phase 3: Live Trading
- [ ] Paper mode validation (1 week)
- [ ] Live mode transition ($60 initial)
- [ ] Dashboard API usage tracking
- [ ] Telegram alerts for all trade events
- [ ] Dynamic hold-to-resolve promotion

### Phase 4: Scale & Optimize
- [ ] Multi-model ensemble (Claude + GPT-4o)
- [ ] Match outcome logging (AI prediction vs actual)
- [ ] Pool-full AI skip (save budget)
- [ ] SportsGameOdds integration
- [ ] Riot Games API + OpenDota API
- [ ] Tennis-specific optimizations
- [ ] Bankroll scaling ($60 → $200 → $500)

### Phase 5: Advanced Features
- [ ] Market making mode (provide liquidity)
- [ ] Cross-platform (Kalshi, Metaculus)
- [ ] Political market expansion
- [ ] ML-based probability (train on historical data)
- [ ] Social signal analysis (Twitter, Reddit)
- [ ] Automated A/B testing framework

---

## 24. Appendix: API Cost Analysis

### Monthly Estimated Costs (Free Tier)
| API | Free Allocation | Expected Usage | Headroom |
|-----|----------------|---------------|----------|
| Claude API | $48 budget | ~$30-40 | 20-37% |
| Gamma API | ~10K req | ~3K req | 70% |
| ESPN | Unlimited | ~500 req | ∞ |
| PandaScore | 1000 req/hr | ~200 req/hr peak | 80% |
| The Odds API | 500 credits/mo | ~100 credits | 80% |
| Tavily | 1000 credits/mo | ~200 credits | 80% |
| NewsAPI | 500 req/day | ~50 req/day | 90% |
| GNews | 150 req/day | ~10 req/day (fallback) | 93% |

### Paid Tier Upgrade Path
| Trigger | Upgrade | Cost |
|---------|---------|------|
| Bot profitable for 2 weeks | The Odds API → 20K plan | $30/mo |
| Bot profitable for 1 month | SportsGameOdds Rookie | $99/mo |
| Bankroll >$500 | PandaScore paid tier | €150/mo |
| Bankroll >$1000 | Claude API budget increase | $96/mo |

### Break-Even Analysis
At $60 bankroll with 15% monthly ROI target:
- Monthly target profit: $9
- Monthly API cost (free tier): ~$40 (mostly Claude)
- **Break-even bankroll: ~$270** (at 15% ROI, $40 API cost)
- Strategy: Minimize AI calls, maximize edge per call

---

## Review Guide for AI Reviewers

This document is designed for multi-AI collaborative review. Here are the key areas where feedback is most valuable:

### Architecture & Design
1. Is the 4-layer exit system over-engineered? Could it be simplified without losing effectiveness?
2. Is the 3-tier re-entry farming worth the complexity? What's the expected hit rate?
3. Should we prioritize multi-model ensemble (reduce single-model risk) or is single-model fine for this scale?

### Risk Management
4. Is 25% Kelly fraction appropriate for a $60 bankroll? Too aggressive? Too conservative?
5. Are the circuit breaker thresholds (-8% daily, -5% hourly) well-calibrated?
6. Is 5 max concurrent positions optimal for $60 bankroll?

### AI & Probability
7. Is the dual-prompt framework (Pro/Con/Synthesize) effective, or should we try chain-of-thought / scratchpad approaches?
8. Should confidence grades be calibrated dynamically (Bayesian) from the start, or is static fine initially?
9. Is $48/month AI budget sufficient for 20 markets/cycle at 30-min intervals?

### Data & Markets
10. Should we add tennis-specific data sources? Community claims it's "free money" — is there a structural reason?
11. Is the PandaScore → HLTV/VLR → ESPN cascade the right priority order?
12. Should we add social signals (Twitter, Reddit) for breaking news detection?

### Strategy
13. Should we expand to spreads/totals, or is moneyline-only the correct approach at this scale?
14. Is the FAR (6-336 hour) strategy viable with such a small bankroll?
15. Are penny alpha plays ($0.01-$0.02 tokens) worth the slot and attention cost?

### Testing & Operations
16. Is the 28-day testing plan too long? Too short? Are the checkpoints well-placed?
17. Should paper mode be required before live, or can we go dry_run → live with small bankroll?
18. Is the self-improvement loop (one parameter change per checkpoint) too conservative?

---

*End of PRD — Optimus Claudeus v2.0*
