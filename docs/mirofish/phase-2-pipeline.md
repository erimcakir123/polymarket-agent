# MiroFish Political Bot — Phase 2: Pipeline Build

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

Phase 0 (setup) and Phase 1 (blind test) are complete. MiroFish showed it can produce useful political predictions. Now we build the automated pipeline.

**Read these files first:**
- `docs/setup-log.md` — what was configured in Phase 0
- `docs/blind-test-results.md` — what worked/didn't in Phase 1
- `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\CLAUDE.md` — READ ONLY, for understanding project conventions

## OBJECTIVE

Build the core pipeline modules for the MiroFish Political Bot. After this phase, the bot can: discover political markets, create seed packets, run simulations, and output probability estimates. NO Polymarket execution yet — that's Phase 3.

## HARD RULES

1. **Read CLAUDE.md from Polymarket Agent** (READ ONLY) to understand coding conventions: type hints, Pydantic models, logging, .env for secrets.
2. **Do NOT import from Polymarket Agent** — copy what you need, adapt it.
3. **Do NOT touch Polymarket Agent directory.**
4. **$0 COST — keep using the same free LLM from Phase 1.** Do NOT upgrade to paid yet.
5. **Type hints on ALL functions, Pydantic for data models.**
6. **Log every decision** — use Python logging module.
7. **Test after every file creation** — run `python -m pytest tests/ -v --tb=short`.
8. **Zero dead code, zero duplication.**
9. **Never hardcode API keys** — always .env.

## PROJECT STRUCTURE

```
c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot\
├── src/
│   ├── __init__.py
│   ├── config.py              ← Configuration + .env loading
│   ├── models.py              ← Pydantic data models
│   ├── political_scanner.py   ← Discover political markets on Polymarket
│   ├── seed_builder.py        ← Market data → structured MiroFish input
│   ├── simulation_client.py   ← Interface with MiroFish engine
│   ├── probability.py         ← Extract probability from simulation results
│   ├── edge_calculator.py     ← Compare MiroFish probability vs market price
│   ├── catalyst_tracker.py    ← Monitor news/prices on open positions for re-evaluation
│   └── news_enrichment.py     ← Fetch relevant news for seed packets
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_political_scanner.py
│   ├── test_seed_builder.py
│   ├── test_simulation_client.py
│   ├── test_probability.py
│   ├── test_edge_calculator.py
│   └── test_catalyst_tracker.py
├── docs/
│   ├── setup-log.md           ← From Phase 0
│   ├── blind-test-results.md  ← From Phase 1
│   └── pipeline-log.md        ← This phase's log
├── mirofish-engine/           ← Cloned MiroFish (from Phase 0)
├── .env
├── .gitignore
├── CLAUDE.md
├── requirements.txt
└── pyproject.toml
```

## MODULE SPECIFICATIONS

### Module 1: `src/config.py` (~50 lines)
Load configuration from .env:
```python
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"
MIROFISH_BACKEND_URL = "http://localhost:5001"  # local MiroFish
GEMINI_API_KEY = env  # for future use
DEFAULT_AGENTS = 100
DEFAULT_ROUNDS = 30
ENSEMBLE_RUNS = 3
MIN_EDGE_PERCENT = 8.0  # minimum edge to consider a trade
```

### Module 2: `src/models.py` (~100 lines)
Pydantic models — adapt from Polymarket Agent's models.py but only what we need:
```python
class PoliticalMarket(BaseModel):
    condition_id: str
    question: str
    description: str
    resolution_rules: str
    end_date: datetime
    yes_price: float
    no_price: float
    yes_token_id: str
    no_token_id: str
    volume: float
    category: str  # politics, geopolitics, policy, etc.

class SeedPacket(BaseModel):
    market: PoliticalMarket
    base_facts: list[str]
    recent_headlines: list[str]
    key_entities: dict[str, list[str]]
    bull_case: list[str]
    bear_case: list[str]
    unknowns: list[str]

class SimulationResult(BaseModel):
    market_id: str
    run_number: int
    probability_yes: float
    agent_count: int
    round_count: int
    top_arguments_for: list[str]
    top_arguments_against: list[str]
    agent_stdev: float
    duration_seconds: float
    raw_report: str  # full MiroFish report text

class EnsembleResult(BaseModel):
    market_id: str
    mean_probability: float
    stdev: float
    min_probability: float
    max_probability: float
    confidence: str  # HIGH (<5% stdev), MEDIUM (5-15%), LOW (>15%)
    runs: list[SimulationResult]

class TradeSignal(BaseModel):
    market: PoliticalMarket
    ensemble: EnsembleResult
    direction: str  # BUY_YES or BUY_NO
    edge_percent: float
    recommended_size_percent: float  # of bankroll
    reasoning: str
```

### Module 3: `src/political_scanner.py` (~150 lines)
Discover political markets on Polymarket via Gamma API.

Key functions:
- `scan_political_markets() -> list[PoliticalMarket]` — fetch active political markets
- `_is_political(market) -> bool` — classify if a market is political/geopolitical
- `_fetch_order_book(token_id) -> dict` — get current prices
- `_meets_criteria(market) -> bool` — liquidity, duration, etc.

Filter criteria:
- Category: politics, geopolitics, policy, elections, government
- Liquidity: >= $500 USDC in order book
- Duration: >= 7 days remaining (no short-term noise)
- Not nearly resolved: YES price between 5% and 95%
- Has both token IDs

Classification approach:
- Gamma API tags (if available for politics)
- Keyword matching on question/description: "president", "congress", "election", "war", "ceasefire", "legislation", "supreme court", "sanctions", etc.
- Exclude: sports, crypto price, weather, entertainment (unless political)

### Module 4: `src/news_enrichment.py` (~100 lines)
Fetch relevant news for seed packet context.

Key functions:
- `fetch_news(query: str, max_results: int = 10) -> list[dict]` — search for relevant news
- `_format_headlines(articles) -> list[str]` — extract clean headlines with dates

Use free news sources (same approach as Polymarket Agent):
- NewsAPI free tier (100 req/day)
- GNews free tier
- RSS feeds as fallback

### Module 5: `src/seed_builder.py` (~200 lines)
Convert market data + news into a structured seed packet for MiroFish.

Key functions:
- `build_seed_packet(market: PoliticalMarket) -> SeedPacket` — main builder
- `_generate_base_facts(market) -> list[str]` — extract facts from market description
- `_generate_bull_bear(market, news) -> tuple[list, list]` — arguments for/against
- `_identify_entities(market, news) -> dict` — extract key people, institutions
- `format_for_mirofish(packet: SeedPacket) -> str` — format as text for MiroFish input

The seed packet format should match what worked best in Phase 1 blind testing.
Reference `docs/blind-test-results.md` for lessons learned about seed quality.

### Module 6: `src/simulation_client.py` (~150 lines)
Interface with MiroFish backend to run simulations.

Key functions:
- `run_simulation(seed_text: str, agents: int, rounds: int) -> SimulationResult` — run one simulation
- `run_ensemble(seed_text: str, runs: int = 3) -> EnsembleResult` — run multiple and aggregate
- `_upload_seed(text) -> str` — upload seed to MiroFish
- `_start_simulation(project_id, agents, rounds) -> str` — start simulation
- `_wait_for_completion(sim_id) -> dict` — poll until done
- `_fetch_report(sim_id) -> str` — get generated report

This module talks to MiroFish's REST API (localhost:5001).
Study MiroFish's API routes in `backend/app/api/` to understand endpoints.

### Module 7: `src/probability.py` (~100 lines)
Extract a probability estimate from MiroFish simulation results.

Key functions:
- `extract_probability(report: str, question: str) -> float` — parse probability from report text
- `_llm_extract(report, question) -> float` — use LLM to extract if not explicit
- `calculate_ensemble(results: list[SimulationResult]) -> EnsembleResult` — aggregate multiple runs

MiroFish reports are natural language. Probability extraction may require:
1. Regex for explicit percentages
2. LLM call to interpret qualitative statements ("very likely" = ~80%)
3. Agent vote counting (if available from simulation data)

### Module 8: `src/edge_calculator.py` (~80 lines)
Compare MiroFish probability with market price to find edge.

Key functions:
- `calculate_edge(ensemble: EnsembleResult, market: PoliticalMarket) -> TradeSignal`
- `effective_price(yes_price: float, direction: str) -> float` — same logic as Polymarket Agent

Edge formula:
```
if mirofish_prob > market_yes_price:
    direction = BUY_YES
    edge = mirofish_prob - market_yes_price
else:
    direction = BUY_NO
    edge = (1 - mirofish_prob) - market_no_price

# Apply uncertainty discount based on ensemble stdev
adjusted_edge = edge - (stdev * 1.5)

# Only signal if edge > minimum threshold
if adjusted_edge > MIN_EDGE_PERCENT / 100:
    generate signal
```

### Module 9: `src/catalyst_tracker.py` (~150 lines)
Track news catalysts and price movements on EXISTING positions to enable active trading (volatility swings, not buy-and-hold).

Key functions:
- `check_catalysts(positions: list[Position]) -> list[CatalystEvent]` — scan news for events affecting held positions
- `check_price_drift(positions: list[Position]) -> list[PriceDrift]` — detect significant price changes since last check
- `should_reevaluate(position, catalysts, price_drift) -> bool` — decide if a position needs a fresh MiroFish simulation
- `build_reevaluation_context(position, catalysts) -> str` — format new seed packet with updated news for re-simulation

This module powers the **active position management** strategy:
- Every HOUR: check prices on all open positions via free Polymarket API (no LLM cost)
- Every HOUR: quick news scan for keywords related to held positions
- If price moved >5% since last check OR a major catalyst detected → flag for re-simulation
- Re-simulation uses the SAME MiroFish pipeline but with UPDATED seed packet (new headlines, current price)

Catalyst detection:
- Keyword match on position's market question entities (e.g., "Trump", "NATO", "tariff")
- Price movement threshold (configurable, default 5%)
- Scheduled event detection: known upcoming dates (votes, hearings, speeches)

### Module 10: `src/models.py` additions
Add these models to support active trading:

```python
class CatalystEvent(BaseModel):
    position_id: str
    headline: str
    source: str
    relevance_score: float  # 0-1, how relevant to this position
    timestamp: datetime

class PriceDrift(BaseModel):
    position_id: str
    entry_price: float
    last_checked_price: float
    current_price: float
    drift_percent: float
    direction: str  # "favorable" or "adverse"

class PositionReeval(BaseModel):
    position_id: str
    old_probability: float
    new_probability: float
    probability_shift: float
    action: str  # "HOLD", "EXIT", "FLIP" (reverse direction), "ADD"
    reasoning: str
```

## EXECUTION ORDER

Build modules in this order, test after each:

1. `src/config.py` + `src/models.py` → `python -m pytest tests/test_models.py -v`
2. `src/political_scanner.py` → `python -m pytest tests/test_political_scanner.py -v`
3. `src/news_enrichment.py` → manual test (needs API)
4. `src/seed_builder.py` → `python -m pytest tests/test_seed_builder.py -v`
5. `src/simulation_client.py` → `python -m pytest tests/test_simulation_client.py -v`
6. `src/probability.py` → `python -m pytest tests/test_probability.py -v`
7. `src/edge_calculator.py` → `python -m pytest tests/test_edge_calculator.py -v`
8. `src/catalyst_tracker.py` → `python -m pytest tests/test_catalyst_tracker.py -v`
9. Integration test: scanner → seed → simulate → probability → edge (end-to-end)
10. Integration test: catalyst_tracker → re-seed → re-simulate → re-evaluate (position update flow)

## TEST REQUIREMENTS

Every module needs tests. Use pytest + mock for external APIs.

- Mock Gamma API responses for scanner tests
- Mock MiroFish API responses for simulation client tests
- Use real Phase 1 data for seed builder and probability tests
- Edge calculator: pure math, test with known inputs/outputs

Minimum: **1 test per public function, 1 integration test for the full pipeline.**

## ANTI-SPAGHETTI CHECKLIST (after EVERY module)

```bash
# 1. Tests pass
python -m pytest tests/ -v --tb=short

# 2. No unused imports
# Check each file for imports that aren't used

# 3. No dead code
# Every function must have a caller or a test

# 4. No duplication
# grep for duplicated logic across files

# 5. Type hints present
# Every function has type hints on params and return

# 6. No hardcoded secrets
# grep for API keys, URLs that should be in .env
```

## SUCCESS CRITERIA

- [ ] All 9 modules created and working (including catalyst_tracker)
- [ ] All tests pass (`python -m pytest tests/ -v --tb=short`)
- [ ] End-to-end integration test: given a political market → outputs a TradeSignal
- [ ] No circular imports
- [ ] No dead code
- [ ] `docs/pipeline-log.md` complete with decisions and rationale
- [ ] Polymarket Agent untouched

## WHAT'S NEXT

Phase 3 adds Polymarket execution capability: order placement, portfolio tracking, risk management, Telegram notifications. The pipeline from this phase feeds into execution.
