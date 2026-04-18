# Baseball Inning Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Baseball maçlarında inning+skor bazlı canlılık matrisi ile flat SL'yi kontrol et — canlı maçta SL devre dışı, ölü maçta SL aktif.

**Architecture:** `stop_loss.py`'ye 2 pure fonksiyon eklenir (parse + canlılık). `check()` ve `compute_stop_loss_pct()` imzalarına `score_info` eklenir. `monitor.py`'de tek satır değişiklik. Config `sport_rules.py`'den okunur.

**Tech Stack:** Python 3.12+, pytest, mevcut ESPN score_info altyapısı

**Spec:** `docs/superpowers/specs/2026-04-18-baseball-inning-guard-design.md`

---

## File Map

| Dosya | İşlem | Sorumluluk |
|---|---|---|
| `src/config/sport_rules.py` | MODIFY | `comeback_thresholds` + `extra_inning_threshold` config |
| `src/strategy/exit/stop_loss.py` | MODIFY | `parse_baseball_inning()` + `is_baseball_alive()` + imza güncellemeleri |
| `src/strategy/exit/monitor.py` | MODIFY | `score_info` iletimi (1 satır) |
| `tests/unit/strategy/exit/test_baseball_guard.py` | CREATE | Parse + canlılık + entegrasyon testleri |

---

### Task 1: Config — comeback_thresholds ekle

**Files:**
- Modify: `src/config/sport_rules.py:42-51`
- Test: `tests/unit/strategy/exit/test_baseball_guard.py`

- [ ] **Step 1: Write the failing test**

Dosya: `tests/unit/strategy/exit/test_baseball_guard.py`

```python
"""Baseball inning guard testleri (SPEC-008)."""
from __future__ import annotations

from src.config.sport_rules import get_sport_rule


def test_mlb_comeback_thresholds_configured() -> None:
    thresholds = get_sport_rule("mlb", "comeback_thresholds")
    assert thresholds is not None
    assert thresholds[3] == 6   # inning 1-3: 6 run
    assert thresholds[5] == 5   # inning 4-5: 5 run
    assert thresholds[7] == 4   # inning 6-7: 4 run
    assert thresholds[8] == 3   # inning 8: 3 run
    assert thresholds[9] == 2   # inning 9: 2 run


def test_mlb_extra_inning_threshold_configured() -> None:
    assert get_sport_rule("mlb", "extra_inning_threshold") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py -v`
Expected: FAIL — `comeback_thresholds` key doesn't exist yet, returns `None`

- [ ] **Step 3: Add config to sport_rules.py**

`src/config/sport_rules.py` — `mlb` bloğuna ekle:

```python
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
        "comeback_thresholds": {3: 6, 5: 5, 7: 4, 8: 3, 9: 2},
        "extra_inning_threshold": 1,
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/config/sport_rules.py tests/unit/strategy/exit/test_baseball_guard.py
git commit -m "feat(config): add baseball comeback_thresholds to sport_rules"
```

---

### Task 2: parse_baseball_inning() — ESPN period string'den inning çıkar

**Files:**
- Modify: `src/strategy/exit/stop_loss.py`
- Test: `tests/unit/strategy/exit/test_baseball_guard.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/strategy/exit/test_baseball_guard.py`'ye ekle:

```python
from src.strategy.exit.stop_loss import parse_baseball_inning


def test_parse_inning_top_1st_returns_1() -> None:
    assert parse_baseball_inning("Top 1st") == 1


def test_parse_inning_bot_5th_returns_5() -> None:
    assert parse_baseball_inning("Bot 5th") == 5


def test_parse_inning_mid_9th_returns_9() -> None:
    assert parse_baseball_inning("Mid 9th") == 9


def test_parse_inning_top_2nd_returns_2() -> None:
    assert parse_baseball_inning("Top 2nd") == 2


def test_parse_inning_bot_3rd_returns_3() -> None:
    assert parse_baseball_inning("Bot 3rd") == 3


def test_parse_inning_extra_11th_returns_11() -> None:
    assert parse_baseball_inning("Top 11th") == 11


def test_parse_inning_empty_returns_none() -> None:
    assert parse_baseball_inning("") is None


def test_parse_inning_final_returns_none() -> None:
    assert parse_baseball_inning("Final") is None


def test_parse_inning_in_progress_returns_none() -> None:
    assert parse_baseball_inning("In Progress") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py::test_parse_inning_top_1st_returns_1 -v`
Expected: FAIL — `ImportError: cannot import name 'parse_baseball_inning'`

- [ ] **Step 3: Implement parse_baseball_inning()**

`src/strategy/exit/stop_loss.py` — dosyanın üstüne `import re` ekle, fonksiyonu `_TOTALS_KEYWORDS` tanımından sonra ekle:

```python
import re

_INNING_RE = re.compile(r"(\d+)(?:st|nd|rd|th)")


def parse_baseball_inning(period: str) -> int | None:
    """ESPN period string'inden inning numarası çıkar.

    "Top 1st" → 1, "Bot 5th" → 5, "Mid 9th" → 9.
    Parse edilemezse None döner.
    """
    if not period:
        return None
    m = _INNING_RE.search(period)
    return int(m.group(1)) if m else None
```

- [ ] **Step 4: Run all parse tests to verify they pass**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py -k "parse" -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/strategy/exit/stop_loss.py tests/unit/strategy/exit/test_baseball_guard.py
git commit -m "feat(stop_loss): add parse_baseball_inning for ESPN period strings"
```

---

### Task 3: is_baseball_alive() — canlılık matrisi

**Files:**
- Modify: `src/strategy/exit/stop_loss.py`
- Test: `tests/unit/strategy/exit/test_baseball_guard.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/strategy/exit/test_baseball_guard.py`'ye ekle:

```python
from src.strategy.exit.stop_loss import is_baseball_alive


def test_alive_deficit_0_any_inning() -> None:
    """Eşit skor → her zaman canlı."""
    assert is_baseball_alive(inning=1, deficit=0) is True
    assert is_baseball_alive(inning=9, deficit=0) is True


def test_alive_leading_any_inning() -> None:
    """Önde → her zaman canlı."""
    assert is_baseball_alive(inning=9, deficit=-3) is True


def test_alive_inning_1_deficit_5() -> None:
    """1. inning, 5 run geride ama eşik 6 → canlı."""
    assert is_baseball_alive(inning=1, deficit=5) is True


def test_dead_inning_1_deficit_6() -> None:
    """1. inning, 6 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=1, deficit=6) is False


def test_dead_inning_3_deficit_7() -> None:
    """3. inning, 7 run geride > eşik 6 → ölü."""
    assert is_baseball_alive(inning=3, deficit=7) is False


def test_alive_inning_4_deficit_4() -> None:
    """4. inning, 4 run geride < eşik 5 → canlı."""
    assert is_baseball_alive(inning=4, deficit=4) is True


def test_dead_inning_5_deficit_5() -> None:
    """5. inning, 5 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=5, deficit=5) is False


def test_alive_inning_6_deficit_3() -> None:
    """6. inning, 3 run geride < eşik 4 → canlı."""
    assert is_baseball_alive(inning=6, deficit=3) is True


def test_dead_inning_7_deficit_4() -> None:
    """7. inning, 4 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=7, deficit=4) is False


def test_alive_inning_8_deficit_2() -> None:
    """8. inning, 2 run geride < eşik 3 → canlı."""
    assert is_baseball_alive(inning=8, deficit=2) is True


def test_dead_inning_8_deficit_3() -> None:
    """8. inning, 3 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=8, deficit=3) is False


def test_alive_inning_9_deficit_1() -> None:
    """9. inning, 1 run geride < eşik 2 → canlı."""
    assert is_baseball_alive(inning=9, deficit=1) is True


def test_dead_inning_9_deficit_2() -> None:
    """9. inning, 2 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=9, deficit=2) is False


def test_dead_extra_deficit_1() -> None:
    """Uzatma (10+), 1 run geride = eşik → ölü."""
    assert is_baseball_alive(inning=10, deficit=1) is False
    assert is_baseball_alive(inning=12, deficit=1) is False


def test_alive_extra_deficit_0() -> None:
    """Uzatma, eşit → canlı."""
    assert is_baseball_alive(inning=10, deficit=0) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py::test_alive_deficit_0_any_inning -v`
Expected: FAIL — `ImportError: cannot import name 'is_baseball_alive'`

- [ ] **Step 3: Implement is_baseball_alive()**

`src/strategy/exit/stop_loss.py` — `parse_baseball_inning()` fonksiyonundan sonra ekle:

```python
def is_baseball_alive(inning: int, deficit: int) -> bool:
    """Canlılık matrisi — maç hala kazanılabilir mi?

    True=canlı (SL devre dışı), False=ölü (SL aktif).
    deficit = opp_score - our_score (pozitif = gerideyiz).
    """
    if deficit <= 0:
        return True

    thresholds: dict[int, int] = get_sport_rule("mlb", "comeback_thresholds", {})
    extra_thresh: int = get_sport_rule("mlb", "extra_inning_threshold", 1)

    if inning > 9:
        return deficit < extra_thresh

    for max_inning in sorted(thresholds):
        if inning <= max_inning:
            return deficit < thresholds[max_inning]

    return deficit < extra_thresh
```

`get_sport_rule` importunu dosyanın başına ekle:

```python
from src.config.sport_rules import get_stop_loss, get_sport_rule
```

- [ ] **Step 4: Run all canlılık tests to verify they pass**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py -k "alive or dead" -v`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add src/strategy/exit/stop_loss.py tests/unit/strategy/exit/test_baseball_guard.py
git commit -m "feat(stop_loss): add is_baseball_alive liveness matrix"
```

---

### Task 4: stop_loss.py — compute_stop_loss_pct() ve check() imza güncellemesi + guard entegrasyonu

**Files:**
- Modify: `src/strategy/exit/stop_loss.py`
- Test: `tests/unit/strategy/exit/test_baseball_guard.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/strategy/exit/test_baseball_guard.py`'ye ekle:

```python
from src.models.position import Position
from src.strategy.exit.stop_loss import check, compute_stop_loss_pct


def _pos(**over) -> Position:
    base = dict(
        condition_id="c1", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        confidence="B", sport_tag="mlb",
    )
    base.update(over)
    return Position(**base)


def test_baseball_alive_sl_disabled() -> None:
    """Canlı maç (1. inning, 0-0): %35 düşüş → SL tetiklenmez."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    score_info = {"available": True, "deficit": 0, "period": "Top 1st"}
    assert compute_stop_loss_pct(p, score_info) is None
    assert check(p, score_info) is False


def test_baseball_alive_behind_under_threshold() -> None:
    """1. inning, 5 run geride ama eşik 6 → canlı → SL devre dışı."""
    p = _pos(entry_price=0.40, current_price=0.20)  # pnl = -50%
    score_info = {"available": True, "deficit": 5, "period": "Bot 3rd"}
    assert compute_stop_loss_pct(p, score_info) is None
    assert check(p, score_info) is False


def test_baseball_dead_sl_active() -> None:
    """Ölü maç (8. inning, 3 run geride): %35 düşüş → SL tetiklenir."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    score_info = {"available": True, "deficit": 3, "period": "Top 8th"}
    sl = compute_stop_loss_pct(p, score_info)
    assert sl is not None
    assert sl == 0.30  # mlb default SL
    assert check(p, score_info) is True


def test_baseball_dead_but_pnl_above_sl() -> None:
    """Ölü maç ama PnL henüz SL'ye ulaşmadı → tetiklenmez."""
    p = _pos(entry_price=0.40, current_price=0.34)  # pnl = -15%
    score_info = {"available": True, "deficit": 3, "period": "Top 8th"}
    sl = compute_stop_loss_pct(p, score_info)
    assert sl == 0.30
    assert check(p, score_info) is False


def test_baseball_unknown_sl_fallback() -> None:
    """Veri yok → SL normal çalışır (fallback)."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    assert check(p, None) is True
    assert check(p) is True  # geriye uyumlu


def test_baseball_unparseable_period_fallback() -> None:
    """Period parse edilemiyor → fallback, SL normal."""
    p = _pos(entry_price=0.40, current_price=0.26)  # pnl = -35%
    score_info = {"available": True, "deficit": 0, "period": "In Progress"}
    assert check(p, score_info) is True


def test_baseball_score_not_available_fallback() -> None:
    """available=False → fallback."""
    p = _pos(entry_price=0.40, current_price=0.26)
    score_info = {"available": False, "deficit": 0, "period": "Top 1st"}
    assert check(p, score_info) is True


def test_non_baseball_unaffected() -> None:
    """NBA → baseball guard atlanır → SL normal çalışır."""
    p = _pos(entry_price=0.40, current_price=0.26, sport_tag="nba")
    score_info = {"available": True, "deficit": 0, "period": "Top 1st"}
    sl = compute_stop_loss_pct(p, score_info)
    assert sl == 0.35  # NBA SL, guard bypass
    assert check(p, score_info) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py::test_baseball_alive_sl_disabled -v`
Expected: FAIL — `compute_stop_loss_pct()` doesn't accept `score_info` yet

- [ ] **Step 3: Update compute_stop_loss_pct() and check()**

`src/strategy/exit/stop_loss.py` — `compute_stop_loss_pct` fonksiyonunu güncelle:

İmzayı değiştir:
```python
def compute_stop_loss_pct(pos: Position, score_info: dict | None = None) -> float | None:
```

Katman 2 (totals/spread skip) ile katman 3 (ultra-low) arasına yeni katman ekle:

```python
    # 2.5 Baseball inning guard — canlı maçta SL devre dışı (SPEC-008)
    if _normalize(pos.sport_tag) == "mlb" and score_info and score_info.get("available"):
        period = score_info.get("period", "")
        inning = parse_baseball_inning(period)
        if inning is not None:
            deficit = score_info.get("deficit", 0)
            if is_baseball_alive(inning, deficit):
                return None
```

`_normalize` importunu ekle (zaten `get_sport_rule` ile aynı modülden):
```python
from src.config.sport_rules import get_stop_loss, get_sport_rule, _normalize
```

`check()` fonksiyonunu güncelle:

```python
def check(pos: Position, score_info: dict | None = None) -> bool:
    """Flat SL tetiklendi mi? True → exit sinyali."""
    sl = compute_stop_loss_pct(pos, score_info)
    if sl is None:
        return False
    return pos.unrealized_pnl_pct < -sl
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `pytest tests/unit/strategy/exit/test_baseball_guard.py -v`
Expected: All passed (config + parse + canlılık + entegrasyon)

- [ ] **Step 5: Run existing stop_loss tests — kırılmadığını doğrula**

Run: `pytest tests/unit/strategy/exit/test_stop_loss.py -v`
Expected: All passed — mevcut testler geriye uyumlu (`score_info` default `None`)

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/stop_loss.py tests/unit/strategy/exit/test_baseball_guard.py
git commit -m "feat(stop_loss): integrate baseball liveness guard into SL decision"
```

---

### Task 5: monitor.py — score_info iletimi

**Files:**
- Modify: `src/strategy/exit/monitor.py:222`

- [ ] **Step 1: Update monitor.py**

`src/strategy/exit/monitor.py` satır 222'yi değiştir:

```python
# Mevcut (satır 222):
        if stop_loss.check(pos):

# Yeni:
        if stop_loss.check(pos, score_info):
```

- [ ] **Step 2: Run full test suite to verify nothing breaks**

Run: `pytest tests/ -q`
Expected: All passed

- [ ] **Step 3: Commit**

```bash
git add src/strategy/exit/monitor.py
git commit -m "feat(monitor): pass score_info to stop_loss for baseball guard"
```

---

### Task 6: Son doğrulama

- [ ] **Step 1: Tam test suite çalıştır**

Run: `pytest tests/ -q`
Expected: All passed, 0 failed

- [ ] **Step 2: Dosya boyutu kontrolü**

Run: `wc -l src/strategy/exit/stop_loss.py src/strategy/exit/monitor.py src/config/sport_rules.py`
Expected: Hepsi 400 satır altında

- [ ] **Step 3: Import kontrolü — katman ihlali yok**

`stop_loss.py` sadece `src/config/` ve `src/models/` import eder → strategy → config/domain, katman uyumlu.

- [ ] **Step 4: Final commit (gerekirse)**

```bash
git add -A
git commit -m "feat(SPEC-008): baseball inning guard — liveness matrix SL control"
```
