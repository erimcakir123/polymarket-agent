# AI Removal Plan — Full Rewrite (Seçenek C)

**Trigger phrase:** "AI silme planını uygula"

**Status:** Ready to execute in a fresh session. Do NOT touch this file until
implementation is complete — this IS the spec for the next session.

**Prerequisite:** Bot must be stopped. Dashboard can stay up.

---

## 1. Why

The AI layer (Claude API) is parroting the bookmaker:
- **Parrot rate %81.8** — in 52 resolved trades, AI and bookmaker gave the
  same direction 52/52 times
- Bookmaker direction accuracy %69.2 vs AI %62.9
- AI-only trades (no bookmaker) net **−$22**
- BM-only filter would have yielded **+$73.84** vs actual **+$51.60**

Conclusion: AI adds zero signal, burns Anthropic credit. Delete it, replace
with bookmaker-derived confidence.

---

## 2. New Confidence System (A/B/C only — drop B+ and B-)

User rule:
- **A** = `has_sharp == True` AND `total_weight ≥ 30`  (Pinnacle-grade signal)
- **B** = `has_sharp == True` OR `total_weight ≥ 30`   (one condition met)
- **C** = neither                                       → **SKIP, no trade**

### Data backing (from 230 historical BUY trades, 155 resolved)

Since historical logs don't contain `has_sharp`, we used weight≥50 as a proxy
for "likely has sharp" in the simulation. The proxy is imperfect but directionally
useful.

```
Scenario 1 (A=weight≥50, B=15-49, C<15):
  A:  W/L=59/46  WR=56%  PnL=+$24.39
  B:  W/L= 4/6   WR=40%  PnL=+$10.90
  C:  W/L=18/22  WR=45%  PnL= +$4.58  ← SKIP eliminates this
  A+B total: W/L=63/52  WR=55%  PnL=+$35.29

Baseline (all trades):
  W/L=81/74  WR=52%  PnL=+$39.86
```

**Trade-off:** skipping C trades costs $4.58 in foregone winnings but avoids
30-40 risky low-data trades. Sample size is enough to show direction, but the
precise weight thresholds may need tuning after 2+ weeks of live `has_sharp`
logging.

### Implementation detail

**Historical logs lack `has_sharp`.** We must start logging it from now on so
this rule can be properly enforced. Proxy for the first 2 weeks:

```python
def derive_confidence(bm_weight: float, has_sharp: bool) -> str:
    """Derive confidence tier from bookmaker signal strength.

    A = sharp (Pinnacle/Betfair Exchange) AND ≥30 weight
    B = sharp OR ≥30 weight
    C = neither → skip entry
    """
    if bm_weight is None or bm_weight <= 0:
        return "C"
    if has_sharp and bm_weight >= 30:
        return "A"
    if has_sharp or bm_weight >= 30:
        return "B"
    return "C"
```

New canonical confidence alphabet: **{"A", "B", "C"}** — drop B+, B-, "?".
Every place that currently reads `estimate.confidence in ("A","B+","B-","C")`
must be updated.

---

## 3. Scope — What Gets Deleted / Rewritten / Refactored

### DELETE (full file removal)
- `src/ai_analyst.py` (657 lines, contains `AIAnalyst`, `AIEstimate`, prompt
  templates, budget tracking, Claude API client)
- `tests/test_ai_analyst.py` (98 lines)
- `tests/test_ai_confidence_prompt.py` (57 lines)
- `logs/ai_budget.json`, `logs/ai_budget.backup.json`, `logs/ai_lessons.md`
  (runtime state files)

### REFACTOR (partial, same file)
- `src/agent.py:23, 105, 161` — drop `AIAnalyst` import and instantiation.
  `ctx.ai` removed. Any other reader of `ctx.ai` must be updated.
- `src/entry_gate.py` (≈1250 lines) — **biggest change**:
  - Remove `self.ai.analyze_batch()` calls (2 sites: `_drain_overflow:353`,
    `_analyze_batch:715`). Replace with a bookmaker-driven candidate builder.
  - Rewrite `_evaluate_candidates` two-case strategy:
    - OLD: `ai_favors_yes vs mkt_favors_yes` (consensus/disagree)
    - NEW: `bookmaker_favors_yes vs mkt_favors_yes`
  - Confidence filter: replace `estimate.confidence in _CONF_SKIP` with
    `derive_confidence(bm_weight, has_sharp) == "C"` skip
  - Rank score formula: replace `_CONF_SCORE = {"A":4,"B+":3,"B-":2,"C":1}`
    with `{"A":3,"B":2,"C":0}` (C never enters)
  - Drop `_confidence_c_attempts` tracking loop (still useful — keep for A/B
    where repeated insufficient data blocks a market)
- `src/probability_engine.py` — rename to something like
  `src/bookmaker_probability.py` OR simplify in place:
  - Function `calculate_anchored_probability(ai_prob, bookmaker_prob, ...)`
    → `calculate_bookmaker_probability(bookmaker_prob, num_bookmakers)`
  - Remove `AI_WEIGHT`, `BOOK_WEIGHT`, shrinkage logic, divergence logic
  - Return `(probability, confidence_via_derive_confidence, metadata)`
- `src/cycle_logic.py:104, 164-182` — delete `self_reflection()` method.
  AI-driven self-improvement loop is gone. Remove the `logs/ai_lessons.md`
  read/write path.
- `src/notifier.py:142` — delete `agent.ai.budget_remaining_usd` line in
  Telegram status (find and remove the whole block that displays budget).
- `src/dashboard.py:14, 85-96, 190-198`:
  - Delete `BUDGET_FILE` constant and `/api/budget` route.
  - Simplify `/api/calibration`: it currently compares `ai_probability` vs
    `bookmaker_prob`. After deletion there's only one prob — the calibration
    endpoint becomes bookmaker-vs-outcome accuracy.
- `src/config.py:34-43, 162` — delete `AIConfig` class and `AppConfig.ai`
  field.
- `src/exit_executor.py:433-478` — `try_demote_to_stock` reconstructs a
  `MarketData` + `AIEstimate` for the stock queue. Replace `AIEstimate` with
  a plain dict `{"anchor_probability": ..., "confidence": ..., "is_sharp": ...}`.
- `src/models.py:63-73, 146-159` — rename `Position.ai_probability` and
  `Signal.ai_probability` to `anchor_probability`. Update field_validator
  error messages. Keep the 0.01–0.99 validation.
- `reset_simulation.py:47, 208` + `scripts/reset_bot.py:35, 52` — remove
  references to `ai_budget.json`, `ai_budget.backup.json`, `ai_lessons.md`.

### MECHANICAL RENAME (19 files, ~106 references)
All of these just read `ai_probability` / `ai_prob` as a number and don't
care about its source. Rename wholesale to `anchor_probability` /
`anchor_prob`:
- `src/match_exit.py` (4 refs)
- `src/exit_executor.py` (7 refs — after the AIEstimate removal above)
- `src/portfolio.py` (3 refs — field access on Position)
- `src/reentry.py` (10 refs)
- `src/edge_calculator.py` (7 refs)
- `src/live_strategies.py` (7 refs)
- `src/edge_decay.py` (2 refs)
- `src/self_improve.py` (6 refs)
- `src/price_updater.py` (6 refs)
- `src/match_outcomes.py` (3 refs)
- `src/dashboard.py` (2 refs)
- `src/models.py` (6 refs — already covered above)
- `src/edge_calculator.py` (7 refs)
- `src/reentry_farming.py` (7 refs)
- `src/cycle_logic.py` (2 refs)
- `src/outcome_tracker.py` (4 refs)
- `src/probability_engine.py` (13 refs — most will be deleted)

**Important:** the `trades.jsonl` file already has `ai_prob` written by the
old code. We do NOT rewrite historical logs. The dashboard must handle both
keys (`ai_probability` in old records, `anchor_probability` in new) —
prefer new, fall back to old.

### NEW FILE
- `src/confidence.py` — single function:
  ```python
  def derive_confidence(bm_weight: float, has_sharp: bool) -> str: ...
  ```
  Plus unit tests in `tests/test_confidence.py`.

---

## 4. Execution Phases (fresh session)

### Phase 0 — Safety checks (before touching code)
1. Verify bot is stopped: `tasklist | grep python` shows only dashboards
2. Verify clean git state: `git status` shows no uncommitted work
3. Take an explicit snapshot: `git log -1 --format=%H` → note the hash for rollback
4. Run full test suite baseline: `pytest tests/ -x --tb=line 2>&1 | tail -15`
   → note pass count (should be 112 or higher depending on skipped cases)

### Phase 1 — Add confidence helper (new code only, no deletions yet)
1. Create `src/confidence.py` with `derive_confidence()`
2. Create `tests/test_confidence.py` — cover:
   - `(0, False)` → "C"
   - `(None, False)` → "C"
   - `(15, False)` → "C" (<30 and no sharp)
   - `(30, False)` → "B"
   - `(50, False)` → "B"
   - `(10, True)` → "B" (sharp but low weight)
   - `(30, True)` → "A"
   - `(100, True)` → "A"
3. Run `pytest tests/test_confidence.py` → green
4. Commit: `feat(confidence): add bookmaker-derived confidence helper`

### Phase 2 — Log `has_sharp` flag in BUY events (forward-only data)
1. `src/entry_gate.py` — find where `bookmaker_count`, `bookmaker_prob` are
   written to the BUY trade_log.log() call. Add `"has_sharp": _has_sharp`.
2. `_has_sharp` must come from the Odds API + ESPN combined path. Inspect
   `_odds_probs` gathering at ~line 820-862. The `odds_api_result.get("has_sharp")`
   flag exists (line 565). We need to preserve it through to the BUY event.
3. Commit: `feat(logging): record has_sharp flag in BUY trade events`

Rationale: even if Phase 3+ fails, after Phase 2 we'll have real `has_sharp`
data building up — future conf calibration can use real signal.

### Phase 3 — Refactor `probability_engine.py` to BM-only
1. Replace `calculate_anchored_probability()` with
   `calculate_bookmaker_probability(bookmaker_prob, num_bookmakers, has_sharp)`
2. Return: `(probability, confidence, metadata_dict)`
3. If `bookmaker_prob is None or <= 0` → raise or return `(None, "C", {})`
4. Delete `AI_WEIGHT`, `BOOK_WEIGHT`, `SHRINKAGE_*`, `HIGH_DIVERGENCE_THRESHOLD`
   constants
5. Delete `AnchoredProbability` dataclass or rename to
   `BookmakerProbability`. Field names: `probability`, `confidence`,
   `bookmaker_prob`, `num_bookmakers`, `has_sharp`.
6. Update `src/config.py:ProbabilityEngineConfig` — remove `book_weight`,
   `ai_weight`, `shrinkage_factor`, `high_divergence_threshold`.
7. Any caller of `calculate_anchored_probability` must be updated now
   (only `entry_gate.py:863`).
8. Run `pytest tests/` → expect `test_probability_engine.py` to fail (needs
   rewrite). Fix those tests.
9. Commit: `refactor(probability_engine): bookmaker-only, drop AI blend`

### Phase 4 — Update `Position` / `Signal` models
1. `src/models.py` — rename `ai_probability` → `anchor_probability` in both
   `Position` and `Signal`.
2. Field validator error message: `"anchor_probability={v} outside [0.01, 0.99]"`
3. **Backward-compat for positions.json on disk:** Position uses Pydantic. On
   load, accept either key. Use `model_validator(mode='before')` to rename
   `ai_probability` → `anchor_probability` if present.
4. Run tests — everything that reads `pos.ai_probability` will break here;
   tests should flag them.
5. Don't commit yet — tests are broken.

### Phase 5 — Mechanical rename (19 files)
Use `Grep` + `Edit replace_all` for each file:
- `ai_probability` → `anchor_probability`
- `ai_prob` → `anchor_prob` (watch out: `ai_prob=est.ai_probability` patterns
  may need context-sensitive edits)

Files (in dependency order):
1. `src/edge_calculator.py`
2. `src/edge_decay.py`
3. `src/match_exit.py`
4. `src/reentry.py`
5. `src/reentry_farming.py`
6. `src/live_strategies.py`
7. `src/portfolio.py`
8. `src/price_updater.py`
9. `src/match_outcomes.py`
10. `src/outcome_tracker.py`
11. `src/self_improve.py`
12. `src/cycle_logic.py`
13. `src/exit_executor.py` (deferred partial — AIEstimate removal here)
14. `src/dashboard.py` (keep backward-compat for old logs)
15. `src/notifier.py`

After each file: `python -m py_compile <file>` → must pass.

Commit: `refactor(models): rename ai_probability → anchor_probability (19 files)`

### Phase 6 — Delete AI from `entry_gate.py`
This is the risky step. Approach as a surgery:

1. Read `src/entry_gate.py` fully (it's ~1250 lines) — understand current
   flow before touching.
2. In `_analyze_batch` (around line 364):
   - Delete `self.ai.analyze_batch(...)` call at line 715
   - Replace with a new helper `_build_bookmaker_estimates(markets)` that
     returns `dict[cid, BookmakerEstimate]` where `BookmakerEstimate` is a
     simple dataclass:
     ```python
     @dataclass
     class BookmakerEstimate:
         anchor_probability: float   # P(YES) from bookmaker
         confidence: str              # "A" / "B" / "C"
         bookmaker_prob: float
         num_bookmakers: float        # total_weight
         has_sharp: bool
     ```
   - Place `BookmakerEstimate` in `src/models.py` (or a new
     `src/bookmaker_estimate.py` if we want it isolated).
3. In `_drain_overflow` (line 340): do the same replacement.
4. In `_evaluate_candidates`:
   - Replace `estimate.confidence in _CONF_SKIP` with
     `estimate.confidence == "C"`
   - Rewrite the consensus/disagree block (lines 869-907):
     - `ai_p = estimate.anchor_probability` (was ai_probability)
     - `ai_favors_yes` → `book_favors_yes` (rename for clarity)
     - Logic stays the same: if BM and market agree → Case A, else Case B
5. In the `try_demote_to_stock` call site — update to use
   `BookmakerEstimate` instead of `AIEstimate`
6. Delete `_confidence_c_attempts` if it becomes dead, OR keep it keyed on
   "C returned" (repeated insufficient data should still block)
7. Run: `python -m py_compile src/entry_gate.py`
8. Run: `pytest tests/ -x` — expect failures in test_entry_gate* tests. Fix.
9. Commit: `refactor(entry_gate): replace AI analysis with bookmaker-derived estimates`

### Phase 7 — Delete `ai_analyst.py` and related
1. `src/agent.py:23, 105, 161` — remove `from src.ai_analyst import AIAnalyst`,
   remove `self.ai = AIAnalyst(config.ai)`, remove `ai=self.ai` from
   EntryGate kwargs.
2. `src/cycle_logic.py:104, 164-182` — delete `self_reflection()` method
   entirely. Also delete the cron/schedule that calls it (search for
   `self_reflection` in cycle_logic and agent).
3. `src/exit_executor.py:433, 478` — the `from src.ai_analyst import AIEstimate`
   import is gone. Replace the `AIEstimate(...)` construction with
   `BookmakerEstimate(...)` (from Phase 6).
4. `src/notifier.py:142` — remove `agent.ai.budget_remaining_usd` and the
   entire budget display block.
5. `src/dashboard.py:14, 85-96` — remove `BUDGET_FILE`, remove `/api/budget`
   route.
6. `src/dashboard.py:190-198` — simplify `/api/calibration`: it currently
   compares `ai_probability` vs `bookmaker_prob`. After deletion drop AI
   side, keep bookmaker vs outcome only.
7. `src/config.py:34-43, 162` — delete `AIConfig` class and
   `AppConfig.ai: AIConfig = AIConfig()` field.
8. **Finally** delete `src/ai_analyst.py` entirely.
9. Delete `tests/test_ai_analyst.py` + `tests/test_ai_confidence_prompt.py`.
10. `reset_simulation.py:47, 208` + `scripts/reset_bot.py:35, 52` — remove
    `ai_budget.json`, `ai_budget.backup.json`, `ai_lessons.md` references.
11. Delete `logs/ai_budget.json`, `logs/ai_budget.backup.json`,
    `logs/ai_lessons.md` if they exist (they are runtime state, safe).
12. Remove `anthropic` from `requirements.txt` if listed.
13. `python -m py_compile` over all of `src/` → must pass.
14. `pytest tests/ --tb=short` → must be 100% green.
15. Commit: `feat(ai-removal): delete AIAnalyst and replace with bookmaker-only pipeline`

### Phase 8 — Audit (grep-first manual)
**CLAUDE.md §3 audit protocol applies** because this is Large change.
Two consecutive CLEAN audits required.

Audit 1 — Broken imports, dead refs:
```
grep -rn "ai_analyst\|AIAnalyst\|AIEstimate\|anthropic\|ai_probability\|ai_prob\|budget_remaining\|ai_lessons\|ai_budget\|_call_claude\|self_reflection" src/ tests/
```
Every match must be either:
- Expected (e.g., backward-compat dashboard read)
- Commented for a known reason
- Or removed

Audit 2 — Runtime logic sanity:
- Re-read `entry_gate._evaluate_candidates`
- Re-read `exit_executor.try_demote_to_stock`
- Re-read `probability_engine.calculate_bookmaker_probability`
- Confirm no stale `AIEstimate` field access

### Phase 9 — dry_run smoke test
1. Bot must still be stopped
2. Start fresh: `python -m src.main` (dry_run mode)
3. Watch `logs/bot.log` for 2 cycles (~5 minutes)
4. Look for:
   - `NameError` / `AttributeError` / `ImportError` — any means **STOP and fix**
   - BUY events must have `has_sharp` flag written
   - `estimate.confidence` should be "A", "B", or "C" only (no B+/B-/?)
   - No Claude API calls (no `anthropic` usage, budget file untouched)
5. If bot completes 2 cycles without errors:
   - Tail the bot.log: any `ERROR` or `WARNING` lines related to the refactor?
   - `tasklist | grep python` → only 1 src.main process
6. If smoke test passes, stop the bot: `taskkill /PID <pid> /F`
7. Final commit: `chore(ai-removal): dry-run smoke test passed`

### Phase 10 — Notes for user
- Self-improvement loop is dead. If user wants it back, it must be rebuilt
  without an LLM (e.g., parameter sweep driven by realized PnL).
- Dashboard "AI Budget" widget is gone. Consider removing the HTML element
  if it exists.
- `logs/calibration_events.jsonl` still works but now only tracks
  `anchor_probability` (bookmaker-derived).
- `anchor_probability` field in trades.jsonl will be NEW. Old records still
  have `ai_probability`. Any analysis script must handle both.

---

## 5. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 5 rename misses a file → NameError at runtime | High | Phase 8 grep audit catches |
| Position deserialization fails on old positions.json | Medium | Phase 4 `model_validator(mode='before')` handles rename |
| Entry gate rewrite introduces logic bug | High | Phase 9 dry-run smoke test + pytest |
| Dashboard crashes on missing budget endpoint | Low | Phase 7 explicit removal |
| `reasoning_pro` / `reasoning_con` fields referenced somewhere not grepped | Medium | Additional grep: `reasoning_pro\|reasoning_con` |
| Test fixtures construct `AIEstimate` objects | Medium | Remove test files in Phase 7; fix any stragglers |
| Window memory bloat during audit | Medium | Session-split — do Phases 0-2 in one, 3-5 next, 6-9 last |

---

## 6. Acceptance Criteria

Before marking this plan complete:
- [ ] `grep -rn "anthropic" src/` → zero matches
- [ ] `grep -rn "AIAnalyst\|AIEstimate" src/` → zero matches
- [ ] `grep -rn "self\.ai\." src/` → zero matches
- [ ] `grep -rn "ai_probability" src/` → zero matches in source (old
      trades.jsonl records and backward-compat readers OK)
- [ ] `pytest tests/ -x --tb=short` → all green
- [ ] `python -m py_compile src/*.py` → all pass
- [ ] Bot starts in dry_run, completes 2 cycles, no errors in log
- [ ] `trades.jsonl` new BUY events contain `has_sharp` key
- [ ] `trades.jsonl` new BUY events contain `anchor_probability` key (not
      `ai_prob`)
- [ ] `logs/ai_budget.json` not recreated after 2 bot cycles (no API calls)
- [ ] Dashboard loads without JS errors when old `/api/budget` is gone (check
      that frontend `dashboard/*.html` doesn't reference it)

---

## 7. What's NOT in Scope

- New strategy logic. We're preserving the existing consensus/disagree case
  framework; only the source of probability changes (AI → bookmaker).
- Confidence threshold tuning. We're using `{≥30 weight, has_sharp}` as the
  starting point. User can retune after 2 weeks of new data.
- Dashboard HTML/JS refactor. Just remove the dead endpoint, let the frontend
  silently skip the missing data.
- Removing scout queue or news_scanner — these can still provide contextual
  info if we choose to use them for anything else later.
- Odds API / ESPN odds fetching — totally untouched, still the primary
  source.

---

## 8. Historical Context (for the next session)

This plan was designed after:
- 2026-04-10/11 ground-truth analysis showed AI-BM parrot rate %81.8
- 230 historical BUY trade simulation of 3-tier confidence system
- User explicitly requested Seçenek C (full rewrite) over stub/kill-switch
- Dead code philosophy: user wants zero dead code, spaghetti is forbidden

The prior session left these artifacts in place:
- Session deleted `catastrophic_floor` exit rule (commit `d5c7d80`)
- Session fixed phantom SCALE_OUT bug in WS force path (commit `d5c7d80`)
- Session deleted 3 dead tests + orphan `_tmp_*.py` files (commit `c4d30ca`)

The next session starts from that clean baseline.
