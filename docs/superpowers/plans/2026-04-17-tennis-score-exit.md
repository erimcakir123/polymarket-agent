# Tennis Score-Based Exit (T1-T2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tennis A-conf hold pozisyonlarda set/game skoru kullanarak kaybedilen maçlardan erken çıkış (T1: straight set, T2: decider set).

**Architecture:** `tennis_exit.py` (Strategy, pure) → `monitor.py` sport gate ile çağırır. ESPN linescores + direction mapping ile our/opp set/game hesaplanır. Config-driven eşikler `sport_rules.py`'den.

**Tech Stack:** Python 3.12+, dataclasses, pytest

**Spec:** `docs/superpowers/specs/2026-04-17-tennis-score-exit-design.md`

---

## File Map

| Dosya | Aksiyon | Sorumluluk |
|---|---|---|
| `src/strategy/exit/tennis_exit.py` | **CREATE** | T1/T2 pure exit kuralları |
| `tests/unit/strategy/exit/test_tennis_exit.py` | **CREATE** | 9 birim test |
| `src/config/sport_rules.py` | **MODIFY** | Tennis exit config eşikleri |
| `src/orchestration/score_enricher.py` | **MODIFY** | `our_is_home` flag ekle |
| `src/strategy/exit/monitor.py` | **MODIFY** | Tennis exit çağrısı |
| `tests/unit/strategy/exit/test_monitor.py` | **MODIFY** | Integration test |

---

## Task 1: Sport Rules Config + score_enricher our_is_home

**Files:**
- Modify: `src/config/sport_rules.py:40-46`
- Modify: `src/orchestration/score_enricher.py:136-144`

- [ ] **Step 1: Add tennis exit config to sport_rules.py**

In `src/config/sport_rules.py`, replace the existing `"tennis"` entry with:

```python
"tennis": {
    "stop_loss_pct": 0.35,
    "match_duration_hours": 2.5,
    "match_duration_hours_bo3": 1.75,
    "match_duration_hours_bo5": 3.5,
    "set_exit": True,
    "score_source": "espn",
    "espn_sport": "tennis",
    "espn_league": "atp",
    "set_exit_deficit": 3,
    "set_exit_games_total": 7,
    "set_exit_blowout_deficit": 4,
    "set_exit_close_set_threshold": 5,
    "set_exit_close_set_buffer": 1,
},
```

- [ ] **Step 2: Add our_is_home to score_info in score_enricher.py**

In `src/orchestration/score_enricher.py`, find the `_build_score_info` function's return statement (around line 136-144). Replace it with:

```python
    deficit = opp_score - our_score  # pozitif = gerideyiz
    linescores: list = getattr(ms, "linescores", []) or []

    # Direction-aware home mapping for linescores:
    # our_is_home=True → linescores[i][0] = our games
    our_is_home = (pos.direction == "BUY_YES") == a_is_home

    return {
        "available": True,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": ms.period,
        "map_diff": -deficit,
        "linescores": linescores,
        "our_is_home": our_is_home,
    }
```

- [ ] **Step 3: Run existing tests**

```bash
python -m pytest tests/unit/orchestration/test_score_enricher.py tests/unit/config/test_sport_rules.py -q
```
Expected: All PASS (backward compatible — new fields)

- [ ] **Step 4: Commit**

```bash
git add src/config/sport_rules.py src/orchestration/score_enricher.py
git commit -m "feat(config): tennis exit thresholds + our_is_home flag (SPEC-006 Task 1)"
```

---

## Task 2: Tennis Exit — Pure Function

**Files:**
- Create: `src/strategy/exit/tennis_exit.py`
- Create: `tests/unit/strategy/exit/test_tennis_exit.py`

- [ ] **Step 1: Write ALL failing tests**

```python
# tests/unit/strategy/exit/test_tennis_exit.py
"""Tennis score-based exit tests (SPEC-006)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.tennis_exit import check, TennisExitResult


def _info(
    linescores: list[list[int]] | None = None,
    our_is_home: bool = True,
    available: bool = True,
) -> dict:
    """Test helper: score_info dict oluştur."""
    ls = linescores or []
    return {
        "available": available,
        "our_score": 0,
        "opp_score": 0,
        "deficit": 0,
        "period": "",
        "map_diff": 0,
        "linescores": ls,
        "our_is_home": our_is_home,
    }


# ── T1: Straight set loss approaching ──

def test_t1_straight_set_2_5() -> None:
    """0-1 set + 2. sette 2-5 (deficit 3, total 7) → EXIT."""
    info = _info(linescores=[[3, 6], [2, 5]], our_is_home=True)
    # 1. set: our=3 opp=6 → kaybettik. 2. set: our=2 opp=5 → deficit 3, total 7
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "T1" in result.detail


def test_t1_early_deficit_1_4_hold() -> None:
    """0-1 set + 1-4 (total 5 < 7, deficit 3) → HOLD (too early)."""
    info = _info(linescores=[[3, 6], [1, 4]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


def test_t1_deficit_4_any_total() -> None:
    """0-1 set + 0-4 (deficit 4) → EXIT regardless of total."""
    info = _info(linescores=[[3, 6], [0, 4]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1" in result.detail


def test_t1_close_set_buffer() -> None:
    """1. set 6-7 tiebreak + 2. set 2-5 → HOLD (close set buffer: threshold 3→4)."""
    info = _info(linescores=[[6, 7], [2, 5]], our_is_home=True)
    # 1. set: 6-7 → close set (opp won with ≥5 games from us). deficit=3 < 4 → HOLD
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


def test_t1_blowout_no_buffer() -> None:
    """1. set 2-6 blowout + 2. set 2-5 → EXIT (no buffer for blowout)."""
    info = _info(linescores=[[2, 6], [2, 5]], our_is_home=True)
    # 1. set: 2-6 → blowout (our < close_set_threshold=5). deficit=3 ≥ 3 + total=7 → EXIT
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1" in result.detail


# ── T2: Decider set loss ──

def test_t2_decider_2_5() -> None:
    """1-1 set + 3. sette 2-5 (deficit 3, total 7) → EXIT."""
    info = _info(linescores=[[6, 3], [4, 6], [2, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T2" in result.detail


def test_t2_decider_deficit_2_hold() -> None:
    """1-1 set + 3. sette 3-5 (deficit 2) → HOLD."""
    info = _info(linescores=[[6, 3], [4, 6], [3, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


# ── Edge cases ──

def test_no_score_no_exit() -> None:
    """available=False → no exit."""
    info = _info(available=False)
    result = check(info, current_price=0.10, sport_tag="tennis")
    assert result is None


def test_winning_no_exit() -> None:
    """1-0 set + 2. set 4-2 → winning, no exit."""
    info = _info(linescores=[[6, 3], [4, 2]], our_is_home=True)
    result = check(info, current_price=0.70, sport_tag="tennis")
    assert result is None


# ── Direction: BUY_NO (our_is_home=False) ──

def test_buy_no_direction_mapping() -> None:
    """BUY_NO: our_is_home=False → linescores[i][1] = our games."""
    # Home=Muchova (opp), Away=Gauff (our). Muchova winning.
    # linescores: [[6,3],[5,2]] → home perspective
    # our_is_home=False → our: [3,2], opp: [6,5]
    # 1. set: our=3 opp=6 → lost. 2. set: our=2 opp=5 → deficit 3, total 7
    info = _info(linescores=[[6, 3], [5, 2]], our_is_home=False)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1" in result.detail
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
python -m pytest tests/unit/strategy/exit/test_tennis_exit.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.strategy.exit.tennis_exit'`

- [ ] **Step 3: Write tennis_exit.py implementation**

```python
# src/strategy/exit/tennis_exit.py
"""Tennis score-based exit — SPEC-006 T1/T2.

BO3 tennis A-conf hold pozisyonlarda set/game skoru ile erken çıkış.
Pure fonksiyon: I/O yok. Eşikler sport_rules.py config'inden.

T1: Straight set kaybı yaklaşıyor (0-1 set + current set deficit ≥ 3)
T2: Decider set kaybı (1-1 set + 3. set deficit ≥ 3)

Tiebreak buffer: 1. set tiebreak kaybı (dar) → T1 deficit eşiği +1.
Blowout: 1. sette our_games < close_set_threshold → buffer yok.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class TennisExitResult:
    """Tennis exit sonucu — monitor.py ExitSignal'a çevirir."""

    reason: ExitReason
    detail: str


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
        return None  # En az 2 set verisi lazım (1 bitmiş + 1 devam eden)

    our_is_home = score_info.get("our_is_home", True)

    # Linescores'u our/opp perspective'e çevir
    sets = _map_linescores(linescores, our_is_home)

    # Bitmiş setler vs devam eden set
    completed = sets[:-1]
    current = sets[-1]

    sets_won = sum(1 for our, opp in completed if our > opp)
    sets_lost = sum(1 for our, opp in completed if opp > our)

    current_our, current_opp = current
    deficit = current_opp - current_our
    games_total = current_our + current_opp

    if deficit <= 0:
        return None  # Mevcut sette öndeyiz veya eşitiz

    # Config eşikleri
    exit_deficit = int(get_sport_rule(sport_tag, "set_exit_deficit", 3))
    exit_games_total = int(get_sport_rule(sport_tag, "set_exit_games_total", 7))
    blowout_deficit = int(get_sport_rule(sport_tag, "set_exit_blowout_deficit", 4))
    close_threshold = int(get_sport_rule(sport_tag, "set_exit_close_set_threshold", 5))
    close_buffer = int(get_sport_rule(sport_tag, "set_exit_close_set_buffer", 1))

    # T1 — Straight set loss (0-1 + current set bad)
    if sets_won == 0 and sets_lost == 1:
        effective_deficit = exit_deficit
        # Tiebreak buffer: 1. set dar kaybı → eşik yükselt
        if _was_close_set(completed[0], close_threshold):
            effective_deficit += close_buffer

        if _should_exit(deficit, games_total, effective_deficit, exit_games_total, blowout_deficit):
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T1: sets=0-1 game={current_our}-{current_opp} eff_threshold={effective_deficit}",
            )

    # T2 — Decider set loss (1-1 + 3rd set bad)
    if sets_won == 1 and sets_lost == 1:
        # T2'de tiebreak buffer yok — 3. set decider, tolerans yok
        if _should_exit(deficit, games_total, exit_deficit, exit_games_total, blowout_deficit):
            return TennisExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"T2: sets=1-1 game={current_our}-{current_opp}",
            )

    return None


def _map_linescores(linescores: list[list[int]], our_is_home: bool) -> list[tuple[int, int]]:
    """Raw linescores → (our_games, opp_games) per set."""
    result = []
    for pair in linescores:
        if len(pair) < 2:
            continue
        if our_is_home:
            result.append((pair[0], pair[1]))
        else:
            result.append((pair[1], pair[0]))
    return result


def _was_close_set(set_scores: tuple[int, int], threshold: int) -> bool:
    """Kaybedilen set dar mıydı? (tiebreak veya 5+ game aldıysak)."""
    our, opp = set_scores
    if our >= opp:
        return False  # Biz kazandık, kaybedilen set değil
    return our >= threshold  # 5-7, 6-7 gibi → close; 2-6, 3-6 gibi → blowout


def _should_exit(
    deficit: int,
    games_total: int,
    exit_deficit: int,
    exit_games_total: int,
    blowout_deficit: int,
) -> bool:
    """Exit koşulu karşılandı mı?"""
    # Deficit çok büyükse → games_total şartsız (0-4, 1-5, 0-5)
    if deficit >= blowout_deficit:
        return True
    # Normal: deficit + games_total birlikte
    return deficit >= exit_deficit and games_total >= exit_games_total
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
python -m pytest tests/unit/strategy/exit/test_tennis_exit.py -v
```
Expected: All 10 PASS

- [ ] **Step 5: Run full suite**

```bash
python -m pytest tests/ -q
```
Expected: All PASS, no regressions

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/tennis_exit.py tests/unit/strategy/exit/test_tennis_exit.py
git commit -m "feat(exit): tennis T1/T2 score-based exit (SPEC-006 Task 2)"
```

---

## Task 3: Monitor.py Integration + Integration Test

**Files:**
- Modify: `src/strategy/exit/monitor.py:180-194`
- Modify: `tests/unit/strategy/exit/test_monitor.py`

- [ ] **Step 1: Write failing integration test**

Append to `tests/unit/strategy/exit/test_monitor.py`:

```python
def test_tennis_score_exit_t1_in_monitor() -> None:
    """Tennis T1 score exit monitor.py'den tetiklenir."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        confidence="A", entry_price=0.64, current_price=0.25,
        size_usdc=56, shares=87, match_start_iso=_iso(start),
        sport_tag="tennis",
    )
    # 0-1 set + 2. sette 2-5 → T1
    score_info = {
        "available": True,
        "our_score": 0, "opp_score": 1,
        "deficit": 1, "period": "In Progress",
        "map_diff": -1,
        "linescores": [[3, 6], [2, 5]],
        "our_is_home": True,
    }
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "T1" in r.exit_signal.detail


def test_tennis_score_no_exit_when_winning() -> None:
    """Tennis 1-0 set + öndeyiz → exit yok."""
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    p = _pos(
        confidence="A", entry_price=0.64, current_price=0.75,
        size_usdc=56, shares=87, match_start_iso=_iso(start),
        sport_tag="tennis",
    )
    score_info = {
        "available": True,
        "our_score": 1, "opp_score": 0,
        "deficit": -1, "period": "In Progress",
        "map_diff": 1,
        "linescores": [[6, 3], [4, 2]],
        "our_is_home": True,
    }
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is None
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
python -m pytest tests/unit/strategy/exit/test_monitor.py::test_tennis_score_exit_t1_in_monitor -v
```
Expected: FAIL — tennis exit not wired yet

- [ ] **Step 3: Wire tennis_exit into monitor.py**

In `src/strategy/exit/monitor.py`, add import at top:

```python
from src.strategy.exit import a_conf_hold, catastrophic_watch, favored, graduated_sl, near_resolve, scale_out, score_exit, stop_loss, tennis_exit
```

After the hockey score_exit block (line ~194), before the market flip block, add:

```python
        # 3a-tennis. Score-based exit — tennis (SPEC-006 T1/T2)
        if _normalize(pos.sport_tag) == "tennis" and score_info.get("available"):
            t_result = tennis_exit.check(
                score_info=score_info,
                current_price=pos.current_price,
                sport_tag=pos.sport_tag,
            )
            if t_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=t_result.reason, detail=t_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
python -m pytest tests/unit/strategy/exit/test_monitor.py -v
```
Expected: All PASS (existing + 2 new)

- [ ] **Step 5: Run full suite**

```bash
python -m pytest tests/ -q
```
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/monitor.py tests/unit/strategy/exit/test_monitor.py
git commit -m "feat(wire): tennis T1/T2 exit in monitor.py (SPEC-006 Task 3)"
```

---

## Task 4: TDD.md + SPEC Status Update

**Files:**
- Modify: `TDD.md`
- Modify: `SPEC.md`

- [ ] **Step 1: Add §6.9d to TDD.md**

Find the §6.9c section (Score Polling Altyapısı) and add after it:

```markdown
#### 6.9d Tennis Score-Based Exit (SPEC-006)

ESPN set/game skoru ile tennis A-conf hold pozisyonlarda erken çıkış. BO3 only.

**T1 — Straight set kaybı:** 0-1 set + current set deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4).
Tiebreak buffer: 1. set dar kaybı (our ≥ 5 game, ör: 6-7) → deficit eşiği +1 (3→4).
Blowout (our < 5, ör: 2-6) → buffer yok.

**T2 — Decider set kaybı:** 1-1 set + 3. set deficit ≥ 3 + games_total ≥ 7 (veya deficit ≥ 4).
Tiebreak buffer uygulanmaz (3. set decider, tolerans yok).

Config: `sport_rules.py → tennis → set_exit_*`. Dönüş ihtimali %3-8.
```

- [ ] **Step 2: Update TDD.md §7.2 tennis row**

Find the tennis row in the sport rules table and update:

```markdown
| Tennis (ATP/WTA) | 0.35 | 1.75-3.5 (BO3/BO5) | T1/T2 set-game exit + market_flip DISABLED + catastrophic DISABLED |
```

- [ ] **Step 3: Update SPEC.md status**

Change SPEC-006 status from `DRAFT` to `IMPLEMENTED`.

- [ ] **Step 4: Commit**

```bash
git add TDD.md SPEC.md
git commit -m "docs: SPEC-006 tennis score exit — TDD + SPEC status update"
```
