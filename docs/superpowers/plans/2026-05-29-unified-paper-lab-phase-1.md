# Unified Paper Lab — Phase 1: Backup + Sport Whitelist Cut

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create rollback safety net (git tag + state snapshot) and reduce `allowed_sport_tags` to basketball only. Tennis is NOT enabled yet (Phase 3). Default mode stays `dry_run`.

**Architecture:** Config-only change. No new modules, no executor changes. Scanner already enforces whitelist correctly — only the YAML list shrinks. Open positions in disabled sports continue under `exit_processor` (whitelist only filters NEW entries).

**Tech Stack:** Git tags, YAML config, pytest, existing scanner filter logic.

**Companion design doc:** `docs/superpowers/specs/2026-05-29-unified-paper-lab-design.md` §8 Phase 1.

**Prerequisite (manual before starting):**
- `git status` clean (no uncommitted changes; commit or stash anything WIP).
- `data/positions.json` open positions count = 0 (verify with `python -c "import json; d=json.load(open('data/positions.json',encoding='utf-8')); print(len(d.get('positions',{})))"`). If non-zero → STOP, wait for positions to close.
- Current branch = `master`.

**ARCH_GUARD self-check before EVERY Edit/Write step:**
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

---

### Task 1: Pre-flight verification

**Files:** none (read-only check).

- [ ] **Step 1: Verify clean working tree**

Run:
```bash
git status --porcelain
```
Expected: empty output. If non-empty → STOP, ask user to commit/stash.

- [ ] **Step 2: Verify on master branch**

Run:
```bash
git branch --show-current
```
Expected: `master`. If not → STOP, `git checkout master`.

- [ ] **Step 3: Verify no open positions**

Run:
```bash
python -c "import json; d=json.load(open('data/positions.json',encoding='utf-8')); n=len(d.get('positions',{})); print(f'open_positions={n}')"
```
Expected: `open_positions=0`. If non-zero → STOP, wait for natural close or document manual close decision.

- [ ] **Step 4: Verify pytest baseline green**

Run:
```bash
pytest -q 2>&1 | tail -5
```
Expected: all green (no failures). Record the pass count for later comparison.

---

### Task 2: Git tag for rollback

**Files:** none (git operation only).

- [ ] **Step 1: Create rollback tag on current HEAD**

Run:
```bash
git tag -a pre-unified-2026-05-29 -m "Rollback point before unified paper lab refactor (basket-only whitelist, paper realism, tennis merge). Phase 1 starts here."
```
Expected: no output, tag created.

- [ ] **Step 2: Verify tag exists and points to current HEAD**

Run:
```bash
git rev-parse pre-unified-2026-05-29 && git rev-parse HEAD
```
Expected: two identical SHA hashes.

---

### Task 3: Tag the tennis-lab branch

**Files:** none (git operation only).

- [ ] **Step 1: Verify feature/tennis-lab branch exists**

Run:
```bash
git rev-parse --verify feature/tennis-lab 2>&1
```
Expected: SHA hash. If "unknown revision" → branch missing; skip tagging (just log a note in commit message later).

- [ ] **Step 2: Create archive tag on tennis-lab tip**

Run:
```bash
git tag -a feature-tennis-lab-archived-2026-05-29 feature/tennis-lab -m "Tennis-lab branch tip archived before merge into master (unified paper lab refactor). Branch NOT deleted — kept for cherry-pick in Phase 3."
```
Expected: no output.

- [ ] **Step 3: List tags to confirm both created**

Run:
```bash
git tag -l | grep -E "(pre-unified|tennis-lab-archived)"
```
Expected: two lines with both tag names.

---

### Task 4: Snapshot data and audit logs

**Files:** Create archive directory `_archive/2026-05-29/`.

- [ ] **Step 1: Verify _archive parent does not exist yet**

Run:
```bash
ls _archive/ 2>&1 | head -5
```
Expected: "No such file or directory" OR existing other date folders. If `2026-05-29/` already exists → STOP, decide overwrite or rename.

- [ ] **Step 2: Create archive directory**

Run:
```bash
mkdir -p _archive/2026-05-29/data _archive/2026-05-29/logs
```

- [ ] **Step 3: Copy data directory state**

Run:
```bash
cp -r data/positions.json data/stock_queue.json data/blacklist.json data/circuit_breaker_state.json data/bot_status.json data/session_start.json _archive/2026-05-29/data/ 2>&1
```
Expected: each `cp` succeeds (no "No such file" for the listed files).

- [ ] **Step 4: Copy audit logs**

Run:
```bash
cp -r logs/audit _archive/2026-05-29/logs/
```
Expected: succeeds.

- [ ] **Step 5: Verify snapshot is restorable**

Run:
```bash
ls -la _archive/2026-05-29/data/ && ls _archive/2026-05-29/logs/audit/ | head -10
```
Expected: positions.json, stock_queue.json etc visible + audit files visible.

- [ ] **Step 6: Document restore command**

Write to `_archive/2026-05-29/RESTORE.md`:

```markdown
# Restore from 2026-05-29 snapshot

Rollback git:
git reset --hard pre-unified-2026-05-29

Restore data + audit:
cp -r _archive/2026-05-29/data/* data/
rm -rf logs/audit && cp -r _archive/2026-05-29/logs/audit logs/

Verify:
python -c "import json; print(json.load(open('data/positions.json',encoding='utf-8')))"
```

Run:
```bash
cat _archive/2026-05-29/RESTORE.md
```
Expected: file content shown.

---

### Task 5: Write the failing test for config whitelist

**Files:**
- Create: `tests/unit/config/test_whitelist_phase_1.py`

> **ARCH_GUARD self-check:** "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

- [ ] **Step 1: Write the failing test**

Create file `tests/unit/config/test_whitelist_phase_1.py`:

```python
"""Phase 1 verification — config.yaml allowed_sport_tags constraint.

After Phase 1, the whitelist must contain ONLY basketball sport tags
(NHL/NCAAF/CFL/UFL/MMA/UFC/Boxing/PGA/LIV/LPGA removed). Tennis
(atp/wta) is NOT added yet — that's Phase 3.
"""
from pathlib import Path

import yaml


_BASKET_ALLOWED = {"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl"}
_MUST_NOT_BE_PRESENT = {
    "nhl",
    "ncaaf", "cfl", "ufl",
    "mma", "ufc", "boxing",
    "lpga*", "liv*", "pga*",
    # Tennis NOT added in Phase 1
    "atp", "wta",
}


def _load_config_yaml() -> dict:
    cfg_path = Path("config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_phase_1_whitelist_contains_only_basketball() -> None:
    cfg = _load_config_yaml()
    tags = set(cfg["scanner"]["allowed_sport_tags"])
    assert tags == _BASKET_ALLOWED, (
        f"Phase 1: whitelist must equal basketball-only set.\n"
        f"got: {sorted(tags)}\nexpected: {sorted(_BASKET_ALLOWED)}"
    )


def test_phase_1_whitelist_excludes_removed_sports() -> None:
    cfg = _load_config_yaml()
    tags = set(cfg["scanner"]["allowed_sport_tags"])
    intersect = tags & _MUST_NOT_BE_PRESENT
    assert not intersect, f"Phase 1: these tags must be REMOVED: {sorted(intersect)}"


def test_phase_1_mode_remains_dry_run() -> None:
    """Phase 1 must NOT change mode. Mode default stays dry_run until Phase 3."""
    cfg = _load_config_yaml()
    assert cfg.get("mode", "dry_run") == "dry_run", (
        "Phase 1 must keep mode=dry_run. Mode change is Phase 3."
    )
```

- [ ] **Step 2: Run test to verify it fails (whitelist still has NHL/golf/MMA)**

Run:
```bash
pytest tests/unit/config/test_whitelist_phase_1.py -v 2>&1 | tail -20
```
Expected: `test_phase_1_whitelist_contains_only_basketball` FAILS (current whitelist has nhl, ncaaf, etc.). `test_phase_1_mode_remains_dry_run` should PASS (mode already dry_run).

---

### Task 6: Modify config.yaml — remove non-basketball sports

**Files:**
- Modify: `config.yaml:29-57` (allowed_sport_tags block)

> **ARCH_GUARD self-check:** "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

- [ ] **Step 1: Apply the edit**

In `config.yaml`, replace the entire `allowed_sport_tags:` block (currently containing basket + nhl + ncaaf + cfl + ufl + mma + ufc + boxing + golf entries) with:

```yaml
  allowed_sport_tags:
    # 2026-05-29 (unified paper lab Phase 1): Portfolio reduced to BASKETBALL ONLY.
    # Tennis (atp/wta) joins in Phase 3 after paper realism executor is built.
    # Removed sports (with rationale):
    #   - NHL: 13 trades, %0 WR, -$57 net (post-reboot bleed)
    #   - NCAAF/CFL/UFL: 0 trades historically (out-of-season / no Polymarket markets)
    #   - MMA/UFC/Boxing: 1 trade total, -$14 (insufficient sample)
    #   - PGA*/LIV*/LPGA*: 0 trades historically
    #   - Baseball: removed 2026-05-26 (-$297 over 5 weeks)
    # Basketball
    - nba
    - wnba
    - ncaab
    - wncaab
    - cbb
    - euroleague
    - nbl
```

- [ ] **Step 2: Verify YAML syntax valid**

Run:
```bash
python -c "import yaml; cfg=yaml.safe_load(open('config.yaml',encoding='utf-8')); print('tags:', cfg['scanner']['allowed_sport_tags'])"
```
Expected: prints `tags: ['nba', 'wnba', 'ncaab', 'wncaab', 'cbb', 'euroleague', 'nbl']`.

- [ ] **Step 3: Run failing test to verify now passes**

Run:
```bash
pytest tests/unit/config/test_whitelist_phase_1.py -v 2>&1 | tail -10
```
Expected: all 3 tests PASS.

- [ ] **Step 4: Run full test suite to verify nothing else broke**

Run:
```bash
pytest -q 2>&1 | tail -5
```
Expected: all green; pass count >= baseline from Task 1 step 4.

---

### Task 7: Smoke test — dry_run cycle confirms whitelist active

**Files:** none (run only).

- [ ] **Step 1: Run a single dry_run cycle**

Run:
```bash
python -m src.main --once --mode dry_run 2>&1 | tee logs/runtime/phase1_smoke.log | tail -50
```
Expected: bot starts, scanner runs once, exits. Pay attention to scanner summary line `Scanner: X raw → Y filtered → top Z`.

- [ ] **Step 2: Verify no NHL/golf/MMA in filtered output**

Run:
```bash
grep -iE "(nhl|ufc|mma|boxing|ncaaf|cfl|ufl|lpga|liv|pga)" logs/runtime/phase1_smoke.log | grep -v "skipped\|filter\|comment" | head -20
```
Expected: empty OR only context lines (not actual market matches). If a market from a disabled sport appears in `entry_processor` or `position_opened` logs → STOP, debug.

- [ ] **Step 3: Confirm basketball markets present (if any in window)**

Run:
```bash
grep -iE "(nba|wnba|ncaab|euroleague|cbb|nbl)" logs/runtime/phase1_smoke.log | head -10
```
Expected: basketball slugs may appear in scanner output. Empty also acceptable (no live games during smoke).

- [ ] **Step 4: Confirm no exceptions or crashes**

Run:
```bash
grep -iE "(error|exception|traceback)" logs/runtime/phase1_smoke.log | head -10
```
Expected: empty, or only known-benign WARNINGs (e.g. odds_api 429 backoff). No Traceback.

---

### Task 8: Commit Phase 1

- [ ] **Step 1: Stage changes**

Run:
```bash
git add config.yaml tests/unit/config/test_whitelist_phase_1.py _archive/2026-05-29/
```

- [ ] **Step 2: Verify staged contents**

Run:
```bash
git status --short && git diff --staged --stat
```
Expected: 3+ files staged (config.yaml modified, test file new, _archive new).

- [ ] **Step 3: Create commit**

Run:
```bash
git commit -m "$(cat <<'EOF'
refactor(config): Phase 1 — reduce sport whitelist to basketball only

Pre-unified-paper-lab rollback safety net:
- git tag pre-unified-2026-05-29 (current HEAD)
- git tag feature-tennis-lab-archived-2026-05-29 (tennis-lab tip)
- snapshot data + audit → _archive/2026-05-29/

Whitelist cut (config.yaml):
- KEEP: nba, wnba, ncaab, wncaab, cbb, euroleague, nbl
- REMOVE: nhl, ncaaf, cfl, ufl, mma, ufc, boxing, lpga*, liv*, pga*
  Rationale: NHL -$57 0%WR, MMA/UFC 1 trade, golf/CFB 0 trades historically.

Tennis (atp/wta) NOT added yet — Phase 3 after paper executor is built.
Mode stays dry_run — Phase 3 default change.

Verified:
- tests/unit/config/test_whitelist_phase_1.py (3 assertions green)
- pytest -q full suite green
- dry_run smoke: scanner output contains no NHL/golf/MMA markets

Rollback: git reset --hard pre-unified-2026-05-29 + cp -r _archive/2026-05-29/data/* data/

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
Expected: commit succeeds, hook tests green (if pre-commit hook runs pytest).

- [ ] **Step 4: Verify commit + final state**

Run:
```bash
git log --oneline -3 && git tag -l | grep -E "(pre-unified|tennis-lab-archived)"
```
Expected: latest commit visible + both tags listed.

---

## Phase 1 Acceptance — User checkpoint

Stop here and ask the user to verify before moving to Phase 2.

Show the user:
1. `git log --oneline -3` — last commit hash + message.
2. `python -c "import yaml; cfg=yaml.safe_load(open('config.yaml',encoding='utf-8')); print('Whitelist:', cfg['scanner']['allowed_sport_tags'])"` — confirmed basketball-only.
3. `wc -l logs/runtime/phase1_smoke.log` — smoke log length (proof the run happened).

Ask:
> "Phase 1 tamamlandı. Whitelist sadece basketbol (NBA/WNBA/NCAAB/WNCAAB/CBB/EuroLeague/NBL). Smoke testte hiç NHL/golf/MMA görünmedi. Phase 2'ye (paper realism executor) geçeyim mi?"

If user says yes → start Phase 2 plan (`2026-05-29-unified-paper-lab-phase-2.md`).
If user says no / wants changes → revert with `git reset --hard pre-unified-2026-05-29` (preserves snapshot in `_archive/`).
