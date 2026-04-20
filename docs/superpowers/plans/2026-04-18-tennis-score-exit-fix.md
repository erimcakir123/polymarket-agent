# Tennis Score Exit Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix yanlış ESPN maç eşleşmesi bug'ı + serve-for-match erken çıkış kuralı ekle + hayalet trade'leri temizle.

**Architecture:** 3 bağımsız fix: (A) `_find_espn_match` fallback koşulu kısıtla, (B) `tennis_exit.check()` + `sport_rules.py`'ye SFM kuralı ekle, (C) `trade_history.jsonl` temizliği + TDD.md güncelleme.

**Tech Stack:** Python 3.12, pytest, JSONL

**Spec:** `docs/superpowers/specs/2026-04-18-tennis-score-exit-fix-design.md`

---

### Task 1: Fix A — `_find_espn_match` Yanlış Eşleşme

**Files:**
- Modify: `src/orchestration/score_enricher.py:85`
- Modify: `tests/unit/orchestration/test_score_enricher.py` (import + 2 test)

- [ ] **Step 1: Write failing test — two-team position must NOT match single-player ESPN entry**

Add to `tests/unit/orchestration/test_score_enricher.py`:

```python
from src.orchestration.score_enricher import (
    ScoreEnricher,
    _build_score_info,
    _find_espn_match,
    _find_match,
    _is_within_match_window,
    _team_match,
)
```

Then add test:

```python
# ── _find_espn_match ──

def test_find_espn_match_skips_wrong_match_same_player() -> None:
    """Two-team position must not match ESPN entry with only one matching player."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    old_match = ESPNMatchScore(
        event_id="old", home_name="Cameron Norrie", away_name="Rafael Jodar",
        home_score=0, away_score=2, period="Final", is_completed=True,
        is_live=False, last_updated="", linescores=[[3, 6], [3, 6]],
    )
    assert _find_espn_match(pos, [old_match]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/orchestration/test_score_enricher.py::test_find_espn_match_skips_wrong_match_same_player -v`

Expected: FAIL — current code returns the old match via `(home_a or away_a)` fallback.

- [ ] **Step 3: Fix the fallback condition**

In `src/orchestration/score_enricher.py` line 85, change:

```python
# OLD:
        if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):
# NEW:
        if (home_a and away_b) or (home_b and away_a) or (not team_b and (home_a or away_a)):
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/orchestration/test_score_enricher.py::test_find_espn_match_skips_wrong_match_same_player -v`

Expected: PASS

- [ ] **Step 5: Write test — correct two-team match still works**

Add to `tests/unit/orchestration/test_score_enricher.py`:

```python
def test_find_espn_match_correct_two_team() -> None:
    """Two-team position matches when both players found."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    correct = ESPNMatchScore(
        event_id="new", home_name="Rafael Jodar", away_name="Arthur Fils",
        home_score=0, away_score=0, period="In Progress", is_completed=False,
        is_live=True, last_updated="", linescores=[[3, 3]],
    )
    result = _find_espn_match(pos, [correct])
    assert result is not None
    assert result.event_id == "new"
```

- [ ] **Step 6: Write test — single-team fallback still works**

Add to `tests/unit/orchestration/test_score_enricher.py`:

```python
def test_find_espn_match_single_team_fallback() -> None:
    """Single-team position (no team_b) still uses fallback matching."""
    pos = _pos(question="Tiger Woods wins", sport_tag="golf")
    espn = ESPNMatchScore(
        event_id="g1", home_name="Tiger Woods", away_name="Rory McIlroy",
        home_score=None, away_score=None, period="", is_completed=False,
        is_live=False, last_updated="",
    )
    result = _find_espn_match(pos, [espn])
    assert result is not None
    assert result.event_id == "g1"
```

- [ ] **Step 7: Write test — correct match returned over old match**

Add to `tests/unit/orchestration/test_score_enricher.py`:

```python
def test_find_espn_match_prefers_correct_over_old() -> None:
    """When both old and correct matches exist, correct one matches first if listed first."""
    pos = _pos(question="Rafael Jodar vs Arthur Fils", sport_tag="tennis")
    old_match = ESPNMatchScore(
        event_id="old", home_name="Cameron Norrie", away_name="Rafael Jodar",
        home_score=0, away_score=2, period="Final", is_completed=True,
        is_live=False, last_updated="", linescores=[[3, 6], [3, 6]],
    )
    correct = ESPNMatchScore(
        event_id="new", home_name="Rafael Jodar", away_name="Arthur Fils",
        home_score=0, away_score=0, period="In Progress", is_completed=False,
        is_live=True, last_updated="", linescores=[[3, 3]],
    )
    # Correct listed first → matches
    result = _find_espn_match(pos, [correct, old_match])
    assert result is not None
    assert result.event_id == "new"

    # Old listed first → skipped, correct matches
    result2 = _find_espn_match(pos, [old_match, correct])
    assert result2 is not None
    assert result2.event_id == "new"
```

- [ ] **Step 8: Run all score_enricher tests**

Run: `pytest tests/unit/orchestration/test_score_enricher.py -v`

Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add src/orchestration/score_enricher.py tests/unit/orchestration/test_score_enricher.py
git commit -m "fix(score-enricher): require both teams to match in _find_espn_match

Fallback condition (home_a or away_a) was matching positions against
completed matches of the same player from previous rounds. This caused
false score_exit triggers within 1-2 seconds of entry.

Now: two-team positions require both teams to match.
Single-team positions (golf etc.) still use the fallback.

SPEC-008 Fix A."
```

---

### Task 2: Fix B — Serve-for-Match Config

**Files:**
- Modify: `src/config/sport_rules.py:52-66`

- [ ] **Step 1: Add config parameter**

In `src/config/sport_rules.py`, in the `"tennis"` dict (line 52-66), add after `"set_exit_close_set_buffer": 1,`:

```python
        "set_exit_serve_for_match_games": 5,
```

- [ ] **Step 2: Run existing tests to verify no breakage**

Run: `pytest tests/unit/strategy/exit/test_tennis_exit.py -v`

Expected: ALL PASS (config addition is backward-compatible)

- [ ] **Step 3: Commit**

```bash
git add src/config/sport_rules.py
git commit -m "config(tennis): add set_exit_serve_for_match_games threshold

SPEC-008 Fix B prep — SFM games threshold (default 5)."
```

---

### Task 3: Fix B — Serve-for-Match Tests (TDD)

**Files:**
- Modify: `tests/unit/strategy/exit/test_tennis_exit.py`

- [ ] **Step 1: Write T2 SFM tests**

Add to `tests/unit/strategy/exit/test_tennis_exit.py`:

```python
# ── Serve-for-match (SFM) ──

def test_t2_sfm_opp_5_deficit_1_exits() -> None:
    """T2: 1-1 set, 3. sette 4-5 (deficit 1, opp ≥ 5) → ÇIK."""
    info = _info(linescores=[[6, 3], [4, 6], [4, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T2-SFM" in result.detail


def test_t2_sfm_opp_5_deficit_2_exits() -> None:
    """T2: 1-1 set, 3. sette 3-5 (deficit 2, opp ≥ 5) → ÇIK."""
    info = _info(linescores=[[6, 3], [4, 6], [3, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T2-SFM" in result.detail


def test_t2_sfm_opp_4_deficit_1_holds() -> None:
    """T2: 1-1 set, 3. sette 3-4 (opp < 5) → HOLD."""
    info = _info(linescores=[[6, 3], [4, 6], [3, 4]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


def test_t2_sfm_5_5_holds() -> None:
    """T2: 1-1 set, 3. sette 5-5 (deficit 0) → HOLD."""
    info = _info(linescores=[[6, 3], [4, 6], [5, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None
```

- [ ] **Step 2: Write T1 SFM tests**

Add to `tests/unit/strategy/exit/test_tennis_exit.py`:

```python
def test_t1_sfm_opp_5_deficit_1_exits() -> None:
    """T1: 0-1 set, 2. sette 4-5 (deficit 1, opp ≥ 5) → ÇIK."""
    info = _info(linescores=[[3, 6], [4, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1-SFM" in result.detail


def test_t1_sfm_opp_4_holds() -> None:
    """T1: 0-1 set, 2. sette 2-4 (opp < 5) → HOLD."""
    info = _info(linescores=[[3, 6], [2, 4]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None
```

- [ ] **Step 3: Run tests to verify they FAIL**

Run: `pytest tests/unit/strategy/exit/test_tennis_exit.py -v -k "sfm"`

Expected: FAIL — SFM logic not yet implemented.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/unit/strategy/exit/test_tennis_exit.py
git commit -m "test(tennis-exit): add serve-for-match test cases (red)

SPEC-008 Fix B — TDD red phase."
```

---

### Task 4: Fix B — Serve-for-Match Implementation

**Files:**
- Modify: `src/strategy/exit/tennis_exit.py:28-87`

- [ ] **Step 1: Implement SFM logic**

In `src/strategy/exit/tennis_exit.py`, replace the `check()` function body (lines 28-87) with:

```python
def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "tennis",
) -> TennisExitResult | None:
    """Tennis T1/T2 exit kontrolü.

    Returns:
        TennisExitResult → çık; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    linescores = score_info.get("linescores", [])
    if not linescores or len(linescores) < 2:
        return None

    our_is_home = score_info.get("our_is_home", True)
    sets = _map_linescores(linescores, our_is_home)

    completed = sets[:-1]
    current = sets[-1]

    sets_won = sum(1 for our, opp in completed if our > opp)
    sets_lost = sum(1 for our, opp in completed if opp > our)

    current_our, current_opp = current
    deficit = current_opp - current_our
    games_total = current_our + current_opp

    if deficit <= 0:
        return None

    exit_deficit = int(get_sport_rule(sport_tag, "set_exit_deficit", 3))
    exit_games_total = int(get_sport_rule(sport_tag, "set_exit_games_total", 7))
    blowout_deficit = int(get_sport_rule(sport_tag, "set_exit_blowout_deficit", 4))
    close_threshold = int(get_sport_rule(sport_tag, "set_exit_close_set_threshold", 5))
    close_buffer = int(get_sport_rule(sport_tag, "set_exit_close_set_buffer", 1))
    sfm_games = int(get_sport_rule(sport_tag, "set_exit_serve_for_match_games", 5))

    # T1 — Straight set loss (0-1 + current set bad)
    if sets_won == 0 and sets_lost == 1:
        # Serve-for-match: rakip seti/maçı bitirmeye yakın
        if current_opp >= sfm_games:
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T1-SFM: sets=0-1 game={current_our}-{current_opp}",
            )

        effective_deficit = exit_deficit
        if _was_close_set(completed[0], close_threshold):
            effective_deficit += close_buffer

        if _should_exit(deficit, games_total, effective_deficit, exit_games_total, blowout_deficit):
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T1: sets=0-1 game={current_our}-{current_opp} threshold={effective_deficit}",
            )

    # T2 — Decider set loss (1-1 + 3rd set bad)
    if sets_won == 1 and sets_lost == 1:
        # Serve-for-match: rakip maçı bitirmeye yakın
        if current_opp >= sfm_games:
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T2-SFM: sets=1-1 game={current_our}-{current_opp}",
            )

        if _should_exit(deficit, games_total, exit_deficit, exit_games_total, blowout_deficit):
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T2: sets=1-1 game={current_our}-{current_opp}",
            )

    return None
```

- [ ] **Step 2: Run all tennis exit tests**

Run: `pytest tests/unit/strategy/exit/test_tennis_exit.py -v`

Expected: ALL PASS

- [ ] **Step 3: Verify existing T1 close-set-buffer still works**

Note: The SFM check is BEFORE `_should_exit`. At `[6,7],[2,5]` (close set buffer test):
- sets_won=0, sets_lost=1 → T1
- current_opp=5 ≥ sfm_games(5) → SFM would trigger!

This changes behavior: previously this HOLD'd (close set buffer), now it EXITS (SFM).
**This is correct behavior** — if opponent is at 5 in a match-ending set, exit regardless of
previous set closeness. Rakip seti bitirmeye 1 game uzakta.

Update the existing test `test_t1_close_set_buffer` to reflect new expected behavior:

In `tests/unit/strategy/exit/test_tennis_exit.py`, update:

```python
def test_t1_close_set_buffer() -> None:
    """1. set 6-7 tiebreak + 2. set 2-5 → EXIT (SFM overrides buffer: opp=5)."""
    info = _info(linescores=[[6, 7], [2, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1-SFM" in result.detail
```

Also update `test_t2_decider_deficit_2_hold` — at 3-5 in decider, SFM now triggers:

```python
def test_t2_decider_deficit_2_sfm_exits() -> None:
    """1-1 set + 3. sette 3-5 (deficit 2, opp=5) → EXIT (SFM)."""
    info = _info(linescores=[[6, 3], [4, 6], [3, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T2-SFM" in result.detail
```

- [ ] **Step 4: Run all tests again**

Run: `pytest tests/unit/strategy/exit/test_tennis_exit.py -v`

Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v --tb=short`

Expected: ALL PASS — no regressions.

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/tennis_exit.py tests/unit/strategy/exit/test_tennis_exit.py
git commit -m "feat(tennis-exit): add serve-for-match rule (SFM)

In match-ending sets (T1: 0-1 set 2, T2: 1-1 set 3), exit when
opponent reaches 5+ games and we're behind. Overrides deficit
threshold — opponent is 1 game from closing the set/match.

Config: set_exit_serve_for_match_games (default 5).

SPEC-008 Fix B."
```

---

### Task 5: Fix C — Trade History Cleanup + TDD Update

**Files:**
- Modify: `logs/trade_history.jsonl` (3 satır sil)
- Modify: `TDD.md:549`

- [ ] **Step 1: Remove 3 ghost trades from trade_history.jsonl**

Remove the 3 lines where `slug == "atp-jodar-fils-2026-04-18"` AND
`exit_timestamp` is within 2 seconds of `entry_timestamp`:

```
entry 14:07:04 → exit 14:07:05 ($0)
entry 14:09:20 → exit 14:09:22 ($0)
entry 14:11:35 → exit 14:11:36 ($0)
```

Keep the 4th trade (entry 14:14:41 → exit 14:25:55, +$2.62).

Use grep to identify exact lines, then use a Python one-liner or manual edit.

- [ ] **Step 2: Update TDD.md §6.9d**

In `TDD.md` after line 549 (`Config: \`sport_rules.py → tennis → set_exit_*\`. Dönüş ihtimali %3-8.`), add:

```markdown

**Serve-for-match (SFM):** Maç bitirici sette (T1: set 2 when 0-1, T2: set 3
when 1-1) rakip ≥ 5 game + gerideyiz → çık. Config: `set_exit_serve_for_match_games`.
Deficit eşiği ve games_total kontrolü bu durumda atlanır — rakip seti/maçı
bitirmek için 1 game uzakta, dönüş ihtimali %8-15.
```

- [ ] **Step 3: Verify dashboard reflects corrected data**

Start dashboard and confirm:
- Exited tab: 3 ghost trades gone
- PnL totals: updated (3× $0 removed = no numeric change, but trade count -3)
- Per Trade PnL chart: 3 phantom bars removed

- [ ] **Step 4: Commit**

```bash
git add logs/trade_history.jsonl TDD.md
git commit -m "fix(data): remove 3 ghost trades + update TDD with SFM rule

Ghost trades caused by _find_espn_match bug (SPEC-008 Fix A).
TDD §6.9d updated with serve-for-match documentation.

SPEC-008 Fix C."
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`

Expected: ALL PASS

- [ ] **Step 2: Verify file sizes**

Run: `wc -l src/orchestration/score_enricher.py src/strategy/exit/tennis_exit.py src/config/sport_rules.py tests/unit/strategy/exit/test_tennis_exit.py tests/unit/orchestration/test_score_enricher.py`

Expected: All < 400 lines.

- [ ] **Step 3: Grep for old fallback pattern**

Run: `grep -n "home_a or away_a" src/orchestration/score_enricher.py`

Expected: Only the fixed line with `not team_b and` prefix.
