# MiroFish Political Bot — Full Plan Review Prompt

> Copy everything below and paste into Claude.

---

## ROLE

You are a senior systems architect and quantitative trading strategist. I'm going to show you a complete plan for building a political prediction bot. I need you to:

1. **Review each phase** — find weaknesses, gaps, unrealistic assumptions
2. **Answer my specific open questions** at the end
3. **Be brutally honest** — if something is stupid, say so. If something is brilliant, say so.
4. **Think about edge cases** I haven't considered

---

## PROJECT OVERVIEW

I have an existing sports betting bot (Polymarket Agent) that trades sports markets on Polymarket. It works. Now I want to build a SEPARATE political prediction bot using MiroFish — an open-source social simulation engine.

**MiroFish** (GitHub: 666ghj/MiroFish): Takes seed text → builds a social graph (GraphRAG) → generates AI personas → runs a dual-platform simulation (Twitter + Reddit style) where agents discuss the topic → produces a report with consensus analysis.

**The idea:** Use MiroFish simulations to predict political/geopolitical outcomes, compare MiroFish's probability estimate with Polymarket's market price, and trade when there's edge.

### Architecture

```
Sports Bot (Polymarket Agent)    Political Bot (MiroFish)
       │  INDEPENDENT               │  INDEPENDENT
       ├── own executor              ├── own executor
       ├── own portfolio             ├── own portfolio
       ├── own risk manager          ├── own risk manager
       │                             │
       └──► Polymarket API ◄─────────┘
            (same account)
```

Two bots, one Polymarket account. Neither knows about the other. Neither can break the other. Code is COPIED from sports bot and adapted, never imported.

### Technology Stack

| Component | Choice | Cost | Why |
|---|---|---|---|
| Simulation Engine | MiroFish Offline (fork with Neo4j instead of Zep Cloud) | $0 | Open-source, runs locally |
| Graph Database | Neo4j Community Edition (Docker) | $0 | Local, unlimited, ~500MB-1GB RAM |
| LLM (Phase 0-3) | Groq free (Llama 3.3 70B) or Google AI Studio free (Gemini Flash) | $0 | Test concept at zero cost |
| LLM (Phase 4+) | Gemini Flash paid | ~$9/month | Best cost/quality ratio |
| Order Execution | Copied from sports bot | $0 | Proven code |
| Notifications | Same Telegram bot | $0 | [POLITICAL] prefix |

### Hardware

- Windows 11, Intel i7-11800H (8 core), 16GB RAM, RTX 3050 4GB VRAM
- Local LLM eliminated (needs 6GB+ VRAM minimum)
- Neo4j + MiroFish + Docker should fit in ~4GB RAM

---

## PHASE 0: Setup & Mechanical Test (1-2 days, $0)

**Goal:** Install MiroFish Offline, Docker, Neo4j. Verify the pipeline works mechanically (input seed → graph builds → simulation runs → report generates). Quality doesn't matter, just mechanics.

**Steps:**
1. Create separate project directory: `MiroFish Political Bot/`
2. Install Docker Desktop (WSL2)
3. Clone MiroFish Offline (nikmcfly/MiroFish-Offline) — falls back to main repo (666ghj/MiroFish) if broken
4. Configure .env with FREE LLM (Groq or Google AI Studio)
5. Start Docker services (Neo4j, backend, frontend)
6. Run a test simulation (20 agents, 10 rounds, non-political topic)
7. Document everything in `docs/setup-log.md`

**Success:** Docker running, Neo4j accessible, MiroFish UI loads, test simulation completes, report generated, RAM < 4GB.

**Kill:** Docker won't start, MiroFish repo broken, Neo4j needs >4GB RAM, simulation crashes.

---

## PHASE 1: Signal Quality Test (3-7 days + wait, $0)

**Goal:** Test if MiroFish produces USEFUL political predictions using FREE LLM. This is the first KILL/CONTINUE decision.

**Why not test on resolved markets?** LLMs already know the outcomes from training data. A "blind test" on resolved markets isn't blind.

**Two test categories:**

### Category A: Open Markets (3-5 markets)
- Currently ACTIVE political markets where nobody knows the outcome
- Decent volume (>$100K), price between 15%-85%, resolution 2 weeks to 3 months out
- Evaluate QUALITY: argument quality (1-5), unique insights (1-5), consistency, meaningful disagreement with market
- We can't check accuracy yet — we evaluate whether MiroFish produces real analysis vs garbage

### Category B: Near-Resolution Markets (2-3 markets)
- Markets resolving within 1-2 weeks — fast feedback loop
- Record MiroFish's prediction NOW, verify accuracy after resolution
- This gives us actual accuracy data within 1-2 weeks

**Simulation settings (to fit free tier):** 50 agents, 20 rounds, ~2000 LLM calls per run.

**Rate limits:**
- Groq free: 30 req/min, 6000 req/day → ~3 simulations/day
- Google AI Studio free: 15 req/min, 1500 req/day → ~0.75 simulations/day (daily limit is the bottleneck, not per-minute)

**Kill criteria:**
- All predictions echo market price (zero value-add)
- Arguments are gibberish
- All predictions cluster around 50% (no opinion)

**Continue criteria:**
- Argument quality 3+/5
- Disagrees with market on 1-2 markets with logical reasoning
- Category B: 2+/3 directionally correct

**Gray zone → Phase 1b:** Switch to the OTHER free LLM provider (Groq↔Gemini Flash). Still $0.

---

## PHASE 2: Pipeline Build (1 week, $0)

**Goal:** Build automated pipeline modules. After this phase: discover political markets → create seed packets → run simulations → output probability estimates. NO execution yet.

**9 modules:**

1. **config.py** — .env loading, constants
2. **models.py** — Pydantic models (PoliticalMarket, SeedPacket, SimulationResult, EnsembleResult, TradeSignal, CatalystEvent, PriceDrift, PositionReeval)
3. **political_scanner.py** — Discover political markets via Gamma API, keyword classification, filter criteria (volume, duration, not nearly resolved)
4. **news_enrichment.py** — Fetch news via free sources (NewsAPI, GNews, RSS)
5. **seed_builder.py** — Market data + news → structured MiroFish seed packet
6. **simulation_client.py** — Interface with MiroFish REST API (localhost:5001). Upload seed, start simulation, poll completion, fetch report
7. **probability.py** — Extract probability from MiroFish natural language report (regex for percentages, LLM fallback for qualitative statements)
8. **edge_calculator.py** — Compare MiroFish probability vs market price, calculate adjusted edge (discount by ensemble stdev)
9. **catalyst_tracker.py** — Monitor news + prices on EXISTING positions. Keyword matching on held position entities. Flag positions for re-evaluation when price drifts >5% or catalyst detected

**Edge formula:**
```
edge = mirofish_prob - market_price (for BUY_YES)
adjusted_edge = edge - (stdev * 1.5)
signal if adjusted_edge > 8%
```

---

## PHASE 3: Polymarket Integration (1 week, $0)

**Goal:** Add execution, portfolio, risk management, notifications. Bot can run in DRY_RUN mode.

**Modules (copied from sports bot and adapted):**
- executor.py — order execution (dry_run/paper/live)
- portfolio.py — position tracking with trade_history per market, price_snapshots, catalyst_flags
- risk_manager.py — conservative limits + re-entry cooldown + flip limit
- notifier.py — Telegram with [POLITICAL] prefix
- political_bot.py — main orchestrator
- main.py — entry point

### Active Trading Architecture: TWO Cycle Types

**Light Cycle (every hour, $0 cost):**
1. Fetch current prices for all open positions (free Polymarket API)
2. Check stop-loss / take-profit triggers
3. Quick news scan for catalyst keywords related to held positions
4. If price drift >5% OR major catalyst → flag for re-evaluation in next heavy cycle
5. If URGENT (price drop >15%) → trigger immediate exit check
6. Log price snapshots

**Heavy Cycle (every 6-12 hours, LLM cost):**

Job A — New Market Discovery:
1. Scan for political markets
2. Build seed packets for top candidates
3. Run MiroFish simulations (100 agents, 30 rounds, 3 ensemble runs)
4. Extract probabilities, calculate edges
5. Execute trades above threshold

Job B — Position Re-Evaluation (only for flagged positions):
1. Build UPDATED seed packet (new headlines, current price)
2. Run fresh MiroFish simulation
3. Compare new probability vs old
4. Decision matrix:
   - Shifted >10% in favor → HOLD or ADD
   - Shifted >10% against → EXIT
   - FLIPPED (70% → 35%) → EXIT, consider FLIP
   - Stable → HOLD

**Risk limits:**
- Max 5 concurrent positions
- Max 3% per position
- Max 12% total exposure
- Stop-loss: -40% from entry
- Take-profit: trailing, activate +25%, trail 10%
- Re-entry cooldown: 2 heavy cycles after exiting a market
- Flip limit: max 1 direction flip per market per week
- Daily loss limit: 3 losses → halt 24 hours

**Volatility Swing Example:**
1. Buy YES at $0.40 (MiroFish=65%, edge=25%) → ENTER
2. Price jumps to $0.70 after news → light cycle flags → heavy cycle re-evals → edge gone → EXIT (+$0.30)
3. Price drops to $0.45 → flagged again → MiroFish still says 62% → edge=17% → RE-ENTER
4. Multiple profitable trades on the SAME market before resolution

---

## PHASE 4: Paper Trading (2 weeks, ~$9)

**Goal:** Run bot in dry_run mode on LIVE political markets. Track every prediction, every hypothetical trade.

**LLM upgrade:** Switch to Gemini Flash paid (~$9/month) for production-quality simulations.

**Metrics tracked:**
- Per trade: probability, edge, direction, entry price, outcome, P&L, trade type (NEW/RE-ENTRY/EXIT_REEVAL/EXIT_SL/EXIT_TP), trigger (DISCOVERY/CATALYST/PRICE_DRIFT)
- Per market: how many entry/exit swings, total P&L across swings, did active monitoring beat buy-and-hold?
- Aggregate: win rate, calibration curve, swing profit vs hold profit, re-evaluation accuracy

**Kill (day 14):** Win rate <35%, edge <3%, terrible calibration.
**Continue:** Win rate >50%, edge >5%, reasonable calibration, positive P&L.
**Gray zone:** Extend 1 more week for more data.

**Rules:** Do NOT optimize mid-test. Do NOT cherry-pick signals. Log everything.

---

## PHASE 5: Live Trading (8+ weeks, ~$9-12/month)

**Scaling ladder:**

| Week | Position Size | Max Positions | Max Exposure |
|------|-------------|---------------|-------------|
| 1 | 1% | 2 | 3% |
| 2 | 1% | 3 | 5% |
| 3-4 | 2% | 4 | 8% |
| 5-8 | 3% | 5 | 12% |
| 9+ | 3% | 5 | 15% |

Never exceed 15% total political exposure. Sports bot is the primary revenue source.

**Kill even in live:** 3 consecutive losses, P&L drops below -5% of invested, any bug causes incorrect order, sports bot affected.

---

## COST SUMMARY

| Phase | Duration | Cost |
|-------|----------|------|
| 0 - Setup | 1-2 days | $0 |
| 1 - Signal Test | 3-7 days | $0 |
| 1b - Retest (optional) | 2-3 days | $0 |
| 2 - Pipeline | 1 week | $0 |
| 3 - Integration | 1 week | $0 |
| 4 - Paper Trading | 2 weeks | ~$9 |
| 5 - Live | 8+ weeks | ~$9-12/month |

**$0 to test if concept works. $9 to reach paper trading. Max $9 lost if killed at Phase 4.**

---

## OPEN QUESTIONS — PLEASE EVALUATE

### Q1: News/Catalyst Monitoring — How Should It Work?

The bot needs to track news on existing positions (to know when to re-evaluate). Three options:

**Option A: Keyword matching only ($0)**
- RSS feeds (Reuters, AP, BBC) + GNews/NewsAPI free tier (100 req/day each)
- Match keywords from position entities (e.g., position on "Trump tariff" → scan for "Trump" + "tariff")
- Pro: Free, simple
- Con: High false positive rate (every "Trump" headline triggers), no understanding of relevance

**Option B: Keyword matching + cheap LLM filter (~$0.50/month)**
- Same keyword scan, but pass each headline to a cheap LLM (Gemini Flash): "Does this headline materially affect this market? YES/NO"
- Pro: Much fewer false positives, smarter re-evaluation triggering
- Con: Small LLM cost per light cycle, adds latency

**Option C: Polymarket price-only, no news ($0)**
- Just watch the price. If it moves >5%, assume something happened and re-evaluate.
- Pro: Simplest, free, the market IS the news aggregator
- Con: Reactive not predictive, by the time price moves the opportunity may be gone

Which approach is best? Is there a better option I'm not seeing?

### Q2: Is Volatility Swing Trading Realistic on Political Markets?

My plan assumes the bot can profitably enter/exit the same market multiple times as news develops. But:
- Political market spreads on Polymarket can be wide (2-5%)
- Each entry/exit costs spread + slippage
- Are political markets volatile ENOUGH to swing trade? Or do they mostly drift slowly toward resolution?
- Should the bot just buy-and-hold with stop-loss/TP instead of trying to swing?

What's your assessment? Is swing trading on political prediction markets realistic, or am I overcomplicating this?

### Q3: MiroFish Re-evaluation Quality

When re-evaluating an existing position with new news:
- Will MiroFish actually produce DIFFERENT results with updated seed packets? Or will it give roughly the same answer regardless of new headlines?
- Is there a risk that MiroFish re-evaluations are just noise (random variation between runs) rather than genuine probability updates?
- How do we distinguish "MiroFish genuinely updated its estimate based on new information" from "MiroFish randomly produced a different number"?

### Q4: Free LLM Quality for Political Simulation

- Llama 3.3 70B (Groq free) vs Gemini Flash (Google AI Studio free) — which would produce better political analysis in a social simulation context?
- Is a free-tier LLM capable enough to run meaningful MiroFish simulations? Or will Phase 1 almost certainly fail due to model quality?
- At what model capability level does MiroFish start producing useful political predictions?

### Q5: Two Bots, One Account — Hidden Risks?

Both bots trade on the same Polymarket account with separate portfolios. Potential issues:
- Combined position might exceed Polymarket's per-account limits
- If both bots try to use the full bankroll, they could overdraw
- One bot's losing streak could eat into the other's bankroll
- Is there a way to partition the bankroll cleanly? Or do we need a shared "bankroll allocator"?

### Q6: Is MiroFish Even the Right Tool?

MiroFish was designed for social media behavior simulation, not prediction markets. My bet is that "simulating public discourse → extracting probability" adds value over direct LLM prompting (just asking Claude/Gemini "what's the probability of X?").

- Does the social simulation layer actually add predictive value? Or is it just expensive noise around a simple LLM prompt?
- Would I get better results by just asking a good LLM directly with structured prompts (superforecasting framework, base rates, etc.)?
- What would MiroFish capture that direct LLM prompting would miss?

### Q7: Phase 1 Test Design — Is It Valid?

- Testing on 3-5 open markets + 2-3 near-resolution markets — is this enough data to make a kill/continue decision?
- Category A (open markets) evaluates quality, not accuracy. Am I measuring the right thing?
- Could MiroFish produce "great arguments" that are actually just the LLM restating common knowledge — making it look useful without actually having edge?

### Q8: Monthly Cost Estimate — Am I Missing Something?

Projected: ~$9-12/month for Gemini Flash at production scale (10 markets, 3 ensemble runs each, + re-evaluations).
- Is this realistic? What could make it spike unexpectedly?
- MiroFish simulations with 100 agents × 30 rounds = ~6000 LLM calls per simulation. At Gemini Flash pricing ($0.075/1M input tokens, $0.30/1M output tokens), each simulation ≈ $0.02-0.05. 10 markets × 3 runs = 30 simulations/day × 2 heavy cycles = 60 sims/day × $0.03 = $1.80/day = $54/month.
- Wait — is my original $9/month estimate WRONG? Please check my math.

---

## YOUR TASK

1. Review the entire plan phase by phase. What's strong? What's weak? What am I missing?
2. Answer each of the 8 questions above with your honest assessment.
3. If you think MiroFish is the wrong approach entirely, say so and suggest what would be better.
4. Rate the overall plan: is this a good bet for someone who already has a working sports bot and wants to expand into political markets at near-zero cost?
