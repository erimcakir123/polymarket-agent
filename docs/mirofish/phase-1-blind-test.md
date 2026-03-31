# MiroFish Political Bot — Phase 1: Blind Validation Test (FREE)

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

Phase 0 is complete — MiroFish is installed and running. We verified the pipeline works mechanically. Now we test whether MiroFish produces USEFUL predictions on real Polymarket political markets.

**This is the first KILL/CONTINUE decision point.** We test with FREE LLM first ($0 cost). If free LLM shows promise → great. If results are mixed → we decide whether to try better LLM (Phase 1b, ~$3) or kill.

## OBJECTIVE

Run MiroFish simulations on 3-5 ALREADY RESOLVED Polymarket political markets using a FREE LLM. We know the real outcome but MiroFish doesn't. Compare MiroFish's probability estimates against actual results.

## HARD RULES

1. **Read Phase 0's `docs/setup-log.md` first** — understand what was configured.
2. **Do NOT tell MiroFish the actual outcome** — this is a blind test.
3. **$0 COST — use the same free LLM from Phase 0.** Do NOT upgrade to paid yet.
4. **Do NOT touch Polymarket Agent** — still 100% off-limits.
5. **Document EVERYTHING** — write results in `docs/blind-test-results.md`.
6. **Be honest about results** — if MiroFish fails, say so clearly.

## STEP 1: Keep Free LLM, Verify It Works

Use the SAME free LLM from Phase 0 (Groq free / Google AI Studio free / whatever worked).
Do NOT upgrade to paid. We test the concept at $0 first.

If Phase 0 used a very small model (7B or less) that produced gibberish, upgrade to the BEST FREE option:
- Groq free: Llama 3.3 70B (good quality, 30 req/min, 6000 req/day)
- Google AI Studio free: Gemini Flash (good quality, 15 req/min, 1500 req/day)

Both are free. Pick whichever has better rate limits for your simulation size.

**Important:** Simulations will be SLOW with free tier rate limits. That's OK — we're testing signal quality, not speed. Run overnight if needed.

## STEP 2: Find Resolved Political Markets

Go to Polymarket and find 3-5 markets that:
- Are RESOLVED (outcome is known)
- Were POLITICAL or GEOPOLITICAL (not sports, not crypto)
- Had decent volume (>$100K)
- Resolved in the last 1-3 months (recent enough for relevant news)

Use the Polymarket API:
```python
import requests
markets = requests.get(
    "https://gamma-api.polymarket.com/markets",
    params={"closed": "true", "limit": 50, "order": "volume", "ascending": "false"}
).json()
# Filter for political markets manually
```

For each market, record:
- Market question (exact text)
- Resolution rules
- Actual outcome (YES or NO)
- Final price before resolution
- Volume
- Resolution date

**Save this data but do NOT include actual outcomes in the seed packets.**

## STEP 3: Build Seed Packets

For each market, create a structured seed document. This is what MiroFish will use as input.

Template:
```
MARKET QUESTION:
[Exact question from Polymarket]

RESOLUTION RULES:
[Full resolution rules, verbatim]

Resolution source: [Official data provider]
End date: [Original end date]

BASE FACTS (as of 2 weeks before resolution):
1. [Verifiable fact]
2. [Verifiable fact]
3. [Verifiable fact]

RECENT HEADLINES (from before resolution):
1. [Real headline from that period]
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

**CRITICAL: Use information that was available BEFORE the market resolved. Do not include post-resolution news.**

Research headlines and facts from the appropriate time period using web search.

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

## STEP 5: Score Results

Create a scorecard in `docs/blind-test-results.md`:

```markdown
## Market 1: [Question]
- Actual outcome: [YES/NO]
- MiroFish ensemble probability: [X%]
- MiroFish direction: [Correct/Wrong]
- Calibration: [Was 70% prediction roughly right 70% of the time?]
- Notes: [Any interesting observations]

## Market 2: ...
(repeat for all markets)

## OVERALL SCORE
- Markets tested: N
- Directionally correct: X/N
- Average confidence: X%
- Average probability error: X%
```

## KILL/CONTINUE CRITERIA

### CONTINUE to Phase 2 (still free) if:
- **3+ out of 5 directionally correct** — better than chance
- **Predictions show meaningful spread** (not all 45-55%) — MiroFish has opinions
- **Arguments in reports are substantive** — not just restating the question

### GO TO PHASE 1b (retest with different free LLM, $0) if:
- **2 out of 5 correct** — inconclusive, could be LLM quality issue
- **Arguments are shallow but directionally sensible** — better model might fix
- **Simulations ran but output was low-quality text** — clearly a model limitation

### HARD KILL if:
- **0-1 out of 5 correct** — concept doesn't work, not just model quality
- **All predictions cluster around 50%** — MiroFish has no opinion, just noise
- **Simulations produce gibberish or crash** — fundamental technical failure
- **Reports have no substantive arguments** — simulation is just noise

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
