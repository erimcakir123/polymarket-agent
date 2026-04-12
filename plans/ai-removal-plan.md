# AI Removal Plan — Full Rewrite (Seçenek C)

**Trigger phrase:** "AI silme planını uygula"

**Status:** IN PROGRESS — Phase 0-2 done, Phase 3 half-done. Resume from Phase 3 remaining steps.

**Rollback hash:** `cc25df8` (last clean commit before any changes)

**Prerequisite:** Bot must be stopped. Dashboard can stay up.

**SESSION RULES:**
- NEVER run `pytest tests/` (full suite) — causes Windows crash (RAM spike ~500 MB)
- Only run single-file tests: `pytest tests/test_specific.py`
- Max 1 audit agent per session, manual audit preferred
- Compile check: `python -m py_compile src/file.py` instead of full pytest

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

### Rules

- **A** = `has_sharp == True` AND `bm_weight >= 5`
- **B** = `bm_weight ≥ 5` (at least a few bookmakers, sharp not required)
- **C** = `bm_weight < 5` or no bookmaker data → **SKIP, no trade**

### Implementation (DONE — `src/confidence.py`)

```python
def derive_confidence(bm_weight: float | None, has_sharp: bool) -> str:
    if bm_weight is None or bm_weight < 5:
        return "C"
    if has_sharp:
        return "A"
    return "B"
```

New canonical confidence alphabet: **{"A", "B", "C"}** — drop B+, B-, "?".

---

## 3. Scope — What Gets Deleted / Rewritten / Refactored

### DELETE (full file removal)
- `src/ai_analyst.py` (657 lines)
- `tests/test_ai_analyst.py` (98 lines)
- `tests/test_ai_confidence_prompt.py` (57 lines)
- `logs/ai_budget.json`, `logs/ai_budget.backup.json`, `logs/ai_lessons.md`

### REFACTOR (partial, same file)
- `src/agent.py` — drop `AIAnalyst` import/instantiation, `ctx.ai`
- `src/entry_gate.py` (~1250 lines) — biggest change:
  - Remove `self.ai.analyze_batch()` calls
  - Rewrite two-case strategy: `ai_favors_yes` → `book_favors_yes`
  - Confidence filter: `derive_confidence() == "C"` skip
  - Rank score: `{"A":3,"B":2,"C":0}`
- `src/probability_engine.py` — DONE (see Phase 3)
- `src/cycle_logic.py` — delete `self_reflection()` method
- `src/notifier.py` — delete budget display
- `src/dashboard.py` — delete `/api/budget`, simplify `/api/calibration`
- `src/config.py` — delete `AIConfig`, clean `ProbabilityEngineConfig`
- `src/exit_executor.py` — replace `AIEstimate` with `BookmakerEstimate`
- `src/models.py` — rename `ai_probability` → `anchor_probability`
- `reset_simulation.py` + `scripts/reset_bot.py` — remove AI file refs

### MECHANICAL RENAME (19 files, ~106 references)
`ai_probability` → `anchor_probability`, `ai_prob` → `anchor_prob`

### NEW FILES (DONE)
- `src/confidence.py` — `derive_confidence()` 
- `tests/test_confidence.py` — 10 parametrized tests, all green

---

## 4. Execution Phases — Progress Tracker

### Phase 0 — Safety checks ✅ DONE
- Bot stopped (only dashboards running, PIDs 3124 + 17660)
- Git clean (only .gitignore modified)
- Rollback hash: `cc25df8`
- Test baseline: 494 tests collected (circuit_breaker has pre-existing file lock issue on Windows — unrelated)

### Phase 1 — Add confidence helper ✅ DONE
- Created `src/confidence.py` with `derive_confidence(bm_weight, has_sharp)` → A/B/C
- Created `tests/test_confidence.py` — 10 parametrized tests, all green
- **Not yet committed** (will batch with other phases)

### Phase 2 — Log `has_sharp` flag in BUY events ✅ DONE
Changes in `src/entry_gate.py`:
- Line 820: Added `_anchor_has_sharp = False` variable
- Line 833: Odds API → `if _mkt_odds.get("has_sharp"): _anchor_has_sharp = True`
- Line 852: ESPN → `if _espn_odds.get("has_sharp"): _anchor_has_sharp = True`
- Line 1033: Added `"has_sharp": _anchor_has_sharp` to candidate dict
- Line 1182: Added `"has_sharp": c.get("has_sharp", False)` to BUY trade_log
- Compile check passed

### Phase 3 — Refactor `probability_engine.py` to BM-only 🔶 HALF DONE

**DONE:**
- `src/probability_engine.py` fully rewritten:
  - `AnchoredProbability` → `BookmakerProbability` (dataclass)
  - `calculate_anchored_probability()` → `calculate_bookmaker_probability(bookmaker_prob, num_bookmakers, has_sharp)`
  - Deleted: `AI_WEIGHT`, `BOOK_WEIGHT`, `SHRINKAGE_*`, `HIGH_DIVERGENCE_THRESHOLD`
  - Deleted: `get_edge_threshold_adjustment()` (was dead code — no callers)
  - New function imports `derive_confidence` from `src.confidence`
  - Returns `BookmakerProbability(probability, confidence, bookmaker_prob, num_bookmakers, has_sharp)`

**REMAINING (do these next):**
1. **`src/config.py`** — `ProbabilityEngineConfig` still has old fields:
   ```python
   class ProbabilityEngineConfig(BaseModel):
       book_weight: float = 0.55      # DELETE
       ai_weight: float = 0.45        # DELETE
       shrinkage_factor: float = 0.10 # DELETE
       high_divergence_threshold: float = 0.15  # DELETE
   ```
   Either delete the entire class (since no config fields remain) or keep as
   empty placeholder. Check if `AppConfig.probability_engine` is referenced
   anywhere — if not, delete both. Also check `config.yaml` for these keys.

2. **`src/entry_gate.py:736,868`** — caller still uses old function:
   ```python
   # Line 736:
   from src.probability_engine import calculate_anchored_probability
   # Line 868-872:
   anchored = calculate_anchored_probability(
       ai_prob=estimate.ai_probability,
       bookmaker_prob=_anchor_book_prob,
       num_bookmakers=_anchor_num_books,
   )
   ```
   Update to:
   ```python
   from src.probability_engine import calculate_bookmaker_probability
   # ...
   anchored = calculate_bookmaker_probability(
       bookmaker_prob=_anchor_book_prob,
       num_bookmakers=_anchor_num_books,
       has_sharp=_anchor_has_sharp,
   )
   ```
   Note: `anchored.probability` is used at line 900 (CASE B). This still works
   because `BookmakerProbability` also has `.probability`. BUT the variable
   `ai_p = estimate.ai_probability` at line 874 is still AI-based — this will
   be replaced in Phase 6 when the full entry_gate AI removal happens.

3. **`tests/test_probability_engine.py`** — needs full rewrite to test
   `calculate_bookmaker_probability` instead of `calculate_anchored_probability`.
   Run: `pytest tests/test_probability_engine.py` to verify.

4. **Compile check** all changed files, then commit:
   `refactor(probability_engine): bookmaker-only, drop AI blend`

### Phase 4 — Update `Position` / `Signal` models (PENDING)
1. `src/models.py` — rename `ai_probability` → `anchor_probability` in both
   `Position` and `Signal`.
2. Field validator error message: `"anchor_probability={v} outside [0.01, 0.99]"`
3. **Backward-compat for positions.json on disk:** Position uses Pydantic. On
   load, accept either key. Use `model_validator(mode='before')` to rename
   `ai_probability` → `anchor_probability` if present.
4. Run tests — everything that reads `pos.ai_probability` will break here;
   tests should flag them.
5. Don't commit yet — tests are broken until Phase 5.

### Phase 5 — Mechanical rename (19 files) (PENDING)
Use `Grep` + `Edit replace_all` for each file:
- `ai_probability` → `anchor_probability`
- `ai_prob` → `anchor_prob`

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
14. `src/dashboard.py` (keep backward-compat for old logs: `ai_probability` fallback)
15. `src/notifier.py`

After each file: `python -m py_compile <file>` → must pass.

**Important:** `trades.jsonl` has `ai_prob` in old records. Dashboard must
handle both keys — prefer `anchor_probability`, fall back to `ai_probability`.

Commit: `refactor(models): rename ai_probability → anchor_probability (19 files)`

### Phase 6 — Delete AI from `entry_gate.py` (PENDING)
This is the risky step. Approach as surgery:

1. Read `src/entry_gate.py` fully — understand current flow before touching.
2. In `_analyze_batch` (~line 364):
   - Delete `self.ai.analyze_batch(...)` call (~line 715)
   - Replace with `_build_bookmaker_estimates(markets)` helper
   - `BookmakerEstimate` dataclass in `src/models.py`:
     ```python
     @dataclass
     class BookmakerEstimate:
         anchor_probability: float
         confidence: str
         bookmaker_prob: float
         num_bookmakers: float
         has_sharp: bool
     ```
3. In `_drain_overflow` (~line 340): same replacement.
4. In `_evaluate_candidates`:
   - Replace `estimate.confidence in _CONF_SKIP` → `estimate.confidence == "C"`
   - Rewrite consensus/disagree block:
     - `ai_p` → `book_p` (from `estimate.anchor_probability`)
     - `ai_favors_yes` → `book_favors_yes`
     - Logic stays same: BM and market agree → Case A, else Case B
   - Rank score: `{"A":3,"B":2,"C":0}` (C never enters)
5. Update `try_demote_to_stock` → use `BookmakerEstimate` instead of `AIEstimate`
6. Keep `_confidence_c_attempts` keyed on "C returned"
7. Compile check + targeted test
8. Commit: `refactor(entry_gate): replace AI analysis with bookmaker-derived estimates`

### Phase 7 — Delete `ai_analyst.py` and related (PENDING)
1. `src/agent.py` — remove `AIAnalyst` import, instantiation, `ai=self.ai`
2. `src/cycle_logic.py` — delete `self_reflection()` method + its caller
3. `src/exit_executor.py` — replace `AIEstimate` with `BookmakerEstimate`
4. `src/notifier.py` — remove `agent.ai.budget_remaining_usd` block
5. `src/dashboard.py` — remove `BUDGET_FILE`, `/api/budget` route, simplify `/api/calibration`
6. `src/config.py` — delete `AIConfig` class and `AppConfig.ai` field
7. **Delete** `src/ai_analyst.py`
8. **Delete** `tests/test_ai_analyst.py` + `tests/test_ai_confidence_prompt.py`
9. `reset_simulation.py` + `scripts/reset_bot.py` — remove AI file refs
10. Delete `logs/ai_budget.json`, `logs/ai_budget.backup.json`, `logs/ai_lessons.md`
11. Remove `anthropic` from `requirements.txt` if listed
12. Compile check all `src/`
13. Targeted test run
14. Commit: `feat(ai-removal): delete AIAnalyst and replace with bookmaker-only pipeline`

### Phase 8 — Audit (grep-first manual) (PENDING)
**CLAUDE.md §3 audit protocol applies** — Large change, 2 consecutive CLEAN required.

Audit 1 — Broken imports, dead refs:
```
grep -rn "ai_analyst\|AIAnalyst\|AIEstimate\|anthropic\|ai_probability\|ai_prob\|budget_remaining\|ai_lessons\|ai_budget\|_call_claude\|self_reflection" src/ tests/
```
Every match must be: expected (backward-compat), commented, or removed.

Audit 2 — Runtime logic sanity:
- Re-read `entry_gate._evaluate_candidates`
- Re-read `exit_executor.try_demote_to_stock`
- Re-read `probability_engine.calculate_bookmaker_probability`
- Confirm no stale `AIEstimate` field access

### Phase 9 — dry_run smoke test (PENDING)
1. Start: `python -m src.main` (dry_run mode)
2. Watch `logs/bot.log` for 2 cycles (~5 minutes)
3. Check: no `NameError`/`AttributeError`/`ImportError`, BUY events have
   `has_sharp` + `anchor_probability`, confidence is A/B/C only, no Claude
   API calls
4. Stop bot, final commit: `chore(ai-removal): dry-run smoke test passed`

---

## 5. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 5 rename misses a file → NameError at runtime | High | Phase 8 grep audit catches |
| Position deserialization fails on old positions.json | Medium | Phase 4 `model_validator(mode='before')` handles rename |
| Entry gate rewrite introduces logic bug | High | Phase 9 dry-run smoke test + pytest |
| Dashboard crashes on missing budget endpoint | Low | Phase 7 explicit removal |
| `reasoning_pro` / `reasoning_con` fields referenced somewhere | Medium | Additional grep |
| Test fixtures construct `AIEstimate` objects | Medium | Remove test files in Phase 7 |
| **Windows RAM crash from full pytest** | **High** | **NEVER run `pytest tests/` — single file only** |

---

## 6. Acceptance Criteria

Before marking this plan complete:
- [ ] `grep -rn "anthropic" src/` → zero matches
- [ ] `grep -rn "AIAnalyst\|AIEstimate" src/` → zero matches
- [ ] `grep -rn "self\.ai\." src/` → zero matches
- [ ] `grep -rn "ai_probability" src/` → zero matches in source (old
      trades.jsonl records and backward-compat readers OK)
- [ ] `python -m py_compile src/*.py` → all pass
- [ ] Targeted test files pass (NOT full suite)
- [ ] Bot starts in dry_run, completes 2 cycles, no errors in log
- [ ] `trades.jsonl` new BUY events contain `has_sharp` key
- [ ] `trades.jsonl` new BUY events contain `anchor_probability` key
- [ ] `logs/ai_budget.json` not recreated after 2 bot cycles
- [ ] Dashboard loads without JS errors when `/api/budget` is gone

---

## 7. What's NOT in Scope

- New strategy logic (consensus/disagree framework preserved)
- Confidence threshold tuning (≥5 weight as starting point)
- Dashboard HTML/JS refactor
- Removing scout queue or news_scanner
- Odds API / ESPN odds fetching — totally untouched

---

## 8. Historical Context

- 2026-04-10/11 ground-truth analysis showed AI-BM parrot rate %81.8
- 2026-04-12 first implementation session: Phase 0-2 done, Phase 3 half-done
- User explicitly requested Seçenek C (full rewrite) over stub/kill-switch
- Dead code philosophy: user wants zero dead code

**Git state (uncommitted):**
- NEW: `src/confidence.py`, `tests/test_confidence.py`
- MODIFIED: `src/entry_gate.py` (has_sharp logging), `src/probability_engine.py` (full rewrite)
- No commits made yet — all changes are staged/unstaged
