# MiroFish Political Bot — Phase 1: Blind Validation Test (FREE)

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

Phase 0 is complete — MiroFish is installed and running. We verified the pipeline works mechanically. Now we test whether MiroFish produces USEFUL predictions on real Polymarket political markets.

**This is the first KILL/CONTINUE decision point.** We test with FREE LLM first ($0 cost). If free LLM shows promise → great. If results are mixed → we try a different free LLM (Phase 1b, $0) or kill.

## OBJECTIVE

Test MiroFish on REAL Polymarket political markets using a FREE LLM. Two test types:

1. **OPEN markets (primary test):** Currently active political markets where nobody knows the outcome — not even the LLM. This is the truest test because the LLM can't cheat from training data.
2. **Near-resolution markets (bonus):** Markets resolving within 1-2 weeks. We record MiroFish's prediction NOW, then verify when it resolves. Fast feedback loop.

**WHY NOT RESOLVED MARKETS?** The LLM's training data already contains the outcomes of resolved markets. Even if we don't tell MiroFish the answer, the model "knows" Biden resigned, Trump won, etc. A blind test on resolved markets isn't truly blind.

## HARD RULES

1. **Read Phase 0's `docs/setup-log.md` first** — understand what was configured.
2. **$0 COST — use the same free LLM from Phase 0.** Do NOT upgrade to paid yet.
3. **Do NOT touch Polymarket Agent** — still 100% off-limits.
4. **Document EVERYTHING** — write results in `docs/signal-quality-results.md`.
5. **Be honest about results** — if MiroFish produces garbage, say so clearly.

## STEP 1: Keep Free LLM, Verify It Works

Use the SAME free LLM from Phase 0 (Groq free / Google AI Studio free / whatever worked).
Do NOT upgrade to paid. We test the concept at $0 first.

If Phase 0 used a very small model (7B or less) that produced gibberish, upgrade to the BEST FREE option:
- Groq free: Llama 3.3 70B (good quality, 30 req/min, 6000 req/day)
- Google AI Studio free: Gemini Flash (good quality, 15 req/min, 1500 req/day)

Both are free. Pick whichever has better rate limits for your simulation size.

**Important:** Simulations will be SLOW with free tier rate limits. That's OK — we're testing signal quality, not speed. Run overnight if needed.

## STEP 2: Find Political Markets (Two Categories)

### Category A: Open Markets (3-5 markets)
Currently ACTIVE political/geopolitical markets where outcome is unknown:
- Must be political/geopolitical (not sports, not crypto)
- Decent volume (>$100K)
- Resolution date: 2 weeks to 3 months out (not too close, not too far)
- Current price between 15%-85% (not already decided)

### Category B: Near-Resolution Markets (2-3 markets)
Markets resolving within 1-2 WEEKS — fast feedback:
- Same criteria as above
- Resolution date within 7-14 days
- These give us quick accuracy data

Use the Polymarket API:
```python
import requests
# Open political markets
markets = requests.get(
    "https://gamma-api.polymarket.com/markets",
    params={"active": "true", "closed": "false", "limit": 50, "order": "volume", "ascending": "false"}
).json()
# Filter for political markets manually
```

For each market, record:
- Market question (exact text)
- Resolution rules
- Current YES/NO price
- Volume
- Resolution date
- Category (A: open long-term, B: near-resolution)

## STEP 3: Build Seed Packets

For each market, create a structured seed document. This is what MiroFish will use as input.

Template:
```
MARKET QUESTION:
[Exact question from Polymarket]

RESOLUTION RULES:
[Full resolution rules, verbatim]

Resolution source: [Official data provider]
End date: [Exact end date]

CURRENT MARKET STATE:
YES price: $X.XX
NO price: $X.XX
Volume: $XXX,XXX

BASE FACTS:
1. [Current verifiable fact]
2. [Current verifiable fact]
3. [Current verifiable fact]

RECENT HEADLINES:
1. [Real headline from past 48 hours]
2. [Real headline]
3. [Real headline]

KEY ENTITIES:
- People: [Names and roles]
- Institutions: [Organizations involved]

PREDICTION TASK:
Estimate the probability that this market resolves YES.
Explain your reasoning through discussion and debate.
Identify the strongest arguments for and against.
```

Use web search to gather CURRENT headlines and facts for each market.

## STEP 4: Run Simulations

Use SMALLER simulations to stay within free tier daily limits:
- **Agents:** 50 (fits within daily rate limits)
- **Rounds:** 20
- **Run 1 time per market first** (save rate limit budget)
- If results look promising, run 2 more per market for ensemble

Record for each run:
- MiroFish probability estimate (YES%)
- Standard deviation across agent opinions
- Top 3 arguments identified FOR
- Top 3 arguments identified AGAINST
- Run duration
- Any errors or anomalies

Calculate ensemble statistics:
- Mean probability across 3 runs
- Standard deviation across 3 runs
- Confidence (low stdev = high confidence)

## STEP 5: Evaluate Results

Two different evaluation methods for two categories:

### Category A (Open Markets) — Evaluate QUALITY, not accuracy (we don't know the answer yet)

Create a scorecard in `docs/signal-quality-results.md`:

```markdown
## Market: [Question]
- Current market price: YES $X.XX
- MiroFish probability: X%
- MiroFish vs market: [agrees / disagrees by X%]
- Argument quality (1-5): [are arguments substantive and logical?]
- Unique insights (1-5): [did MiroFish surface something non-obvious?]
- Consistency across runs: [stdev if multiple runs]
- Notes: [observations]
```

**What we're looking for:**
- Does MiroFish produce REASONING, not just a number?
- Are the arguments things a smart analyst would consider?
- Does it sometimes disagree with the market? (If it always matches market price, it's useless)
- Is the disagreement backed by logic? (If it disagrees randomly, also useless)

### Category B (Near-Resolution Markets) — Evaluate ACCURACY after resolution

```markdown
## Market: [Question]
- MiroFish probability at test time: X%
- Market price at test time: $X.XX
- Actual outcome: [YES/NO] (fill in after resolution)
- MiroFish direction: [Correct/Wrong]
- Market direction: [Correct/Wrong]
- MiroFish beat market? [YES/NO]
- Notes: [what did MiroFish get right or wrong?]
```

**Category B is the real test** — but we need to wait 1-2 weeks for results.

## KILL/CONTINUE CRITERIA

Evaluate based on BOTH categories:

### CONTINUE to Phase 2 (still free) if:
- **Category A:** Argument quality averages 3+/5 — MiroFish produces real analysis
- **Category A:** MiroFish disagrees with market on at least 1-2 markets with logical reasoning
- **Category A:** Predictions show meaningful spread (not all 45-55%)
- **Category B (if resolved by now):** 2+ out of 3 directionally correct

### GO TO PHASE 1b (retest with different free LLM, $0) if:
- Arguments are shallow but directionally sensible — better model might fix
- Simulations ran but output was low-quality text — clearly a model limitation
- Category B inconclusive (too few resolved)

### HARD KILL if:
- **All predictions just echo market price** — MiroFish adds zero value
- **Arguments are gibberish or just restating the question** — no real analysis
- **All predictions cluster around 50%** — MiroFish has no opinion, just noise
- **Simulations produce gibberish or crash** — fundamental technical failure

## PHASE 1b: OPTIONAL RETEST WITH BETTER FREE LLM ($0)

Only enter Phase 1b if Phase 1 results were GRAY ZONE (2/5 correct or shallow arguments).

The idea: if Phase 1 used Groq (Llama 70B), try Google AI Studio (Gemini Flash free).
Or vice versa. Switch to the OTHER free provider to see if model quality was the issue.

1. Switch to a different free LLM:
```env
# If Phase 1 used Groq, try Gemini Flash free:
LLM_API_KEY=<Google AI Studio free key from aistudio.google.com>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL_NAME=gemini-2.0-flash

# If Phase 1 used Gemini Flash, try Groq free:
LLM_API_KEY=<Groq free key from console.groq.com>
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_NAME=llama-3.3-70b-versatile
```
2. Re-run the SAME 5 markets (same seed packets, same questions)
3. Compare: did prediction quality improve with different model?
4. If YES and now 3+/5 correct → continue to Phase 2
5. If NO, still bad → KILL the project. It's not a model problem, it's a concept problem.

**Phase 1b cost: $0.** Both options are free.

## COST TRACKING

Track all LLM usage for this phase:
- Number of simulations run
- Free tier provider used
- Rate limit issues encountered
- Phase 1: $0
- Phase 1b (if triggered): $0 (different free provider)

## ANTI-SPAGHETTI RULES

- Do NOT write any automation code in this phase. Everything is manual.
- Do NOT modify MiroFish source code.
- Do NOT start building the political bot pipeline yet.
- Focus ONLY on: does MiroFish produce useful political predictions?

## AUDIT AT END OF PHASE

1. `docs/blind-test-results.md` — complete scorecard with all markets
2. Kill/continue decision clearly stated with reasoning
3. Cost tracking documented
4. Polymarket Agent untouched: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && git status`
5. If CONTINUE: list of lessons learned for seed packet design

## WHAT'S NEXT

- If HARD KILL: Archive the project, document learnings, move on. $0 lost.
- If GRAY ZONE: Enter Phase 1b (retest with different free LLM, $0). Then kill or continue.
- If CONTINUE: Phase 2 builds the automated pipeline (seed builder, scanner, probability extractor). Still uses free LLM until Phase 4.
