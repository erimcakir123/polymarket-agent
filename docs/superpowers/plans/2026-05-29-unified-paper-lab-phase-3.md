# Unified Paper Lab — Phase 3: Tennis Merge + Bankroll Unification + Mode=Paper Default

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cherry-pick tennis-specific code (gamma series_id, surname-collision fix, Sackmann refresher) from `feature/tennis-lab` into master; add `atp`/`wta` to whitelist; add tennis-specific `exclude_combos` to config; flip mode default to `paper`; delete `tennis_main.py` and `config_tennis.yaml`; archive `_backup_tennis_lab/`; clean up `--live-lab` marker in `reboot.py`. Final unified single-bot state.

**Architecture:** Selective code migration from `feature/tennis-lab` branch. Use `git show feature/tennis-lab:<file>` to extract specific changes rather than merge (avoids dragging in tennis-paper-lab structural changes). Files migrate one at a time, each verified with tests before next.

**Tech Stack:** Git cherry-pick / git show, Python 3.12, pytest, YAML config.

**Companion design doc:** `docs/superpowers/specs/2026-05-29-unified-paper-lab-design.md` §8 Phase 3.

**Prerequisites (manual before starting):**
- Phase 2 commit merged + user-approved (tag `phase2-paper-executor-2026-05-29` exists).
- `git status` clean.
- **No open positions** (reboot=full wipe behavior; user preference).
- Sackmann cache (if exists at `data/sackmann_cache/`) — leave alone, refresher will validate.

**ARCH_GUARD self-check before EVERY Edit/Write step (mandatory):**
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

---

### Task 1: Pre-flight verification

- [ ] **Step 1: Confirm Phase 2 complete**

Run:
```bash
git tag -l | grep phase2-paper-executor
```
Expected: tag `phase2-paper-executor-2026-05-29` listed.

- [ ] **Step 2: Confirm clean tree**

Run: `git status --porcelain`
Expected: empty.

- [ ] **Step 3: Open positions check**

Run:
```bash
python -c "import json; d=json.load(open('data/positions.json',encoding='utf-8')); n=len(d.get('positions',{})); print(f'open_positions={n}')"
```
Expected: `open_positions=0`. If non-zero → STOP, user must decide (manual close or wait).

- [ ] **Step 4: Baseline pytest**

Run: `pytest -q 2>&1 | tail -3`
Expected: green. Record pass count.

---

### Task 2: Cherry-pick `gamma_client.py` series_id support

**Files:**
- Modify: `src/infrastructure/apis/gamma_client.py`
- Modify (or extend): `tests/unit/infrastructure/apis/test_gamma_client.py`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: View the tennis-lab version of gamma_client.py**

Run:
```bash
git show feature/tennis-lab:src/infrastructure/apis/gamma_client.py > /tmp/gamma_tennis.py
diff src/infrastructure/apis/gamma_client.py /tmp/gamma_tennis.py | head -100
```
Confirm the diff matches the patch (series_id support).

- [ ] **Step 2: Copy tennis-lab version into master**

Run:
```bash
git show feature/tennis-lab:src/infrastructure/apis/gamma_client.py > src/infrastructure/apis/gamma_client.py
```

- [ ] **Step 3: Copy tennis-lab tests file**

Run:
```bash
git show feature/tennis-lab:tests/unit/infrastructure/apis/test_gamma_client.py > tests/unit/infrastructure/apis/test_gamma_client.py
```

- [ ] **Step 4: Run gamma_client tests**

Run: `pytest tests/unit/infrastructure/apis/test_gamma_client.py -v 2>&1 | tail -15`
Expected: all pass (including new `test_fetch_events_uses_series_id_when_present`, `test_fetch_events_series_id_invalid_value_skipped`).

- [ ] **Step 5: Full pytest**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/apis/gamma_client.py tests/unit/infrastructure/apis/test_gamma_client.py
git commit -m "feat(gamma): series_id discovery (cherry-pick from feature/tennis-lab)

Polymarket assigns ITF tennis events to a series, not a tennis tag.
Series-based fetch is the only discovery path for ~95% of daily
tennis volume. Tag-based fetch alone misses them.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Cherry-pick `tennis_player_matcher.py` surname-collision fix

**Files:**
- Modify: `src/domain/matching/tennis_player_matcher.py`
- Modify: `tests/unit/domain/matching/test_tennis_player_matcher.py`

> **ARCH_GUARD self-check** (mandatory). Domain layer — no I/O.

- [ ] **Step 1: Copy tennis-lab versions**

Run:
```bash
git show feature/tennis-lab:src/domain/matching/tennis_player_matcher.py > src/domain/matching/tennis_player_matcher.py
git show feature/tennis-lab:tests/unit/domain/matching/test_tennis_player_matcher.py > tests/unit/domain/matching/test_tennis_player_matcher.py
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/domain/matching/test_tennis_player_matcher.py -v 2>&1 | tail -15`
Expected: all pass (including new `test_match_player_surname_not_unique_returns_none`, `test_match_player_surname_eight_collisions_returns_none`, `test_match_player_two_surname_collisions_with_compound_returns_none`).

- [ ] **Step 3: Verify no I/O imports (ARCH_GUARD Rule 2)**

Run:
```bash
grep -E "^(import|from) (requests|httpx|urllib|socket|open\(|pathlib|os\.path)" src/domain/matching/tennis_player_matcher.py
```
Expected: empty.

- [ ] **Step 4: Full pytest**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 5: Commit**

```bash
git add src/domain/matching/tennis_player_matcher.py tests/unit/domain/matching/test_tennis_player_matcher.py
git commit -m "fix(tennis): surname-collision returns None (cherry-pick from feature/tennis-lab)

Polymarket questions sometimes use surname only ('Smith vs Svajda').
With 8 ATP Smiths, fuzzy partial_ratio scores all at 100 and picks
one wrong. Must refuse to guess when surname ambiguous.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Migrate `sackmann_refresher.py` from backup

**Files:**
- Create: `src/infrastructure/data/__init__.py` (if not exists)
- Create: `src/infrastructure/data/sackmann_refresher.py` (from `_backup_tennis_lab/sackmann_refresher.py`)
- Create: `scripts/refresh_sackmann.py` (from `_backup_tennis_lab/refresh_sackmann.py`)
- Create: `tests/unit/infrastructure/data/__init__.py`
- Create: `tests/unit/infrastructure/data/test_sackmann_refresher.py` (from backup)

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Inspect backup files**

Run:
```bash
ls _backup_tennis_lab/ && wc -l _backup_tennis_lab/sackmann_refresher.py _backup_tennis_lab/refresh_sackmann.py _backup_tennis_lab/test_sackmann_refresher.py
```

- [ ] **Step 2: Create dir + __init__**

Run:
```bash
mkdir -p src/infrastructure/data tests/unit/infrastructure/data
touch src/infrastructure/data/__init__.py tests/unit/infrastructure/data/__init__.py
```

- [ ] **Step 3: Copy files**

Run:
```bash
cp _backup_tennis_lab/sackmann_refresher.py src/infrastructure/data/sackmann_refresher.py
cp _backup_tennis_lab/refresh_sackmann.py scripts/refresh_sackmann.py
cp _backup_tennis_lab/test_sackmann_refresher.py tests/unit/infrastructure/data/test_sackmann_refresher.py
```

- [ ] **Step 4: Run sackmann tests**

Run: `pytest tests/unit/infrastructure/data/test_sackmann_refresher.py -v 2>&1 | tail -15`
Expected: all pass.

- [ ] **Step 5: If tests fail because imports differ**

If `ModuleNotFoundError` or import errors → check `_backup_tennis_lab` test imports and align with master codebase paths. Adjust as needed. Re-run tests.

- [ ] **Step 6: Verify file sizes < 400**

Run: `wc -l src/infrastructure/data/sackmann_refresher.py scripts/refresh_sackmann.py`

- [ ] **Step 7: Commit**

```bash
git add src/infrastructure/data/ scripts/refresh_sackmann.py tests/unit/infrastructure/data/
git commit -m "feat(infra): sackmann_refresher migrated from tennis-lab backup

Used by main.py startup if tennis is in allowed_sport_tags (Phase 3).
Refreshes Sackmann CSV cache + rebuilds tennis_ratings.json.
Stale cache (>3 days) triggers refresh; fresh cache → skip.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Migrate `build_tennis_ratings.py` if absent

**Files:** check existence, migrate from backup if needed.

- [ ] **Step 1: Check if `scripts/build_tennis_ratings.py` exists in master**

Run: `ls scripts/build_tennis_ratings.py 2>&1`

- [ ] **Step 2: Check tennis-lab for it**

Run: `git show feature/tennis-lab:scripts/build_tennis_ratings.py 2>&1 | head -3`

- [ ] **Step 3: If missing in master AND present in tennis-lab — cherry-pick**

```bash
git show feature/tennis-lab:scripts/build_tennis_ratings.py > scripts/build_tennis_ratings.py
```

- [ ] **Step 4: Smoke test the script (read help)**

Run:
```bash
python scripts/build_tennis_ratings.py --help 2>&1 | head -10
```
Expected: usage text, no ImportError.

- [ ] **Step 5: Commit if changes**

```bash
git add scripts/build_tennis_ratings.py
git commit -m "feat(tennis): build_tennis_ratings.py from feature/tennis-lab

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Add Sackmann startup hook to `factory.py`

**Files:**
- Modify: `src/orchestration/factory.py` (build_agent function)

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Write failing test**

Create `tests/unit/orchestration/test_factory_sackmann_hook.py`:

```python
"""Phase 3: factory.build_agent invokes Sackmann refresh when tennis is whitelisted."""
from unittest.mock import patch

from src.config.settings import AppConfig


def test_sackmann_refresh_skipped_when_tennis_not_in_whitelist() -> None:
    cfg = AppConfig()
    cfg.scanner.allowed_sport_tags = ["nba", "wnba"]
    with patch("src.orchestration.factory.maybe_refresh_sackmann_on_startup") as m:
        from src.orchestration import factory
        factory._maybe_invoke_sackmann_refresh(cfg)
        m.assert_not_called()


def test_sackmann_refresh_invoked_when_tennis_in_whitelist() -> None:
    cfg = AppConfig()
    cfg.scanner.allowed_sport_tags = ["nba", "atp", "wta"]
    with patch("src.orchestration.factory.maybe_refresh_sackmann_on_startup") as m:
        from src.orchestration import factory
        factory._maybe_invoke_sackmann_refresh(cfg)
        m.assert_called_once()
```

- [ ] **Step 2: Run, verify fails**

Run: `pytest tests/unit/orchestration/test_factory_sackmann_hook.py -v 2>&1 | tail -10`

- [ ] **Step 3: Add hook function to factory.py**

At top of `src/orchestration/factory.py`, add import (if not already):

```python
from pathlib import Path

from src.infrastructure.data.sackmann_refresher import refresh_if_stale, is_cache_stale
```

Add new function near `_build_executor` (around line 282):

```python
def maybe_refresh_sackmann_on_startup(cache_dir: Path) -> None:
    """Refresh Sackmann CSV + rebuild ratings if cache stale."""
    if not is_cache_stale(cache_dir):
        logger.info("Sackmann cache fresh — skipping startup refresh")
        return
    logger.info("Sackmann cache stale — refreshing before agent start")
    refreshed = refresh_if_stale(cache_dir)
    if not refreshed:
        logger.warning("Sackmann refresh attempted but no files downloaded")
        return
    logger.info("Rebuilding tennis_ratings.json from refreshed CSVs...")
    from scripts.build_tennis_ratings import main as rebuild_main
    rebuild_main()
    logger.info("Startup Sackmann refresh + rebuild complete")


def _maybe_invoke_sackmann_refresh(cfg: AppConfig) -> None:
    """Tennis aktif iken Sackmann refresh hook çağır."""
    tags_lc = {t.lower() for t in (cfg.scanner.allowed_sport_tags or [])}
    if not ({"atp", "wta"} & tags_lc):
        return
    maybe_refresh_sackmann_on_startup(Path("data/sackmann_cache"))
```

In `build_agent`, at the top (right after `cfg = state.config`), add:

```python
    _maybe_invoke_sackmann_refresh(cfg)
```

- [ ] **Step 4: Run new tests, verify pass**

Run: `pytest tests/unit/orchestration/test_factory_sackmann_hook.py -v 2>&1 | tail -10`

- [ ] **Step 5: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/factory.py tests/unit/orchestration/test_factory_sackmann_hook.py
git commit -m "feat(factory): Sackmann startup hook gated by tennis whitelist

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Manual Sackmann cache pre-warm (avoid startup stall)

**Files:** none (run only).

- [ ] **Step 1: Pre-warm cache before activating tennis**

Run:
```bash
python scripts/refresh_sackmann.py 2>&1 | tail -10
```
Expected: download proceeds (~1-2 min first time). Subsequent runs skip if cache fresh.

- [ ] **Step 2: Verify cache present**

Run:
```bash
ls data/sackmann_cache/ 2>&1 | head -5
```
Expected: CSV files visible.

- [ ] **Step 3: Build ratings.json**

Run:
```bash
python scripts/build_tennis_ratings.py 2>&1 | tail -5
```
Expected: `tennis_ratings.json` created in `data/`.

- [ ] **Step 4: Verify ratings file**

Run:
```bash
ls -la data/tennis_ratings.json 2>&1
```

---

### Task 8: Update `config.yaml` — add tennis, exclude_combos, mode=paper

**Files:**
- Modify: `config.yaml`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Write failing test**

Create `tests/unit/config/test_phase_3_config.py`:

```python
"""Phase 3: config.yaml final state — tennis active, exclude_combos, paper default."""
import yaml


def _cfg() -> dict:
    return yaml.safe_load(open("config.yaml", encoding="utf-8")) or {}


def test_mode_is_paper() -> None:
    assert _cfg().get("mode") == "paper"


def test_whitelist_contains_basket_and_tennis() -> None:
    tags = set(_cfg()["scanner"]["allowed_sport_tags"])
    expected = {"nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl", "atp", "wta"}
    assert tags == expected


def test_exclude_combos_contains_tennis_set_totals() -> None:
    combos = _cfg()["edge"]["exclude_combos"]
    tour_market = {(c["tour"], c["market_type"]) for c in combos}
    assert ("atp", "tennis_set_totals") in tour_market
    assert ("wta", "tennis_set_totals") in tour_market


def test_exclude_combos_contains_tennis_first_set_winner() -> None:
    combos = _cfg()["edge"]["exclude_combos"]
    tour_market = {(c["tour"], c["market_type"]) for c in combos}
    assert ("atp", "tennis_first_set_winner") in tour_market
    assert ("wta", "tennis_first_set_winner") in tour_market
```

- [ ] **Step 2: Run, verify fails (mode is dry_run, no tennis tags, no exclude_combos)**

Run: `pytest tests/unit/config/test_phase_3_config.py -v 2>&1 | tail -15`

- [ ] **Step 3: Edit config.yaml — `mode:` line at top**

Find first line `mode: dry_run` and change to:

```yaml
mode: paper
```

- [ ] **Step 4: Add tennis tags to `allowed_sport_tags`**

After the `nbl` line in the whitelist block, add:

```yaml
    # Tennis (Phase 3 — joins basketball as portfolio)
    - atp
    - wta
```

- [ ] **Step 5: Add `exclude_combos` to `edge:` block**

Replace the `edge:` block (existing has `min_edge` and `confidence_multipliers`) with:

```yaml
edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 1.00
    B: 1.00
  # 2026-05-29 (Phase 3): tennis paper lab analysis (97 trades post-spike-removal):
  #   tennis_set_totals (-$63 net), tennis_first_set_winner (-$162 net)
  #   Sackmann model accuracy 16%/56% vs market 72%/69% → model not trusted.
  # tennis_set_handicap (+$2), tennis_match_totals (+$117), moneyline kept open.
  exclude_combos:
    - {tour: atp, market_type: tennis_set_totals, confidence: A}
    - {tour: atp, market_type: tennis_set_totals, confidence: B}
    - {tour: wta, market_type: tennis_set_totals, confidence: A}
    - {tour: wta, market_type: tennis_set_totals, confidence: B}
    - {tour: atp, market_type: tennis_first_set_winner, confidence: A}
    - {tour: atp, market_type: tennis_first_set_winner, confidence: B}
    - {tour: wta, market_type: tennis_first_set_winner, confidence: A}
    - {tour: wta, market_type: tennis_first_set_winner, confidence: B}
```

- [ ] **Step 6: Run tests, verify pass**

Run: `pytest tests/unit/config/test_phase_3_config.py -v 2>&1 | tail -10`
Expected: 4 PASS.

- [ ] **Step 7: Ensure EdgeConfig in settings.py accepts exclude_combos**

Check `src/config/settings.py` `EdgeConfig`:

```bash
grep -A5 "class EdgeConfig" src/config/settings.py
```

If `exclude_combos` field is missing → add it:

```python
class EdgeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_edge: float = 0.06
    confidence_multipliers: dict = {"A": 1.00, "B": 1.00}
    exclude_combos: list[dict] = Field(default_factory=list)
```

Then verify config loads:

```bash
python -c "from src.config.settings import load_config; cfg=load_config(); print('combos:', len(cfg.edge.exclude_combos))"
```
Expected: `combos: 8`.

- [ ] **Step 8: Full pytest green**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 9: Commit**

```bash
git add config.yaml src/config/settings.py tests/unit/config/test_phase_3_config.py
git commit -m "feat(config): Phase 3 — tennis active, exclude_combos, mode=paper

allowed_sport_tags now: nba, wnba, ncaab, wncaab, cbb, euroleague, nbl, atp, wta.
exclude_combos: tennis_set_totals + tennis_first_set_winner (negative EV).
mode: paper (default flipped from dry_run).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Clean up `reboot.py` --live-lab marker

**Files:**
- Modify: `scripts/reboot.py`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Inspect current marker**

Run:
```bash
grep -n "live-lab\|_BOT_CMDLINE_MARKER\|_DASHBOARD_CMDLINE_MARKER" scripts/reboot.py
```

- [ ] **Step 2: Replace `--live-lab` markers**

Edit `scripts/reboot.py`:

Change `_BOT_CMDLINE_MARKER = "--live-lab"` to:
```python
_BOT_CMDLINE_MARKER = "src.main"  # unified bot entry
```

Change `_DASHBOARD_CMDLINE_MARKER = "--live-lab"` to:
```python
_DASHBOARD_CMDLINE_MARKER = "src.presentation.dashboard"
```

Remove any `"--live-lab"` arg added to `start_bot` / `start_dashboard` cmd lists.

- [ ] **Step 3: Smoke — reload (does NOT kill anything if no bot running)**

Run:
```bash
python scripts/reboot.py reload --dry 2>&1 | head -20
```
(If `--dry` flag not supported, skip and rely on Task 12 smoke.)

- [ ] **Step 4: Full pytest**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 5: Commit**

```bash
git add scripts/reboot.py
git commit -m "chore(reboot): unified bot markers (--live-lab obsolete after merge)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Delete `scripts/tennis_main.py` and `config_tennis.yaml`

**Files:**
- Delete: `scripts/tennis_main.py` (if exists)
- Delete: `config_tennis.yaml` (if exists)

- [ ] **Step 1: Check existence**

Run:
```bash
ls scripts/tennis_main.py config_tennis.yaml 2>&1
```

- [ ] **Step 2: Delete if present**

Run:
```bash
[ -f scripts/tennis_main.py ] && git rm scripts/tennis_main.py
[ -f config_tennis.yaml ] && git rm config_tennis.yaml
```

- [ ] **Step 3: Verify nothing references them**

Run:
```bash
grep -rn "tennis_main\|config_tennis" src/ tests/ scripts/ 2>&1 | head -10
```
Expected: empty or only historical references in docs/comments.

- [ ] **Step 4: Full pytest**

Run: `pytest -q 2>&1 | tail -3`

- [ ] **Step 5: Commit**

```bash
git commit -m "chore: remove tennis_main.py + config_tennis.yaml (unified into main)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Archive `_backup_tennis_lab/`

- [ ] **Step 1: Move backup folder**

Run:
```bash
mkdir -p _archive/2026-05-29/
mv _backup_tennis_lab/ _archive/2026-05-29/tennis-lab-backup/
```

- [ ] **Step 2: Verify move**

Run:
```bash
ls _archive/2026-05-29/tennis-lab-backup/ | head -5 && ls _backup_tennis_lab/ 2>&1
```
Expected: files present in archive; `_backup_tennis_lab/` "No such file".

- [ ] **Step 3: Commit**

```bash
git add _archive/2026-05-29/tennis-lab-backup/
git commit -m "chore: archive _backup_tennis_lab → _archive/2026-05-29/

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Phase 3 smoke test — paper mode + basketball + tennis E2E

- [ ] **Step 1: Pre-flight clean state**

Run:
```bash
rm -f logs/audit/paper_executions.jsonl logs/runtime/phase3_smoke.log
```

- [ ] **Step 2: Run paper mode for one cycle**

Run:
```bash
python -m src.main --once --mode paper 2>&1 | tee logs/runtime/phase3_smoke.log | tail -100
```
Expected: bot starts, mode=paper, Sackmann refresh skipped (cache fresh from Task 7), scanner runs, exits cleanly.

- [ ] **Step 3: Verify mode is paper**

Run:
```bash
grep -iE "mode.*paper\|paper.*mode" logs/runtime/phase3_smoke.log | head -5
```

- [ ] **Step 4: Verify Sackmann hook ran (or was skipped because fresh)**

Run:
```bash
grep -iE "sackmann" logs/runtime/phase3_smoke.log | head -5
```
Expected: at least one log line referencing Sackmann (skip or refresh).

- [ ] **Step 5: Verify tennis markets discovered**

Run:
```bash
grep -iE "atp|wta|tennis" logs/runtime/phase3_smoke.log | head -10
```
Expected: tennis market references in scanner output (if tennis matches in window).

- [ ] **Step 6: Verify gamma series_id query**

Run:
```bash
grep -iE "series_id" logs/runtime/phase3_smoke.log | head -5
```
Expected: at least one series_id query (tennis ITF discovery).

- [ ] **Step 7: Verify no NHL/golf/MMA/etc**

Run:
```bash
grep -iE "(nhl|ufc|mma|boxing|ncaaf|cfl|ufl|lpga|liv|pga)" logs/runtime/phase3_smoke.log | grep -v "skipped\|filter\|comment\|removed" | head -5
```
Expected: empty.

- [ ] **Step 8: Verify py-clob-client place_order NOT called**

Run:
```bash
grep -iE "place_order|live order placed" logs/runtime/phase3_smoke.log
```
Expected: empty.

- [ ] **Step 9: Verify paper_executions.jsonl (if any trades evaluated)**

Run:
```bash
ls -la logs/audit/paper_executions.jsonl 2>&1
wc -l logs/audit/paper_executions.jsonl 2>&1
```
If file exists with N>0 lines, inspect first record:
```bash
head -1 logs/audit/paper_executions.jsonl | python -m json.tool
```

- [ ] **Step 10: Full pytest**

Run: `pytest -q 2>&1 | tail -3`

---

### Task 13: Update DECISIONS.md

**Files:**
- Modify: `DECISIONS.md`

> **ARCH_GUARD self-check** (mandatory).

- [ ] **Step 1: Append SPEC log entry**

In `DECISIONS.md` §B (chronological SPEC log), add new entry:

```markdown
## SPEC-UNIFIED-PAPER-LAB (2026-05-29)

**Karar:** Tek bot, tek bankroll, sadece basket + tennis, mode=paper default.

**Sebep:** Tennis lab + main bot ayrı duruyordu; iki process + iki config + iki dashboard yormakta. Diğer sporlar (NHL %0 WR, NCAAF/CFL/UFL/golf 0 trade) portföyde anlam taşımıyor. Gerçek paraya geçiş öncesi hiper gerçekçi tek paper bot.

**Değişiklikler:**
- allowed_sport_tags: nba, wnba, ncaab, wncaab, cbb, euroleague, nbl, atp, wta (9 entry).
- mode default: dry_run → paper.
- Paper executor: gerçek Polymarket orderbook + FOK/GTC strategy parity + 1¢ tick + $1 min order + maker/taker fee + Polygon gas.
- Tennis: Sackmann startup hook, gamma series_id desteği, surname-collision fix.
- exclude_combos: tennis_set_totals + tennis_first_set_winner (paper lab negative-EV kanıtı).
- Force-close paper modda zero-realize YAPMAZ — pozisyon stuck → dashboard alarm.
- Silinenler: scripts/tennis_main.py, config_tennis.yaml. Arşiv: _archive/2026-05-29/.
- Rollback: git tag pre-unified-2026-05-29.

**Etki:** Tek doğruluk kaynağı (master), gerçek parayla başlamaya hazır altyapı.
```

- [ ] **Step 2: Update §A CURRENT STATE if mode/whitelist sections exist**

Search for "allowed_sport_tags" or "mode" in §A:
```bash
grep -n "allowed_sport_tags\|mode:" DECISIONS.md | head -10
```
Update those references to reflect Phase 3 state.

- [ ] **Step 3: Commit**

```bash
git add DECISIONS.md
git commit -m "docs(decisions): SPEC-UNIFIED-PAPER-LAB log entry + §A updates

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Phase 3 final tag + summary

- [ ] **Step 1: Final tag**

Run:
```bash
git tag -a phase3-unified-paper-2026-05-29 -m "Phase 3 complete: tennis merged, bankroll unified, mode=paper default. Single-bot unified state. Ready for paper-run observation phase."
```

- [ ] **Step 2: Final log review**

Run:
```bash
git log --oneline pre-unified-2026-05-29..HEAD
git tag -l | grep -E "(pre-unified|phase[123])"
```
Expected: ~20 commits across Phases 1-3 + 4 tags (pre-unified, phase2, phase3, tennis-lab-archived).

---

## Phase 3 Acceptance — Final user checkpoint

Show the user:
1. `git log --oneline pre-unified-2026-05-29..HEAD` — full refactor commit list.
2. `pytest -q | tail -3` — all green.
3. `python -c "import yaml; c=yaml.safe_load(open('config.yaml',encoding='utf-8')); print('mode:', c.get('mode')); print('tags:', c['scanner']['allowed_sport_tags']); print('exclude_combos:', len(c['edge']['exclude_combos']))"` → mode=paper, 9 tags, 8 combos.
4. Smoke log location: `logs/runtime/phase3_smoke.log`.
5. Open paper executions: `wc -l logs/audit/paper_executions.jsonl` (if any).

Ask:
> "Phase 3 tamamlandı. Tek bot, tek bankroll, basket + tennis, paper mode default. Hiper gerçekçi fill (FOK/GTC + 1¢ tick + fee + gas). Şimdi 3-7 günlük paper gözlem fazına geçilebilir. Bot'u başlatayım mı (python -m src.main --run)?"

Rollback options if needed:
- Roll back Phase 3 only: `git reset --hard phase2-paper-executor-2026-05-29`
- Roll back ALL: `git reset --hard pre-unified-2026-05-29` + restore from `_archive/2026-05-29/`
