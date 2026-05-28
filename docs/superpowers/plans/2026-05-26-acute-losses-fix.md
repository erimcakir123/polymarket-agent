# Acute Losses Fix — 3 Surgical Changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Tasks use checkbox (`- [ ]`) syntax.

**Goal:** Stop the 3 specific data-confirmed bleeding patterns from the 51-trade analysis (2026-05-26):

1. **ATP_set_totals B confidence**: 2W/10L, **-$179 net** — clear negative EV, kill it
2. **same_market_type chain duplicates on B**: aguilar 3.5+4.5 type chains, A is fine
3. **simple stop_loss on set_handicap markets**: shnaide $66 katastrofik (2/2 premature) — graduated_sl stays

**Architecture:**
- Config-driven exclusions (no hardcoded market-type strings in business logic).
- Confidence-aware guards (A retains current behavior — A win rate 77%, lift cannot harm).
- Drift cleanup at end. Final ARCH_GUARD compliance check.
- Tennis-lab only (main bot has its own MLB submarket dynamics, not in scope).

**Repo:** `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\`

**Drift policy:** "dead code drift code vs bişey olmasın". After Task 4 we sweep for stale references. Task 5 is the ARCH_GUARD repair safety net.

---

## Task 1: Exclude ATP_set_totals B from entry

**Files:**
- Modify: `src/config/settings.py` (add `EntryExcludeCombo` model + `exclude_combos` field on EdgeConfig)
- Modify: `config_tennis.yaml` (add the exclusion)
- Modify: `src/strategy/enrichment/tennis_market_enricher.py` (post-classify_tier check)
- Modify: `tests/unit/config/test_tennis_sizing.py` or appropriate test for config load
- Modify: `tests/unit/strategy/enrichment/test_tennis_market_enricher.py` for enricher exclude

- [ ] **Step 1: Write failing config-load test**

In a tennis-config test (e.g., `tests/unit/config/test_tennis_settings.py`):

```python
def test_edge_exclude_combos_loaded_from_yaml() -> None:
    from src.config.settings import load_config
    from pathlib import Path
    cfg = load_config(Path("config_tennis.yaml"))
    excl = cfg.edge.exclude_combos
    assert any(
        c.tour == "atp" and c.market_type == "tennis_set_totals" and c.confidence == "B"
        for c in excl
    )
```

- [ ] **Step 2: Run failing**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/config/ -v -k "exclude_combos"
```

Expected fail: AttributeError on `cfg.edge.exclude_combos`.

- [ ] **Step 3: Add EntryExcludeCombo + exclude_combos field**

In `src/config/settings.py`, add near EdgeConfig (search for `class EdgeConfig`):

```python
class EntryExcludeCombo(BaseModel):
    """Block entry when (tour, market_type, confidence) all match.

    Used to surgically disable bleeding (tour, market_type, conf) combos
    without closing an entire confidence tier. Data-driven: each entry
    here has a 50+ trade history showing negative EV.
    """
    tour: str          # "atp" | "wta"
    market_type: str   # Polymarket sports_market_type (e.g., "tennis_set_totals")
    confidence: str    # "A" | "B"
```

Add field to EdgeConfig:

```python
class EdgeConfig(BaseModel):
    # ... existing fields ...
    exclude_combos: List[EntryExcludeCombo] = []
```

- [ ] **Step 4: Add yaml block in config_tennis.yaml**

Under the `edge:` section, append:

```yaml
  # Data-driven entry exclusions (2026-05-26 analysis: 51 closed trades).
  # ATP_set_totals B: 2W/10L, -$179 net, -$14.93 EV/trade. Clear negative.
  # WTA_set_totals B and ATP_set_handicap B left ENABLED (positive EV in data).
  exclude_combos:
    - tour: atp
      market_type: tennis_set_totals
      confidence: B
```

- [ ] **Step 5: Wire enricher to honor exclude_combos**

In `src/strategy/enrichment/tennis_market_enricher.py`, find the `classify_tier` function and the `enrich()` function where the tier result is used. After `tier = classify_tier(...)` (which returns "A" / "B" / "skip"), add a check:

```python
# Data-driven exclude (config.edge.exclude_combos)
if tier in ("A", "B"):
    tour = parsed.get("tour", "atp")
    smt = market.sports_market_type or ""
    for excl in cfg.edge.exclude_combos:
        if excl.tour == tour and excl.market_type == smt and excl.confidence == tier:
            return None  # blocked combo, skip this candidate
```

Verify `cfg` is accessible at that point (probably passed as arg).

- [ ] **Step 6: Add enricher exclude test**

In `tests/unit/strategy/enrichment/test_tennis_market_enricher.py`:

```python
def test_enrich_blocks_atp_set_totals_b_when_excluded() -> None:
    """ATP_set_totals B is data-driven excluded; enrich returns None."""
    from src.config.settings import EntryExcludeCombo
    # build a minimal cfg with the exclusion (mirror existing test fixture pattern)
    # build a market with sports_market_type="tennis_set_totals" + atp slug
    # build ratings/sackmann_matches so candidate would be tier B
    # call enrich(...) and assert is None
    # (Mirror an existing enricher test for fixture setup)
    pass  # IMPLEMENT — read existing tests for the fixture pattern
```

The implementer must actually write this test using existing fixture conventions in that file.

- [ ] **Step 7: Run full tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/config/ tests/unit/strategy/enrichment/test_tennis_market_enricher.py -v
```

All PASS.

- [ ] **Step 8: Commit**

```bash
git add src/config/settings.py config_tennis.yaml src/strategy/enrichment/tennis_market_enricher.py tests/
git commit -m "feat(entry): exclude ATP_set_totals B — data-driven kill of -\$179 EV combo

51-trade analysis shows ATP_set_totals B: 2W/10L, -\$14.93 EV/trade, -\$179 net.
WTA_set_totals B and ATP_set_handicap B left enabled (positive EV).

Implemented as config.edge.exclude_combos list — extensible, no hardcoded
market-type strings in business logic. New EntryExcludeCombo pydantic model.
Enricher post-classify_tier checks exclude_combos and returns None on match."
```

---

## Task 2: same_market_type guard, ONLY for B confidence

**Files:**
- Modify: `src/orchestration/_entry_processor_signals.py` (where event_count cap is enforced)
- Modify: `tests/unit/orchestration/` — find the test for entry processor signals

**Why B-only:** A confidence has 77% win rate; same-market-type multi-line bets compound wins (your "free para" intuition). B at 26% compounds losses. Apply guard surgically to B.

- [ ] **Step 1: Read the existing event_count check**

```bash
PYTHONIOENCODING=utf-8 grep -n "event_count\|event_count_per_event_cap" src/orchestration/_entry_processor_signals.py
```

Read 30 lines around it.

- [ ] **Step 2: Write failing test**

In a new or existing test file for entry processor signals, add:

```python
def test_b_confidence_blocks_same_market_type_per_event() -> None:
    """When a B-confidence signal arrives for an event+market_type that already
    has an open B position, the new signal is skipped (same_market_type_per_event).
    A-confidence is unaffected — multi-line same-type allowed."""
    # Build state with one B set_totals position open for event X
    # Try to add another B set_totals signal for event X — should be skipped
    # Try to add an A set_totals signal — should pass (A allowed multi-line)
    pass  # IMPLEMENT mirroring existing event_count tests
```

Implementer must wire fixtures using existing patterns.

- [ ] **Step 3: Run failing**

Expected fail because the guard doesn't exist yet.

- [ ] **Step 4: Add the guard**

In `_entry_processor_signals.py`, after the existing `event_count >= max_per_event` check, add:

```python
# B-only same-market-type guard (data-driven: B at 26% win rate compounds
# chain losses on same-type multi-line bets. A retains multi-line freedom).
if signal.confidence == "B" and market.event_id:
    same_type_count = pm.count_event_market_type(
        market.event_id, market.sports_market_type,
    )
    if same_type_count >= 1:
        detail = (
            f"event_id={market.event_id} "
            f"market_type={market.sports_market_type} "
            f"already_held_for_B={same_type_count}"
        )
        operational_writers.log_skip(
            self.deps.skipped_logger, market,
            "same_market_type_per_event_b", detail=detail,
        )
        self.deps.stock.add(market, "same_market_type_per_event_b")
        continue
```

(Verify `pm.count_event_market_type` exists. If not, add a small method on PortfolioManager that counts positions matching both event_id AND sports_market_type. Mirror `count_event`.)

- [ ] **Step 5: Add count_event_market_type to PortfolioManager (if missing)**

In `src/domain/portfolio/manager.py`, add:

```python
def count_event_market_type(self, event_id: str, market_type: str) -> int:
    """Count open positions matching both event_id and sports_market_type.

    Used by B-confidence same-market-type guard to prevent chain losses on
    correlated multi-line bets (e.g., set_totals 3.5 + 4.5 on same match).
    """
    return sum(
        1 for p in self._positions.values()
        if p.event_id == event_id
        and (p.sports_market_type or "") == market_type
    )
```

(Read existing `count_event` for the exact internal data structure name.)

- [ ] **Step 6: Run tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/orchestration/ tests/unit/domain/portfolio/ -v
```

All PASS.

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/_entry_processor_signals.py src/domain/portfolio/manager.py tests/
git commit -m "feat(entry): B-only same_market_type_per_event guard

aguilar set_totals 3.5+4.5 type chain losses: -\$31 in one match.
B confidence (26% win rate) compounds chain loss on correlated multi-line
bets. A confidence (77% win rate) retains multi-line freedom — multi-line
on A compounds wins (asymmetric upside intact).

Adds PortfolioManager.count_event_market_type + B-conf check in
entry_processor_signals before opening."
```

---

## Task 3: Disable simple stop_loss on set_handicap markets

**Files:**
- Modify: `src/config/settings.py` (add `stop_loss_exempt_market_types` field)
- Modify: `config_tennis.yaml` (add the exemption)
- Modify: `src/strategy/exit/monitor.py` (skip stop_loss check on exempt types)
- Modify: `tests/unit/strategy/exit/test_monitor.py` for exempt behavior

**Why:** shnaide-zarazua set_handicap: simple SL at -30% fired @ 0.33, market resolved at 0.9995 — bot lost \$10 on a position that should have made +\$56. Two of two set_handicap stop_loss fires in our data were premature (zakharo also). graduated_sl (smarter, elapsed-aware) stays — it had 4/5 correct.

- [ ] **Step 1: Write failing test**

In `tests/unit/strategy/exit/test_monitor.py`:

```python
def test_monitor_skips_simple_stop_loss_for_set_handicap() -> None:
    """Bimodal set_handicap markets: simple stop_loss exempt (graduated_sl still applies).

    Real case: shnaide-zarazua set_handicap, entry 0.64, current 0.32 (-50%),
    bot's old simple SL would fire, but graduated_sl decides based on elapsed.
    """
    # Build position with sports_market_type="tennis_set_handicap",
    # entry 0.64, current 0.32 (would trigger simple SL at -30%).
    # cfg with stop_loss_exempt_market_types=["tennis_set_handicap"].
    # Run evaluate; assert exit_signal is None OR reason != "stop_loss"
    # (graduated_sl may or may not fire depending on elapsed setup —
    # arrange elapsed so it doesn't, isolating the simple_sl check).
    pass  # IMPLEMENT
```

- [ ] **Step 2: Run failing**

Expected fail (no exempt logic yet, stop_loss would fire).

- [ ] **Step 3: Add exempt field to config**

`src/config/settings.py` — add to RiskConfig (or wherever stop_loss config sits):

```python
class RiskConfig(BaseModel):
    # ... existing ...
    stop_loss_exempt_market_types: List[str] = []
```

`config_tennis.yaml` under `risk:`:

```yaml
  # 2026-05-26: shnaide-zarazua bug. set_handicap is bimodal — price swings
  # between sets normally exceed -30%, triggering simple SL prematurely. Bot
  # exited a winning position (resolved 0.9995) at -\$10 stop_loss when it
  # should have won +\$56. graduated_sl (elapsed-aware) remains active.
  stop_loss_exempt_market_types:
    - tennis_set_handicap
```

- [ ] **Step 4: Skip stop_loss in monitor for exempt market types**

In `src/strategy/exit/monitor.py`, find the call to `stop_loss.check(...)` (around line 280+). Wrap with exempt check:

```python
# Bimodal markets (set_handicap) exempt from simple stop_loss — price swings
# between sets normally exceed -30%. graduated_sl continues to apply.
smt = (pos.sports_market_type or "")
if smt not in cfg.risk.stop_loss_exempt_market_types:
    exit_sl = stop_loss.check(pos)
    if exit_sl:
        return exit_sl
# else: skip simple SL entirely for this position
```

(Verify exact existing call form by reading the file.)

- [ ] **Step 5: Run tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/exit/ tests/unit/config/ -v
```

All PASS.

- [ ] **Step 6: Commit**

```bash
git add src/config/settings.py config_tennis.yaml src/strategy/exit/monitor.py tests/
git commit -m "fix(monitor): disable simple stop_loss on set_handicap (bimodal SL bug)

shnaide-zarazua case: entry 0.64, current 0.32 (-50% transient), simple SL
fired, bot exited at -\$10. Market resolved at 0.9995 — would have won +\$56.
Net catastrophic loss \$66 from one bad SL fire.

Pattern: set_handicap markets are bimodal — price swings between sets routinely
exceed -30%. Simple -30% threshold mechanically fires prematurely.
graduated_sl (elapsed+price-tier-aware) remains active as backup."
```

---

## Task 4: Drift cleanup audit

User directive: "dead code drift code vs bişey olmasın".

- [ ] **Step 1: Grep for stale exclude_combos references**

```bash
PYTHONIOENCODING=utf-8 grep -rn "atp_min_confidence\|tennis_min_confidence\|exclude_combos" src/ tests/ config_tennis.yaml
```

Expected: only the new code from Task 1. No old hardcoded exclusions left over.

- [ ] **Step 2: Grep for stale stop_loss exemption (SPEC-V history)**

SPEC-V (2026-05-23) earlier removed totals/spread stop_loss exemption from main bot. Tennis lab may have residual references.

```bash
PYTHONIOENCODING=utf-8 grep -rn "_TOTALS_KEYWORDS\|stop_loss_exempt\|bimodal.*sl\|sl.*bimodal" src/ tests/
```

Expected: only the new `stop_loss_exempt_market_types` from Task 3.

- [ ] **Step 3: Grep for same_market_type residuals**

```bash
PYTHONIOENCODING=utf-8 grep -rn "same_market_type" src/ tests/
```

Expected: only Task 2 code (`same_market_type_per_event_b` skip reason + `count_event_market_type` method).

- [ ] **Step 4: Run full unit test suite**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/ -q 2>&1 | tail -10
```

All PASS (or only pre-existing failures unrelated to this work).

- [ ] **Step 5: If drift found, fix it inline and commit**

```bash
git add <changed files>
git commit -m "refactor: drift cleanup after acute-losses-fix plan"
```

If no drift, skip the commit (no empty commits).

---

## Task 5: ARCH_GUARD repair (safety net — only if needed)

User directive: "arch guard'da bir sorun olursa en son bir task daha ekle onu da onar".

- [ ] **Step 1: Read ARCH_GUARD.md to refresh the 8 anti-patterns**

```bash
cat ARCHITECTURE_GUARD.md | head -60
```

- [ ] **Step 2: Manually scan changes from Tasks 1-3 against the 8 anti-patterns**

| Anti-pattern | Check method |
|---|---|
| 1. DRY | grep added code for duplication |
| 2. <400 satır | wc -l on each modified file |
| 3. Domain I/O | grep for requests/open/file in src/domain/ |
| 4. Katman düzeni | new code respects 5-layer (presentation→orchestration→strategy→domain→infra) |
| 5. Magic number | new thresholds all come from config |
| 6. utils/helpers/misc | no new dirs with these names |
| 7. Sessiz hata | new code raises explicit errors / logs warnings |
| 8. P(YES) anchor | no direction-adjusted prob storage |

Run:

```bash
PYTHONIOENCODING=utf-8 wc -l src/strategy/exit/monitor.py src/orchestration/_entry_processor_signals.py src/strategy/enrichment/tennis_market_enricher.py src/domain/portfolio/manager.py src/config/settings.py
```

For each file over 400 lines, decide whether the addition pushed it over (vs pre-existing).

- [ ] **Step 3: If any violation, FIX and commit**

Common likely violations:
- File grew past 400 (rare — these changes are small)
- Magic number sneaked into a check (should be all config-driven)

Fix any actual violations with minimal scope: extract helper, move to config, etc.

```bash
git commit -m "refactor: ARCH_GUARD compliance fix after acute-losses-fix plan"
```

If no violations found, this task ends with no commit (skip cleanly).

- [ ] **Step 4: Report final state**

Print summary:
- Tasks 1-3 commits
- Task 4 drift findings (if any)
- Task 5 ARCH_GUARD findings (if any)
- Full test count
- ARCH_GUARD pass/fail per anti-pattern

---

## After all tasks: reload (NO wipe)

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab"
PYTHONIOENCODING=utf-8 python scripts/reboot_tennis.py --reload
```

Dashboard separate process — kill PID on port 5051, restart `scripts/tennis_dashboard.py`.

Verify next heavy cycle:
- No new ATP_set_totals B entries
- No duplicate same_market_type B trades in same event
- set_handicap positions don't trigger simple stop_loss (skip log shows the exempt was honored)
