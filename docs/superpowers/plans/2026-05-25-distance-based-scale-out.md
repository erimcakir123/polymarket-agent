# Distance-Based Scale-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Tasks use checkbox (`- [ ]`) syntax.

**Goal:** Replace profit-percentage scale-out (broken EV — locks $1-2 per trade) with distance-to-resolution scale-out (Model D, simulated +$26 better across 10 edge cases). Apply identical change to BOTH tennis-lab and main bot (Polymarket Agent 2.0).

**Architecture:**
- `ScaleOutConfig` gains `mode` field; threshold semantic depends on mode: `profit` (current, deprecated) vs `distance` (new default).
- `check_scale_out` signature changes: takes `entry_price` + `current_price` + tiers instead of `unrealized_pnl_pct`.
- Distance formula: `progress = (current_price - entry_price) / (1.0 - entry_price)`. Tier fires when `progress >= threshold`.
- Caller (`monitor.py`) passes raw prices instead of pre-computed pnl_pct.
- Tier defaults: `[(0.40, 0.40), (0.70, 0.50)]` — Tier 1 at 40% of distance to victory, sell 40%; Tier 2 at 70% of distance, sell 50% of remaining.

**Drift policy:** Profit-based path is REMOVED entirely. No `mode=profit` fallback retained. Constants `TIER1_TRIGGER_PNL` / `TIER2_TRIGGER_PNL` deleted. Tests rewritten with distance-based assertions. User directive: "dead code drift code vs bişey olmasın".

**Apply to BOTH repos (identical changes):**
- Tennis lab: `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab\`
- Main bot:   `c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\Polymarket Agent 2.0\`

Per ARCH_GUARD self-check before every Edit/Write.

---

## Task 1: Update ScaleOutConfig schema in both repos

**Files:**
- Modify (both): `src/config/settings.py` (ScaleOutTier + ScaleOutConfig classes, ~line 116-128)

- [ ] **Step 1: Write failing tests for new tier defaults**

In `tests/unit/config/test_settings.py` (or wherever ScaleOutConfig is tested), add per-repo:

```python
def test_scale_out_default_tiers_are_distance_based() -> None:
    from src.config.settings import ScaleOutConfig
    cfg = ScaleOutConfig()
    assert len(cfg.tiers) == 2
    assert cfg.tiers[0].threshold == 0.40
    assert cfg.tiers[0].sell_pct == 0.40
    assert cfg.tiers[1].threshold == 0.70
    assert cfg.tiers[1].sell_pct == 0.50
```

- [ ] **Step 2: Run failing**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/config/test_settings.py -v
```

Expected: fails on the new asserts (defaults still 0.25/0.40, 0.50/0.50).

- [ ] **Step 3: Update ScaleOutConfig defaults**

In `src/config/settings.py`, modify:

```python
class ScaleOutTier(BaseModel):
    """Scale-out tier: at threshold (distance-to-resolution), sell sell_pct of remaining.

    threshold: 0.40 = price moved 40% of the way from entry toward $1.00 resolution.
               Formula: progress = (current - entry) / (1.0 - entry); fires when progress >= threshold.
    """
    threshold: float
    sell_pct: float


class ScaleOutConfig(BaseModel):
    enabled: bool = True
    tiers: List[ScaleOutTier] = [
        ScaleOutTier(threshold=0.40, sell_pct=0.40),
        ScaleOutTier(threshold=0.70, sell_pct=0.50),
    ]
```

(Note: NO `mode` field added. The semantic is hardcoded distance-based since profit-based is removed entirely.)

- [ ] **Step 4: Tests pass**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/config/ -v
```

- [ ] **Step 5: Commit (run separately in each repo)**

```bash
git add src/config/settings.py tests/unit/config/test_settings.py
git commit -m "feat(scale-out): distance-based tier defaults (0.40/0.40, 0.70/0.50)"
```

---

## Task 2: Rewrite check_scale_out for distance mode

**Files:**
- Modify (both): `src/strategy/exit/scale_out.py` (full file rewrite — ~50 lines)
- Modify (both): `tests/unit/strategy/exit/test_scale_out.py`

- [ ] **Step 1: Write failing test for new signature + distance logic**

In `tests/unit/strategy/exit/test_scale_out.py`, replace existing tests with:

```python
"""Distance-based scale-out: tier fires when (current-entry)/(1-entry) >= threshold."""
from src.strategy.exit.scale_out import check_scale_out
from src.config.settings import ScaleOutTier


def _tiers() -> list[ScaleOutTier]:
    return [
        ScaleOutTier(threshold=0.40, sell_pct=0.40),
        ScaleOutTier(threshold=0.70, sell_pct=0.50),
    ]


def test_tier1_fires_when_progress_hits_40pct() -> None:
    # entry=0.20, current=0.52 -> progress = (0.52-0.20)/(1-0.20) = 0.40 exact
    d = check_scale_out(scale_out_tier=0, entry_price=0.20, current_price=0.52, tiers=_tiers())
    assert d is not None
    assert d.tier == 1
    assert d.sell_pct == 0.40


def test_tier1_does_not_fire_below_threshold() -> None:
    # entry=0.20, current=0.50 -> progress = 0.375, below 0.40
    d = check_scale_out(scale_out_tier=0, entry_price=0.20, current_price=0.50, tiers=_tiers())
    assert d is None


def test_tier2_fires_when_progress_hits_70pct() -> None:
    # entry=0.20, current=0.76 -> progress = (0.76-0.20)/0.80 = 0.70
    d = check_scale_out(scale_out_tier=1, entry_price=0.20, current_price=0.76, tiers=_tiers())
    assert d is not None
    assert d.tier == 2
    assert d.sell_pct == 0.50


def test_tier2_does_not_fire_when_only_tier1_passed() -> None:
    # progress = 0.50 > tier1 but tier1 already fired (state=1), tier2 needs 0.70
    d = check_scale_out(scale_out_tier=1, entry_price=0.20, current_price=0.60, tiers=_tiers())
    assert d is None


def test_no_decision_when_all_tiers_fired() -> None:
    d = check_scale_out(scale_out_tier=2, entry_price=0.20, current_price=0.95, tiers=_tiers())
    assert d is None


def test_high_entry_tier1_fires_at_appropriate_price() -> None:
    # entry=0.80, threshold 0.40 -> trigger price = 0.80 + 0.20*0.40 = 0.88
    d = check_scale_out(scale_out_tier=0, entry_price=0.80, current_price=0.88, tiers=_tiers())
    assert d is not None
    assert d.tier == 1


def test_low_entry_tier1_fires_at_appropriate_price() -> None:
    # entry=0.19, threshold 0.40 -> trigger price = 0.19 + 0.81*0.40 = 0.514
    d = check_scale_out(scale_out_tier=0, entry_price=0.19, current_price=0.515, tiers=_tiers())
    assert d is not None
    assert d.tier == 1


def test_zero_distance_edge_case_entry_above_one() -> None:
    # Defensive: if entry >= 1.0 (shouldn't happen, but guard divide-by-zero)
    d = check_scale_out(scale_out_tier=0, entry_price=1.0, current_price=1.0, tiers=_tiers())
    assert d is None
```

DELETE all old tests in this file that used `unrealized_pnl_pct=...`. They are obsolete (drift).

- [ ] **Step 2: Run failing**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/exit/test_scale_out.py -v
```

Expected: fails with `TypeError: check_scale_out() got an unexpected keyword argument 'entry_price'` (old signature).

- [ ] **Step 3: Rewrite scale_out.py**

Open `src/strategy/exit/scale_out.py` and read the full file. Then REPLACE the module with:

```python
"""Distance-based partial profit-taking (scale-out).

Tier fires when price has covered `threshold` fraction of the distance from
entry to $1.00 resolution. Formula:

    progress = (current_price - entry_price) / (1.0 - entry_price)

This is scale-invariant across entry prices: a 19¢ entry and a 50¢ entry
both fire their first tier at ~40% of their respective journeys, locking
substantial $ each time (unlike profit-percentage thresholds which fire
~5¢ above a 19¢ entry and never above an 80¢ entry).

Spec: docs/superpowers/plans/2026-05-25-distance-based-scale-out.md
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import ScaleOutTier


@dataclass(frozen=True)
class ScaleOutDecision:
    tier: int           # 1-indexed: 1 = first tier fired, 2 = second, etc.
    sell_pct: float     # of remaining shares to sell


def check_scale_out(
    *,
    scale_out_tier: int,
    entry_price: float,
    current_price: float,
    tiers: list[ScaleOutTier],
) -> ScaleOutDecision | None:
    """Return the next scale-out decision, or None if no tier fires.

    scale_out_tier: number of tiers already fired (0 = none, 1 = tier1 fired, etc.)
    entry_price:   original fill price (0 < entry < 1)
    current_price: latest market price
    tiers:         ordered list of ScaleOutTier (config.scale_out.tiers)
    """
    distance_to_resolution = 1.0 - entry_price
    if distance_to_resolution <= 0.0:
        return None  # Pathological: entry at or above $1 — no upside

    progress = (current_price - entry_price) / distance_to_resolution

    next_tier_idx = scale_out_tier  # already-fired count == 0-based index of next tier
    if next_tier_idx >= len(tiers):
        return None

    tier_cfg = tiers[next_tier_idx]
    if progress >= tier_cfg.threshold:
        return ScaleOutDecision(
            tier=next_tier_idx + 1,
            sell_pct=tier_cfg.sell_pct,
        )
    return None
```

Note: signature uses keyword-only args (`*,`) to prevent positional confusion across the 4 numeric/list params.

- [ ] **Step 4: Run tests pass**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/exit/test_scale_out.py -v
```

All 8 new tests pass.

- [ ] **Step 5: Verify no other code references removed constants**

```bash
PYTHONIOENCODING=utf-8 grep -rn "TIER1_TRIGGER_PNL\|TIER2_TRIGGER_PNL\|unrealized_pnl_pct.*scale" src/ tests/
```

Expected: zero hits in src/, zero hits in tests/ for the removed constants. Any remaining hit must be cleaned (drift).

- [ ] **Step 6: Commit (per repo)**

```bash
git add src/strategy/exit/scale_out.py tests/unit/strategy/exit/test_scale_out.py
git commit -m "feat(scale-out): replace profit-based logic with distance-based (Model D)"
```

---

## Task 3: Wire monitor.py to pass entry/current prices

**Files:**
- Modify (both): `src/strategy/exit/monitor.py` (the line that calls `check_scale_out`)
- Modify (both): `tests/unit/orchestration/test_agent_scale_out_log.py` (if test mocks the call)

- [ ] **Step 1: Locate the caller**

```bash
PYTHONIOENCODING=utf-8 grep -n "check_scale_out\|scale_out.check" src/strategy/exit/monitor.py
```

Per survey: tennis-lab around line 244-256, main bot around 213-225. Read the surrounding context.

- [ ] **Step 2: Update the call site**

Replace the call from:

```python
decision = check_scale_out(pos.scale_out_tier, pos.unrealized_pnl_pct)
```

(approximate — verify exact form by reading the line) to:

```python
decision = check_scale_out(
    scale_out_tier=pos.scale_out_tier,
    entry_price=pos.entry_price,
    current_price=pos.current_price,
    tiers=cfg.scale_out.tiers,
)
```

Ensure `cfg` (or whatever the config handle is) is in scope. If not, plumb it from the function args.

- [ ] **Step 3: Run monitor tests**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/strategy/exit/ tests/unit/orchestration/test_agent_scale_out_log.py -v
```

Fix any failing tests by updating mock setups (most likely: tests inject `cfg` or call check_scale_out directly with new kwargs).

- [ ] **Step 4: Full unit suite green**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/unit/ -q 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/exit/monitor.py tests/
git commit -m "feat(monitor): pass entry/current prices to distance-based scale-out"
```

---

## Task 4: Update config YAML defaults in both repos

**Files:**
- Modify: tennis-lab `config_tennis.yaml`
- Modify: main bot `config.yaml`

- [ ] **Step 1: Locate scale_out block**

```bash
PYTHONIOENCODING=utf-8 grep -n "scale_out\|threshold" config_tennis.yaml config.yaml
```

- [ ] **Step 2: Update tier values**

In each yaml, change `scale_out.tiers` to:

```yaml
scale_out:
  enabled: true
  # threshold = distance to resolution (1.0 - entry). Tier fires when
  # (current - entry) / (1 - entry) >= threshold. Scale-invariant across
  # entry prices — fires at meaningful $ locks regardless of entry.
  # Replaces profit-percentage (broken EV: locked $1-2 per trade).
  tiers:
    - threshold: 0.40   # 40% of way from entry to $1 → sell 40%
      sell_pct: 0.40
    - threshold: 0.70   # 70% of way → sell 50% of remaining
      sell_pct: 0.50
```

- [ ] **Step 3: Verify config loads**

```bash
PYTHONIOENCODING=utf-8 python -c "
from src.config.settings import load_config
from pathlib import Path
cfg = load_config(Path('config_tennis.yaml'))  # or 'config.yaml' for main bot
print('tiers:', [(t.threshold, t.sell_pct) for t in cfg.scale_out.tiers])
assert cfg.scale_out.tiers[0].threshold == 0.40
assert cfg.scale_out.tiers[1].threshold == 0.70
print('OK')
"
```

- [ ] **Step 4: Commit (per repo)**

```bash
git add config_tennis.yaml   # or config.yaml
git commit -m "tweak(config): scale_out tiers to distance-based 0.40/0.70"
```

---

## Task 5: Full test suite + reload (both repos)

- [ ] **Step 1: Run all tests in each repo**

```bash
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all PASS in both repos.

- [ ] **Step 2: Reload tennis bot (NOT wipe — state preserved)**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\tennis-lab"
PYTHONIOENCODING=utf-8 python scripts/reboot_tennis.py --reload
```

- [ ] **Step 3: Restart tennis dashboard separately (Python process, not bot)**

The dashboard is a separate process; reboot_tennis.py --reload does NOT restart it. Kill PID owning port 5051 and restart `scripts/tennis_dashboard.py`. Find PID via netstat / Get-NetTCPConnection -LocalPort 5051.

- [ ] **Step 4: Reload main bot (NOT wipe)**

```bash
cd "c:\Users\erimc\OneDrive\Desktop\CLAUDE PROJELER\Polymarket Agent 2.0"
PYTHONIOENCODING=utf-8 python scripts/reboot.py reload
```

- [ ] **Step 5: Verify next cycle uses new scale-out**

For tennis lab — wait for first heavy cycle log, then check whether any positions had partial exits with the new thresholds. Sample 1-2 open positions and confirm their `entry_price` + `current_price` would (or would not) trigger tier 1 by hand calc.

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
p = json.load(open('data/positions.json', encoding='utf-8'))
pos = list(p.get('positions', {}).values())[:3]
for pp in pos:
    e = pp.get('entry_price', 0)
    c = pp.get('current_price', 0)
    prog = (c - e) / (1.0 - e) if e < 1.0 else 0
    print(f\"{pp.get('slug','')[:50]} entry={e} cur={c} progress={prog:.2%} tier1={prog>=0.40} tier2={prog>=0.70}\")
"
```

---

## Drift Audit (run after Task 5 in BOTH repos)

User directive: "dead code drift code vs bişey olmasın".

```bash
# 1) No profit-based constants
PYTHONIOENCODING=utf-8 grep -rn "TIER1_TRIGGER_PNL\|TIER2_TRIGGER_PNL" src/ tests/

# 2) No old check_scale_out callers using unrealized_pnl_pct
PYTHONIOENCODING=utf-8 grep -rn "check_scale_out.*unrealized_pnl_pct" src/ tests/

# 3) No stale comments mentioning 25%/50% profit thresholds
PYTHONIOENCODING=utf-8 grep -rn "25%.*scale\|50%.*scale\|profit.*scale-out\|scale-out.*profit" src/ docs/superpowers/ config_tennis.yaml config.yaml 2>/dev/null
```

All three should return ZERO hits in src/ + tests/ + active config. Historical plans in `docs/superpowers/plans/*` are EXEMPT — leave them.

If any drift found: clean inline, re-run audit, then commit (`refactor: drift cleanup`).
