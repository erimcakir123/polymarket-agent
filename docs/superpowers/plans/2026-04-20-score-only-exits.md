# Score-Only Exit System (A3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fiyat-refleks SL guard'larını (flat SL, graduated SL, catastrophic bounce) kaldırıp, çıkış kararlarını skor-tabanlı kurallara dayandır. NBA ve NFL için yeni skor-çıkışları ekle. A-hold / non-A-hold dal ayrımını tek dala indirge. MMA ve Golf'ü MVP'den çıkar.

**Architecture:** Mevcut `src/strategy/exit/` dizininde iki yeni pure fonksiyon modülü (`nba_score_exit.py`, `nfl_score_exit.py`) hockey_score_exit benzeri yapıda. `monitor.py` öncelik zinciri tek dal olarak yeniden yazılır. Silmeler sistematik: önce modül + test, sonra çağrı yerleri, sonra config + enum.

**Tech Stack:** Python 3.12, Pydantic v2 (Position model), pytest, sport_rules.py config layer.

**Spec:** [docs/superpowers/specs/2026-04-20-score-only-exits-design.md](../specs/2026-04-20-score-only-exits-design.md)

---

## Task 1: NBA Score Exit Modülü (TDD)

**Files:**
- Test: `tests/unit/strategy/exit/test_nba_score_exit.py` (yeni)
- Create: `src/strategy/exit/nba_score_exit.py` (yeni)

- [ ] **Step 1.1: Failing testleri yaz**

```python
"""nba_score_exit.py birim testleri — N1 + N2."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit import nba_score_exit


def _score(deficit: int = 0, available: bool = True) -> dict:
    return {"available": available, "deficit": deficit}


def test_n1_triggers_at_q3_end_with_20_deficit() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=20), elapsed_pct=0.76, sport_tag="nba")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.detail


def test_n1_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=25), elapsed_pct=0.74, sport_tag="nba")
    assert r is None


def test_n1_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=19), elapsed_pct=0.80, sport_tag="nba")
    assert r is None


def test_n2_triggers_at_final_minutes_with_10_deficit() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=10), elapsed_pct=0.93, sport_tag="nba")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.detail


def test_n2_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=15), elapsed_pct=0.91, sport_tag="nba")
    assert r is None


def test_n2_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=9), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_deficit_zero_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=0), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_deficit_negative_means_we_are_ahead_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=-8), elapsed_pct=0.95, sport_tag="nba")
    assert r is None


def test_score_info_unavailable_returns_none() -> None:
    r = nba_score_exit.check(score_info=_score(deficit=25, available=False), elapsed_pct=0.95, sport_tag="nba")
    assert r is None
```

- [ ] **Step 1.2: Testleri çalıştır, başarısız olmalarını doğrula**

Run: `pytest tests/unit/strategy/exit/test_nba_score_exit.py -v`
Expected: FAIL (ModuleNotFoundError: nba_score_exit)

- [ ] **Step 1.3: Modülü yaz**

```python
"""NBA score exit (SPEC score-only — A3 spec).

N1 — Late game + ağır fark (Q3 sonu + 20+ sayı)
N2 — Son dakikalar + iki possession (son 4dk + 10+ sayı)

Pure fonksiyon: I/O yok, tüm veri parametre olarak gelir. Tüm threshold'lar
sport_rules.py config'inden okunur (magic number yok).

Hockey K2/K4 simetrisinde: geç maç + insurmountable deficit. Erken fire etmez.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class NBAExitResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    elapsed_pct: float,
    sport_tag: str = "nba",
) -> NBAExitResult | None:
    """NBA N1/N2 exit kontrolü.

    Returns:
        NBAExitResult → çık; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    deficit = int(score_info.get("deficit", 0))
    if deficit <= 0:
        return None

    n1_elapsed = float(get_sport_rule(sport_tag, "score_exit_n1_elapsed", 0.75))
    n1_deficit = int(get_sport_rule(sport_tag, "score_exit_n1_deficit", 20))
    n2_elapsed = float(get_sport_rule(sport_tag, "score_exit_n2_elapsed", 0.92))
    n2_deficit = int(get_sport_rule(sport_tag, "score_exit_n2_deficit", 10))

    # N2 önce (daha geç + daha küçük deficit gerektirir)
    if elapsed_pct >= n2_elapsed and deficit >= n2_deficit:
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    if elapsed_pct >= n1_elapsed and deficit >= n1_deficit:
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N1: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
```

- [ ] **Step 1.4: Testler geçmeli**

Run: `pytest tests/unit/strategy/exit/test_nba_score_exit.py -v`
Expected: 9 passed

- [ ] **Step 1.5: Commit**

```bash
git add src/strategy/exit/nba_score_exit.py tests/unit/strategy/exit/test_nba_score_exit.py
git commit -m "feat(exit): add NBA score exit (N1/N2) — A3 spec"
```

---

## Task 2: NFL Score Exit Modülü (TDD)

**Files:**
- Test: `tests/unit/strategy/exit/test_nfl_score_exit.py` (yeni)
- Create: `src/strategy/exit/nfl_score_exit.py` (yeni)

- [ ] **Step 2.1: Failing testleri yaz**

```python
"""nfl_score_exit.py birim testleri — N1 + N2."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit import nfl_score_exit


def _score(deficit: int = 0, available: bool = True) -> dict:
    return {"available": available, "deficit": deficit}


def test_n1_triggers_at_q3_end_with_21_deficit() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=21), elapsed_pct=0.76, sport_tag="nfl")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.detail


def test_n1_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=25), elapsed_pct=0.74, sport_tag="nfl")
    assert r is None


def test_n1_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=20), elapsed_pct=0.80, sport_tag="nfl")
    assert r is None


def test_n2_triggers_at_final_minutes_with_11_deficit() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=11), elapsed_pct=0.93, sport_tag="nfl")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.detail


def test_n2_does_not_trigger_when_elapsed_below_gate() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=15), elapsed_pct=0.91, sport_tag="nfl")
    assert r is None


def test_n2_does_not_trigger_when_deficit_below_threshold() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=10), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None


def test_deficit_zero_returns_none() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=0), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None


def test_overtime_with_large_deficit_triggers_n2() -> None:
    # OT'de elapsed 1.0'ı aşabilir; büyük deficit → N2 fire (doğru davranış)
    r = nfl_score_exit.check(score_info=_score(deficit=14), elapsed_pct=1.05, sport_tag="nfl")
    assert r is not None
    assert "N2" in r.detail


def test_score_info_unavailable_returns_none() -> None:
    r = nfl_score_exit.check(score_info=_score(deficit=25, available=False), elapsed_pct=0.95, sport_tag="nfl")
    assert r is None
```

- [ ] **Step 2.2: Testleri çalıştır, başarısız olmalarını doğrula**

Run: `pytest tests/unit/strategy/exit/test_nfl_score_exit.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 2.3: Modülü yaz**

```python
"""NFL score exit (SPEC score-only — A3 spec).

N1 — Late game + 3-skor farkı (Q3 sonu + 21+ sayı = 3 touchdown)
N2 — Son dakikalar + 2-possession (son 5dk + 11+ sayı)

Pure fonksiyon: I/O yok. Tüm threshold'lar sport_rules.py config'inden.
Hockey K2/K4 simetrisinde. Erken fire etmez.

Overtime: elapsed 1.0'ı aşabilir. N2 gate'i aşıldığı için OT'de büyük deficit
→ fire eder (doğru davranış).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class NFLExitResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    elapsed_pct: float,
    sport_tag: str = "nfl",
) -> NFLExitResult | None:
    """NFL N1/N2 exit kontrolü."""
    if not score_info.get("available"):
        return None

    deficit = int(score_info.get("deficit", 0))
    if deficit <= 0:
        return None

    n1_elapsed = float(get_sport_rule(sport_tag, "score_exit_n1_elapsed", 0.75))
    n1_deficit = int(get_sport_rule(sport_tag, "score_exit_n1_deficit", 21))
    n2_elapsed = float(get_sport_rule(sport_tag, "score_exit_n2_elapsed", 0.92))
    n2_deficit = int(get_sport_rule(sport_tag, "score_exit_n2_deficit", 11))

    if elapsed_pct >= n2_elapsed and deficit >= n2_deficit:
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    if elapsed_pct >= n1_elapsed and deficit >= n1_deficit:
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N1: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
```

- [ ] **Step 2.4: Testler geçmeli**

Run: `pytest tests/unit/strategy/exit/test_nfl_score_exit.py -v`
Expected: 9 passed

- [ ] **Step 2.5: Commit**

```bash
git add src/strategy/exit/nfl_score_exit.py tests/unit/strategy/exit/test_nfl_score_exit.py
git commit -m "feat(exit): add NFL score exit (N1/N2) — A3 spec"
```

---

## Task 3: NBA + NFL Config Anahtarlarını Ekle

**Files:**
- Modify: `src/config/sport_rules.py` (NBA + NFL entry'leri)
- Test: `tests/unit/config/test_sport_rules.py` (regression)

- [ ] **Step 3.1: Config test yaz (yeni key'ler + dead key'lerin henüz orada olduğunu doğrula)**

Bu testi test_sport_rules.py'nin sonuna ekle:

```python
def test_nba_has_score_exit_n1_n2_thresholds() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("nba", "score_exit_n1_elapsed") == 0.75
    assert get_sport_rule("nba", "score_exit_n1_deficit") == 20
    assert get_sport_rule("nba", "score_exit_n2_elapsed") == 0.92
    assert get_sport_rule("nba", "score_exit_n2_deficit") == 10


def test_nfl_has_score_exit_n1_n2_thresholds() -> None:
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("nfl", "score_exit_n1_elapsed") == 0.75
    assert get_sport_rule("nfl", "score_exit_n1_deficit") == 21
    assert get_sport_rule("nfl", "score_exit_n2_elapsed") == 0.92
    assert get_sport_rule("nfl", "score_exit_n2_deficit") == 11
```

- [ ] **Step 3.2: Testi çalıştır, başarısız olmalarını doğrula**

Run: `pytest tests/unit/config/test_sport_rules.py -v -k "score_exit_n"`
Expected: FAIL (KeyError veya None)

- [ ] **Step 3.3: sport_rules.py'de NBA + NFL entry'lerini güncelle**

`src/config/sport_rules.py`'de NBA bloğunu bul:

```python
    "nba": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "halftime_exit": True,
        "halftime_exit_deficit": 15,
        "score_source": "espn",
        "espn_sport": "basketball",
        "espn_league": "nba",
    },
```

Ve şöyle değiştir (bu aşamada halftime_exit DEAD key'leri KALSIN — Task 11'de silinecek):

```python
    "nba": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "halftime_exit": True,
        "halftime_exit_deficit": 15,
        "score_source": "espn",
        "espn_sport": "basketball",
        "espn_league": "nba",
        # Score exit N1: Q3 sonu + ağır fark
        "score_exit_n1_elapsed": 0.75,
        "score_exit_n1_deficit": 20,
        # Score exit N2: son dakikalar + iki possession
        "score_exit_n2_elapsed": 0.92,
        "score_exit_n2_deficit": 10,
    },
```

Aynı şekilde NFL bloğu:

```python
    "nfl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.25,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
        "score_source": "espn",
        "espn_sport": "football",
        "espn_league": "nfl",
        # Score exit N1: Q3 sonu + 3-skor farkı
        "score_exit_n1_elapsed": 0.75,
        "score_exit_n1_deficit": 21,
        # Score exit N2: son 5dk + 2-possession
        "score_exit_n2_elapsed": 0.92,
        "score_exit_n2_deficit": 11,
    },
```

- [ ] **Step 3.4: Testler geçmeli**

Run: `pytest tests/unit/config/test_sport_rules.py -v`
Expected: tümü PASS (yeni + eski regression)

- [ ] **Step 3.5: Commit**

```bash
git add src/config/sport_rules.py tests/unit/config/test_sport_rules.py
git commit -m "feat(config): NBA/NFL score exit threshold'lari eklendi"
```

---

## Task 4: Monitor.py'e NBA + NFL Entegrasyonu

**Files:**
- Modify: `src/strategy/exit/monitor.py`
- Test: `tests/unit/strategy/exit/test_monitor.py` (yeni entegrasyon testleri)

- [ ] **Step 4.1: Failing entegrasyon testi yaz**

test_monitor.py'nin sonuna ekle:

```python
def test_nba_score_exit_integration_n1() -> None:
    """NBA pozisyonu + Q3 sonu + 20 sayı deficit → SCORE_EXIT."""
    start = datetime.now(timezone.utc) - timedelta(minutes=120)  # 2h / 2.5h = 0.80 elapsed
    p = _pos(sport_tag="nba", match_start_iso=_iso(start), current_price=0.30)
    score_info = {"available": True, "deficit": 22}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "N1" in r.exit_signal.detail


def test_nfl_score_exit_integration_n2() -> None:
    """NFL pozisyonu + son dakikalar + 14 sayı → SCORE_EXIT N2."""
    start = datetime.now(timezone.utc) - timedelta(minutes=185)  # 185/195 = 0.95 elapsed (3.25h)
    p = _pos(sport_tag="nfl", match_start_iso=_iso(start), current_price=0.30)
    score_info = {"available": True, "deficit": 14}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
    assert "N2" in r.exit_signal.detail


def test_nba_no_early_exit_when_deficit_small_and_early() -> None:
    """NBA early match + küçük deficit → exit yok."""
    start = datetime.now(timezone.utc) - timedelta(minutes=30)  # 30/150 = 0.20
    p = _pos(sport_tag="nba", match_start_iso=_iso(start), current_price=0.35)
    score_info = {"available": True, "deficit": 8}
    r = evaluate(p, score_info=score_info)
    # Sadece fiyat-tabanlı guard'lar aktif, onlar da elapsed<70% → exit yok
    assert r.exit_signal is None
```

- [ ] **Step 4.2: Test çalıştır, başarısız olmalarını doğrula**

Run: `pytest tests/unit/strategy/exit/test_monitor.py::test_nba_score_exit_integration_n1 -v`
Expected: FAIL (NBA henüz monitor.py'de wire edilmemiş)

- [ ] **Step 4.3: monitor.py import'una ekle**

[monitor.py:22](src/strategy/exit/monitor.py#L22) satırında:

```python
from src.strategy.exit import a_conf_hold, baseball_score_exit, catastrophic_watch, cricket_score_exit, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, soccer_score_exit, stop_loss, tennis_score_exit
```

Şöyle yap:

```python
from src.strategy.exit import a_conf_hold, baseball_score_exit, catastrophic_watch, cricket_score_exit, favored, graduated_sl, nba_score_exit, near_resolve, nfl_score_exit, scale_out, hockey_score_exit, soccer_score_exit, stop_loss, tennis_score_exit
```

- [ ] **Step 4.4: A-hold dalında NBA + NFL branch'leri ekle**

[monitor.py:252-262](src/strategy/exit/monitor.py#L252-L262) satırları civarında soccer score exit bloğundan sonra ekle:

```python
        # 3a-nba. Score-based exit — NBA (A3 spec, N1/N2)
        if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
            nba_result = nba_score_exit.check(
                score_info=score_info,
                elapsed_pct=elapsed_pct,
                sport_tag=pos.sport_tag,
            )
            if nba_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=nba_result.reason, detail=nba_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )

        # 3a-nfl. Score-based exit — NFL (A3 spec, N1/N2)
        if _normalize(pos.sport_tag) == "nfl" and score_info.get("available"):
            nfl_result = nfl_score_exit.check(
                score_info=score_info,
                elapsed_pct=elapsed_pct,
                sport_tag=pos.sport_tag,
            )
            if nfl_result is not None:
                return MonitorResult(
                    exit_signal=ExitSignal(reason=nfl_result.reason, detail=nfl_result.detail),
                    fav_transition=_fav_transition(pos),
                    elapsed_pct=elapsed_pct,
                )
```

**Not:** Bu Task 4'te geçici olarak A-hold dalının içinde. Task 5'te dal yapısı kalkınca bu bloklar tek-dal akışına taşınacak.

- [ ] **Step 4.5: Testler geçmeli**

Run: `pytest tests/unit/strategy/exit/test_monitor.py -v`
Expected: tümü PASS

- [ ] **Step 4.6: Commit**

```bash
git add src/strategy/exit/monitor.py tests/unit/strategy/exit/test_monitor.py
git commit -m "feat(exit): NBA/NFL score exit monitor.py'ye wire edildi"
```

---

## Task 5: Monitor.py Tek-Dal Akışa Dönüşüm (A-hold Kaldırma)

**Files:**
- Modify: `src/strategy/exit/monitor.py`
- Test: `tests/unit/strategy/exit/test_monitor.py` (A-hold testleri silinir, tek-dal testleri eklenir)

- [ ] **Step 5.1: Mevcut A-hold dependent testleri tespit et ve sil**

Grep: `grep -n "a_conf_hold\|A-conf\|a_hold" tests/unit/strategy/exit/test_monitor.py`
Her satırı incele. A-hold branching'e bağlı olanlar silinir (ör. "test_a_conf_hold_branch_skips_graduated_sl").

Kalacak olanlar: near_resolve priority, scale_out priority, score exits, fiyat guard'lar.

- [ ] **Step 5.2: Yeni tek-dal entegrasyon testi ekle**

```python
def test_unified_flow_score_exit_wins_over_never_in_profit() -> None:
    """Score exit öncelikli; never_in_profit gate'i aşılmış olsa bile score önce fire eder."""
    start = datetime.now(timezone.utc) - timedelta(minutes=130)  # 130/150 = 0.87 NBA
    p = _pos(
        sport_tag="nba",
        confidence="B",
        match_start_iso=_iso(start),
        entry_price=0.50,
        current_price=0.20,  # never_in_profit gate tetiklenebilir
        ever_in_profit=False,
    )
    score_info = {"available": True, "deficit": 25}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT


def test_unified_flow_b_conf_hockey_gets_score_exit() -> None:
    """B-conf hokey K1 fire etmeli (A-gate kaldırıldı)."""
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    p = _pos(
        sport_tag="nhl",
        confidence="B",
        match_start_iso=_iso(start),
        current_price=0.40,
    )
    score_info = {"available": True, "deficit": 3}
    r = evaluate(p, score_info=score_info)
    assert r.exit_signal is not None
    assert r.exit_signal.reason == ExitReason.SCORE_EXIT
```

- [ ] **Step 5.3: monitor.py evaluate() fonksiyonunu tek-dal yap**

[monitor.py:192-310](src/strategy/exit/monitor.py#L192-L310) (if a_hold: / else: bloğu) tamamen şöyle yeniden yazılır:

```python
    # 3. Sport-specific score-based exit (tüm pozisyonlar — A-hold ayrımı yok)
    if _is_hockey_family(pos.sport_tag) and score_info.get("available"):
        sc_result = hockey_score_exit.check(
            sport_tag=pos.sport_tag,
            confidence=pos.confidence,
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            current_price=pos.current_price,
        )
        if sc_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=sc_result.reason, detail=sc_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    if _normalize(pos.sport_tag) == "tennis" and score_info.get("available"):
        t_result = tennis_score_exit.check(
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

    if _normalize(pos.sport_tag) in ("mlb", "kbo", "npb", "baseball") and score_info.get("available"):
        b_result = baseball_score_exit.check(
            score_info=score_info,
            current_price=pos.current_price,
            sport_tag=pos.sport_tag,
        )
        if b_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=b_result.reason, detail=b_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    if is_cricket_sport(pos.sport_tag) and score_info.get("available"):
        c_result = cricket_score_exit.check(
            score_info=score_info,
            current_price=pos.current_price,
            sport_tag=pos.sport_tag,
        )
        if c_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=c_result.reason, detail=c_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    if _is_soccer_sport(pos.sport_tag) and score_info.get("available"):
        s_result = soccer_score_exit.check(score_info=score_info, sport_tag=pos.sport_tag)
        if s_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=s_result.reason, detail=s_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
        nba_result = nba_score_exit.check(
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            sport_tag=pos.sport_tag,
        )
        if nba_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=nba_result.reason, detail=nba_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    if _normalize(pos.sport_tag) == "nfl" and score_info.get("available"):
        nfl_result = nfl_score_exit.check(
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            sport_tag=pos.sport_tag,
        )
        if nfl_result is not None:
            return MonitorResult(
                exit_signal=ExitSignal(reason=nfl_result.reason, detail=nfl_result.detail),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    # 4. Market flip — tennis hariç (set kaybı ≠ maç kaybı)
    if _normalize(pos.sport_tag) != "tennis" and elapsed_pct >= 0 and a_conf_hold.market_flip_exit(pos, elapsed_pct):
        return MonitorResult(
            exit_signal=ExitSignal(reason=ExitReason.MARKET_FLIP, detail="eff < 0.50 at elapsed >= 0.85"),
            fav_transition=_fav_transition(pos),
            elapsed_pct=elapsed_pct,
        )

    # 5. Fiyat-tabanlı geç guard'lar (sadece elapsed ≥ 0 ise)
    if elapsed_pct >= 0:
        if _ultra_low_guard_exit(pos, elapsed_pct):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.ULTRA_LOW_GUARD, detail="ultra-low dead"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        if _never_in_profit_exit(pos, elapsed_pct, score_info):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.NEVER_IN_PROFIT, detail="never profited + late + dropped"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )
        if _hold_revocation_exit(pos, elapsed_pct, score_info):
            return MonitorResult(
                exit_signal=ExitSignal(reason=ExitReason.HOLD_REVOKED, detail="hold revoked + exit"),
                fav_transition=_fav_transition(pos),
                elapsed_pct=elapsed_pct,
            )

    # 6. Exit yok — sadece favored transition dön
    return MonitorResult(exit_signal=None, fav_transition=_fav_transition(pos), elapsed_pct=elapsed_pct)
```

**Not:** `catastrophic_watch`, `stop_loss`, `graduated_sl` çağrıları çıkarıldı — Task 7/8/9'da modülleri silinecek. `a_conf_hold.is_a_conf_hold` çağrısı kaldırıldı; sadece `market_flip_exit` kullanılıyor.

Ayrıca monitor.py imports'undan şunları sil: `a_conf_hold, catastrophic_watch, graduated_sl, stop_loss` yerine sadece `a_conf_hold` kalsın (market_flip için). Yani import şöyle kalır:

```python
from src.strategy.exit import a_conf_hold, baseball_score_exit, cricket_score_exit, favored, nba_score_exit, near_resolve, nfl_score_exit, scale_out, hockey_score_exit, soccer_score_exit, tennis_score_exit
```

- [ ] **Step 5.4: Tüm test suite'ini çalıştır**

Run: `pytest tests/unit/strategy/exit/ -v`
Expected: Silinecek modüllerin testleri hala var (Task 7-9'a kadar) ama çağrıları yok — çökebilirler veya skip edilebilirler. `test_catastrophic_watch.py`, `test_stop_loss.py`, `test_graduated_sl.py` hala geçmeli (modülleri silmeden test çalışıyor).

`test_monitor.py` PASS olmalı.

Eğer `test_monitor.py` fail ederse → yeni test case'leri veya akış assertions'ları güncelle.

- [ ] **Step 5.5: Commit**

```bash
git add src/strategy/exit/monitor.py tests/unit/strategy/exit/test_monitor.py
git commit -m "refactor(exit): monitor.py tek-dal akis (A-hold ayrimi kaldirildi)"
```

---

## Task 6: Hockey A-conf Gate'ini Kaldır

**Files:**
- Modify: `src/strategy/exit/hockey_score_exit.py`
- Test: `tests/unit/strategy/exit/test_hockey_score_exit.py`

- [ ] **Step 6.1: B-conf hokey testi ekle**

test_hockey_score_exit.py'ye ekle:

```python
def test_b_conf_hockey_k1_fires_after_a_gate_removed() -> None:
    """A-conf gate kaldırıldı — B-conf hokey de K1 fire etmeli."""
    result = hockey_score_exit.check(
        sport_tag="nhl",
        confidence="B",  # B-conf
        score_info={"available": True, "deficit": 3},
        elapsed_pct=0.30,
        current_price=0.40,
    )
    assert result is not None
    assert "K1" in result.detail
```

- [ ] **Step 6.2: Testi çalıştır, başarısız olmalı**

Run: `pytest tests/unit/strategy/exit/test_hockey_score_exit.py::test_b_conf_hockey_k1_fires_after_a_gate_removed -v`
Expected: FAIL (B-conf şu an None döndürüyor)

- [ ] **Step 6.3: hockey_score_exit.py'dan gate'i sil**

[hockey_score_exit.py:51-52](src/strategy/exit/hockey_score_exit.py#L51-L52):

```python
    if confidence != "A":
        return None
```

Bu iki satırı SİL.

Fonksiyon imzasındaki `confidence: str` parametresi kullanılmıyorsa kaldırılabilir AMA `monitor.py` hala pas geçiyor. Breaking change yapmamak için `confidence` parametresi kalsın; sadece gate silinsin. Docstring'deki "Kapsam: sadece hockey + A-conf" satırını da sil.

- [ ] **Step 6.4: Eski A-conf test'lerini güncelle**

test_hockey_score_exit.py'de `confidence="B"` geçip None bekleyen testler varsa → güncelle (artık fire etmesi gerekiyor) veya sil. Grep: `grep -n "confidence=\"B\"" tests/unit/strategy/exit/test_hockey_score_exit.py`.

- [ ] **Step 6.5: Testler geçmeli**

Run: `pytest tests/unit/strategy/exit/test_hockey_score_exit.py -v`
Expected: tümü PASS

- [ ] **Step 6.6: Commit**

```bash
git add src/strategy/exit/hockey_score_exit.py tests/unit/strategy/exit/test_hockey_score_exit.py
git commit -m "refactor(exit): hockey A-conf gate kaldirildi — tum confidence'lara acik"
```

---

## Task 7: catastrophic_watch Sil + Position Alanları Temizle

**Files:**
- Delete: `src/strategy/exit/catastrophic_watch.py`
- Delete: `tests/unit/strategy/exit/test_catastrophic_watch.py`
- Modify: `src/models/position.py:93-94` (catastrophic_watch + catastrophic_recovery_peak alanları)
- Modify: `config.yaml` (exit_extras.catastrophic_*)

- [ ] **Step 7.1: Regression testi — catastrophic referansı olan her yer**

Run: `pytest tests/ -v -k "catastrophic"`
Not: Şu an geçen/kalan testler yenide sayılır, not al.

Grep: `grep -rn "catastrophic" src/ tests/`
Her sonucu listele; hepsi Task 7'de temizlenecek.

- [ ] **Step 7.2: Modül + testi sil**

```bash
rm src/strategy/exit/catastrophic_watch.py
rm tests/unit/strategy/exit/test_catastrophic_watch.py
```

- [ ] **Step 7.3: Position modelinden alanları sil**

[position.py:93-94](src/models/position.py#L93-L94):

```python
    catastrophic_watch: bool = False
    catastrophic_recovery_peak: float = 0.0
```

Bu iki satırı SİL.

- [ ] **Step 7.4: config.yaml'dan catastrophic alanlarını sil**

Grep ile bul: `grep -n "catastrophic" config.yaml`
Bu anahtarları içeren tüm satırları sil. `exit_extras.catastrophic_*` altındaki key'ler (trigger, drop_pct, cancel gibi) silinir.

- [ ] **Step 7.5: ExitExtrasConfig tipinden catastrophic field'ları sil**

Grep: `grep -rn "catastrophic" src/config/`
Genelde `src/config/settings.py` içinde `CatastrophicConfig` veya benzeri. Alan tamamen silinir.

- [ ] **Step 7.6: monitor.py imzasından catastrophic_config parametresini kaldır**

[monitor.py:137](src/strategy/exit/monitor.py#L137) benzeri satırda `catastrophic_config: dict | None = None` parametresi varsa sil. `cat_cfg`, `cat_trigger`, `cat_drop`, `cat_cancel` local variable'ları da silinir (Task 5'te block zaten gitmişti).

- [ ] **Step 7.7: Çağrı yerlerinden catastrophic_config pas geçişleri sil**

Grep: `grep -rn "catastrophic_config" src/`
Orchestration katmanında factory.py veya cycle_manager.py'de pas geçiyor olabilir. Silinir.

- [ ] **Step 7.8: Testleri çalıştır**

Run: `pytest -q`
Expected: tümü PASS (catastrophic referansı kalmamalı)

- [ ] **Step 7.9: Grep verification**

Run: `grep -rn "catastrophic" src/ tests/`
Expected: 0 sonuç

- [ ] **Step 7.10: Commit**

```bash
git add -u
git commit -m "refactor(exit): catastrophic_watch silindi (A3 spec)"
```

---

## Task 8: stop_loss Sil

**Files:**
- Delete: `src/strategy/exit/stop_loss.py`
- Delete: `tests/unit/strategy/exit/test_stop_loss.py`
- Modify: `src/config/sport_rules.py` (tüm sporlardan `stop_loss_pct`)
- Modify: `src/config/settings.py:52` (default stop_loss_pct)

- [ ] **Step 8.1: Grep referansları**

Run: `grep -rn "stop_loss\|StopLoss\|STOP_LOSS" src/ tests/`
Expected: stop_loss.py + testi + sport_rules.py + settings.py + enums.py (enum silme Task 15'te).

- [ ] **Step 8.2: Modülü ve testini sil**

```bash
rm src/strategy/exit/stop_loss.py
rm tests/unit/strategy/exit/test_stop_loss.py
```

- [ ] **Step 8.3: sport_rules.py'dan `stop_loss_pct` her yerde sil**

Grep: `grep -n "stop_loss_pct" src/config/sport_rules.py`
Her sport dict'inden bu satırı çıkar. `get_stop_loss` fonksiyonunu da silmek gerekiyorsa kontrol et:

Grep: `grep -rn "get_stop_loss" src/`
Eğer sadece stop_loss.py kullanıyordu → sil; başka yerde kullanılıyorsa önce o çağrıyı düzelt.

- [ ] **Step 8.4: settings.py'dan default stop_loss_pct'i sil**

[src/config/settings.py:52](src/config/settings.py#L52):

```python
    stop_loss_pct: float = 0.30
```

Bu satırı sil. Eğer bu değer başka bir dataclass field'ı ise onu da sadeleştir.

- [ ] **Step 8.5: Testler geçmeli**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 8.6: Grep verification**

Run: `grep -rn "stop_loss" src/ tests/`
Expected: sadece enum (`STOP_LOSS = "stop_loss"` — Task 15'te silinecek) ve display label (Task 16'da silinecek) kalır.

- [ ] **Step 8.7: Commit**

```bash
git add -u
git commit -m "refactor(exit): stop_loss modulu silindi (A3 spec)"
```

---

## Task 9: graduated_sl Sil

**Files:**
- Delete: `src/strategy/exit/graduated_sl.py`
- Delete: `tests/unit/strategy/exit/test_graduated_sl.py`

- [ ] **Step 9.1: Grep referansları**

Run: `grep -rn "graduated_sl\|GraduatedSL\|GRADUATED_SL" src/ tests/`
Expected: modül + test + monitor.py (Task 5'te çağrı silinmişti) + enums.py.

- [ ] **Step 9.2: Modülü ve testini sil**

```bash
rm src/strategy/exit/graduated_sl.py
rm tests/unit/strategy/exit/test_graduated_sl.py
```

- [ ] **Step 9.3: Testler geçmeli**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 9.4: Grep verification**

Run: `grep -rn "graduated_sl" src/ tests/`
Expected: sadece enum `GRADUATED_SL` (Task 15) + JS label (Task 16) kalır.

- [ ] **Step 9.5: Commit**

```bash
git add -u
git commit -m "refactor(exit): graduated_sl modulu silindi (A3 spec)"
```

---

## Task 10: is_a_conf_hold Fonksiyonunu Sil

**Files:**
- Modify: `src/strategy/exit/a_conf_hold.py` (sadece `market_flip_exit` ve sabitler kalır)
- Modify: `tests/unit/strategy/exit/test_a_conf_hold.py` (is_a_conf_hold testleri silinir)

- [ ] **Step 10.1: Grep referansları**

Run: `grep -rn "is_a_conf_hold" src/ tests/`
Expected: a_conf_hold.py tanımı + test + belki factory.py.

- [ ] **Step 10.2: Fonksiyonu sil**

[a_conf_hold.py:26-29](src/strategy/exit/a_conf_hold.py#L26-L29):

```python
def is_a_conf_hold(pos: Position, min_entry_price: float = DEFAULT_MIN_ENTRY_PRICE) -> bool:
    """Pozisyon A-conf strong-entry hold'a tabi mi?"""
    return pos.confidence == "A" and pos.entry_price >= min_entry_price
```

Bu fonksiyonu tamamen SİL. Ayrıca `DEFAULT_MIN_ENTRY_PRICE = 0.60` sabitini da sil (sadece bu fonksiyon kullanıyordu).

Dosyanın docstring'ini güncelle — artık sadece market_flip_exit barındırıyor:

```python
"""Market-flip exit (TDD §6.9 — A3 sonrası sadeleşmiş).

Market flip rule (elapsed ≥ 85%):
  effective_current < 0.50 → çık (market artık tarafımızda değil)

v1 verisi: 25 A-conf resolved trade → market_flip kural $110.78 tasarruf etti.
Elapsed gate eklenmesi early-match false positive'leri elediği için zorunlu.
"""
```

- [ ] **Step 10.3: Testlerden is_a_conf_hold testleri sil**

test_a_conf_hold.py'de `is_a_conf_hold` içeren her testi sil. `market_flip_exit` testleri kalır.

- [ ] **Step 10.4: Testler geçmeli**

Run: `pytest tests/unit/strategy/exit/test_a_conf_hold.py -v`
Expected: market_flip_exit testleri PASS

Run: `pytest -q`
Expected: tüm suite PASS

- [ ] **Step 10.5: Commit**

```bash
git add -u
git commit -m "refactor(exit): is_a_conf_hold fonksiyonu silindi (A3 tek-dal)"
```

---

## Task 11: Config Ölü Anahtarları Temizle (halftime_exit / period_exit / inning_exit / set_exit flag'leri)

**Files:**
- Modify: `src/config/sport_rules.py`
- Test: `tests/unit/config/test_sport_rules.py` (ölü key'lere referansları sil)

- [ ] **Step 11.1: NBA'dan halftime_exit flag + deficit sil**

```python
    "nba": {
        # halftime_exit: True         ← SİL
        # halftime_exit_deficit: 15   ← SİL
        ...
    },
```

- [ ] **Step 11.2: NFL'den halftime_exit flag + deficit sil**

Aynı şekilde.

- [ ] **Step 11.3: NHL'den period_exit boolean flag sil**

```python
    "nhl": {
        # period_exit: True   ← SİL
        "period_exit_deficit": 3,  # ← KALIR (hockey_score_exit kullanır)
        ...
    },
```

- [ ] **Step 11.4: MLB'den eski inning_exit key'lerini sil**

```python
    "mlb": {
        # inning_exit: True               ← SİL
        # inning_exit_deficit: 5          ← SİL
        # inning_exit_after: 6            ← SİL
        "score_exit_m1_inning": 7,  # ← KALIR
        ...
    },
```

- [ ] **Step 11.5: Tennis'ten set_exit boolean flag sil**

```python
    "tennis": {
        # set_exit: True    ← SİL
        "set_exit_deficit": 3,  # ← KALIR (tennis_score_exit kullanır)
        ...
    },
```

- [ ] **Step 11.6: Testlerden ölü key'lere referansları sil**

test_sport_rules.py'de eski key'leri test eden satırlar varsa sil (grep ile bul).

- [ ] **Step 11.7: Testler geçmeli**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 11.8: Grep verification**

Run: `grep -rn "halftime_exit" src/`
Expected: 0 sonuç

Run: `grep -rnE "\"period_exit\":|\"inning_exit\":|\"set_exit\":" src/`
Expected: 0 sonuç (sub-key'ler gibi `period_exit_deficit` kalmalı)

- [ ] **Step 11.9: Commit**

```bash
git add -u
git commit -m "refactor(config): olu sport flag key'leri silindi (halftime_exit/period_exit/inning_exit/set_exit)"
```

---

## Task 12: MMA ve Golf MVP'den Çıkar (sport_rules'dan Sil)

**Files:**
- Modify: `src/config/sport_rules.py` (mma + golf entry'leri silinir)
- Test: `tests/unit/config/test_sport_rules.py` (regression)

- [ ] **Step 12.1: Grep kontrolü — MMA/Golf referansları**

Run: `grep -rn "\"mma\"\|\"golf\"" src/`
Expected: sport_rules.py dışında varsa Task 14'te entry gate'te ele alacağız.

- [ ] **Step 12.2: sport_rules.py'dan MMA entry'sini sil**

```python
    "mma": {
        ...
    },
```

Tamamen sil.

- [ ] **Step 12.3: sport_rules.py'dan Golf entry'sini sil**

Aynı şekilde.

- [ ] **Step 12.4: Testler geçmeli**

Run: `pytest tests/unit/config/test_sport_rules.py -v`
Expected: PASS (MMA/Golf testleri yoksa veya silindiyse)

Eğer test varsa:
```python
def test_mma_sport_rule() -> None:
    ...
```
Sil.

- [ ] **Step 12.5: Commit**

```bash
git add -u
git commit -m "refactor(sports): MMA + Golf MVP'den cikarildi (A3 spec, TODO'ya eklenecek)"
```

---

## Task 13: Entry Gate'te MMA + Golf Reject

**Files:**
- Modify: `src/strategy/entry/gate.py`
- Test: `tests/unit/strategy/entry/test_gate.py` (yeni test)

- [ ] **Step 13.1: Failing test yaz**

tests/unit/strategy/entry/test_gate.py'ye ekle (veya yeni test dosyası):

```python
def test_mma_market_rejected_with_sport_not_in_mvp_reason() -> None:
    """MMA pozisyonu entry gate'te reddedilmeli."""
    # Test setup: MMA sport_tag'li MarketData oluştur
    # Expected: Signal is None (skip) veya signal.reason == "sport_not_in_mvp"
    ...  # Testin projenin mevcut gate test pattern'ine uygun yazılması gerekir
    # Grep: grep -n "def test_" tests/unit/strategy/entry/test_gate.py
    # Mevcut bir skip test case'ini kopyalayıp sport_tag="mma" yap

def test_golf_market_rejected_with_sport_not_in_mvp_reason() -> None:
    """Golf pozisyonu entry gate'te reddedilmeli."""
    ...
```

- [ ] **Step 13.2: Testi çalıştır, başarısız olmalı**

Run: `pytest tests/unit/strategy/entry/test_gate.py -v -k "mma or golf"`
Expected: FAIL

- [ ] **Step 13.3: gate.py'ye MMA + Golf reject eklensin**

[gate.py](src/strategy/entry/gate.py) içinde — pipeline'ın başında (event_guard'dan sonra, sport-specific logic'ten önce). Önce `_NON_MVP_SPORTS` sabiti ekle:

```python
# MVP dışı sporlar — entry gate'te reddedilir (TODO-002, TODO-003)
_NON_MVP_SPORTS: frozenset[str] = frozenset({"mma", "golf"})
```

Sonra gate pipeline'ında uygun yere ekle (sport_tag normalize sonrası, directional/three_way'den önce):

```python
        from src.config.sport_rules import _normalize
        if _normalize(market.sport_tag) in _NON_MVP_SPORTS:
            logger.info(f"[skip] {market.slug} — sport_not_in_mvp ({market.sport_tag})")
            # mevcut skip logging/stats mekanizmasıyla uyumlu şekilde
            # skipped_trades.jsonl'e "sport_not_in_mvp" reason ile yaz
            return Signal(...)  # projenin mevcut skip Signal pattern'i
```

**Not:** Gate'in gerçek skip mekanizmasını (Signal vs None) bilmeden buraya kesin kod yazmak zor. Executor bu task'ta gate.py'nin mevcut skip path'ini incelemeli ve aynı pattern'i kullanmalı.

- [ ] **Step 13.4: Testler geçmeli**

Run: `pytest tests/unit/strategy/entry/test_gate.py -v`
Expected: PASS

- [ ] **Step 13.5: Commit**

```bash
git add -u
git commit -m "feat(entry): MMA + Golf entry reject (sport_not_in_mvp)"
```

---

## Task 14: ExitReason Enum'undan Ölü Değerleri Sil

**Files:**
- Modify: `src/models/enums.py`
- Modify: `tests/unit/models/test_enums.py`

- [ ] **Step 14.1: Grep referansları — silinen enum değerler başka kodda kullanılıyor mu?**

Run: `grep -rn "ExitReason\.STOP_LOSS\|ExitReason\.GRADUATED_SL\|ExitReason\.CIRCUIT_BREAKER\|ExitReason\.MANUAL\|ExitReason\.CATASTROPHIC_BOUNCE" src/ tests/`
Expected: sadece enum tanımı + belki JSONL okuma/yazma (string-based olmalı).

Eğer aktif çağrı yeri varsa o çağrıyı önce düzelt.

- [ ] **Step 14.2: Enum'dan sil**

[enums.py:26-38](src/models/enums.py#L26-L38):

```python
class ExitReason(str, Enum):
    SCALE_OUT = "scale_out"
    NEVER_IN_PROFIT = "never_in_profit"
    MARKET_FLIP = "market_flip"
    NEAR_RESOLVE = "near_resolve"
    HOLD_REVOKED = "hold_revoked"
    ULTRA_LOW_GUARD = "ultra_low_guard"
    SCORE_EXIT = "score_exit"
```

Silinenler: `STOP_LOSS`, `GRADUATED_SL`, `CIRCUIT_BREAKER`, `MANUAL`, `CATASTROPHIC_BOUNCE`.

- [ ] **Step 14.3: test_enums.py'deki silinen değerlere referansları sil**

Grep: `grep -n "STOP_LOSS\|GRADUATED_SL\|CIRCUIT_BREAKER\|MANUAL\|CATASTROPHIC_BOUNCE" tests/unit/models/test_enums.py`
Her satırı güncelle/sil.

- [ ] **Step 14.4: Testler geçmeli**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 14.5: Commit**

```bash
git add -u
git commit -m "refactor(enums): olu ExitReason degerleri silindi (STOP_LOSS/GRADUATED_SL/CIRCUIT_BREAKER/MANUAL/CATASTROPHIC_BOUNCE)"
```

---

## Task 15: Frontend JS Display Label'larını Temizle

**Files:**
- Modify: `src/presentation/dashboard/static/js/trade_history_modal.js`

- [ ] **Step 15.1: Dosyayı oku ve silinen reason'lara referansları bul**

Grep: `grep -n "stop_loss\|graduated_sl\|circuit_breaker\|manual\|catastrophic_bounce" src/presentation/dashboard/static/js/trade_history_modal.js`

Her satır bir display label mapping'idir. Örnek:
```javascript
{ stop_loss: "Stop Loss", graduated_sl: "Graduated SL", ... }
```

- [ ] **Step 15.2: Bu key'leri label haritasından sil**

Label objesinden sadece `stop_loss`, `graduated_sl`, `circuit_breaker`, `manual`, `catastrophic_bounce` key'lerini kaldır. Diğerleri kalır.

- [ ] **Step 15.3: Manuel browser testi**

Dashboard'u aç → trade history modal'ı aç → birkaç eski trade'in exit reason'ı görünüyor mu (SCORE_EXIT, SCALE_OUT, MARKET_FLIP vb.)?
**Expected:** Silinen reason'lı eski kayıt varsa raw string görünür ("graduated_sl" olarak), nice label değil. Bu kabul edilebilir (historical, yeni kayıt üretilmiyor).

- [ ] **Step 15.4: Commit**

```bash
git add src/presentation/dashboard/static/js/trade_history_modal.js
git commit -m "refactor(dashboard): olu exit reason JS label'lari silindi"
```

---

## Task 16: Monitor.py Docstring + Scale-Out Drift Fix

**Files:**
- Modify: `src/strategy/exit/monitor.py:1-13`

- [ ] **Step 16.1: monitor.py docstring'ini yeniden yaz**

Mevcut docstring A-hold yapısını anlatıyor (drift). Yerine:

```python
"""Exit orchestrator — tüm exit guard'larını koordine eder (A3 sadeleşmiş).

Öncelik zinciri (ilk tetiklenen kazanır):
  1. Near-resolve profit (eff ≥ 94¢)        — en yüksek öncelik, kâr lock
  2. Scale-out (tek tier: entry→0.99 yolun %50'si, %40 sat) — kısmi exit
  3. Sport-specific score exit (hockey/tennis/baseball/cricket/soccer/nba/nfl)
  4. Market flip (tennis hariç, elapsed ≥85% + eff<50¢)
  5. Fiyat-tabanlı geç guard'lar (ultra_low / never_in_profit / hold_revoked)
  6. FAV promote/demote — sadece state güncellemesi, exit değil

Pure: pos + elapsed_pct + score_info dışarıdan verilir.
"""
```

- [ ] **Step 16.2: Testler geçmeli**

Run: `pytest tests/unit/strategy/exit/test_monitor.py -v`
Expected: PASS (docstring değişimi kod davranışını etkilemez)

- [ ] **Step 16.3: Commit**

```bash
git add src/strategy/exit/monitor.py
git commit -m "docs(monitor): A3 sonrasi docstring guncellendi (scale-out drift fix dahil)"
```

---

## Task 17: TDD.md Güncelleme

**Files:**
- Modify: `TDD.md`

- [ ] **Step 17.1: §6.8 (graduated SL) bölümünü sil**

Grep: `grep -n "6\.8\|graduated_sl\|graduated SL" TDD.md`
Bölüm başından sonraki bölüm başına kadar olan içeriği sil.

- [ ] **Step 17.2: §6.9 (A-conf hold) bölümünü sadeleştir**

Mevcut §6.9 hem `is_a_conf_hold` hem `market_flip_exit` anlatıyor. Şöyle yap:
- `is_a_conf_hold` ve bağlı davranış paragraflarını sil
- `market_flip_exit` kısmı kalır
- Bölüm başlığını "§6.9 — Market Flip Exit" olarak güncelle

- [ ] **Step 17.3: §7.1 / §7.2 MVP spor kapsamını güncelle**

Grep: `grep -n "mma\|golf" TDD.md`
MMA ve Golf'ü tablolardan/listelerden çıkar. Yerine not: "MMA ve Golf TODO-002 / TODO-003 altında ele alınacak."

NBA + NFL için score exit bölümü ekle (hockey §7.2 ile simetrik):

```markdown
### §7.2.X — NBA Score Exit (A3)

- N1: elapsed ≥ 0.75 + deficit ≥ 20 (Q3 sonu + ağır fark)
- N2: elapsed ≥ 0.92 + deficit ≥ 10 (son dakikalar + 2 possession)

Threshold'lar sport_rules.py'den okunur.

### §7.2.Y — NFL Score Exit (A3)

- N1: elapsed ≥ 0.75 + deficit ≥ 21 (3-skor farkı)
- N2: elapsed ≥ 0.92 + deficit ≥ 11 (2-possession, son 5dk)
```

- [ ] **Step 17.4: SPEC-004 K5 (catastrophic_watch) referanslarını sil**

Grep: `grep -n "K5\|catastrophic_watch\|SPEC-004 K5" TDD.md`
Referansları temizle / not olarak "SPEC-004 K5 kaldırıldı (A3 spec)" ekle.

- [ ] **Step 17.5: Commit**

```bash
git add TDD.md
git commit -m "docs(tdd): A3 spec uyumu — graduated_sl/A-conf hold/catastrophic_watch silindi, NBA/NFL score exit eklendi"
```

---

## Task 18: TODO.md'ye TODO-002 + TODO-003 Ekle

**Files:**
- Modify: `TODO.md`

- [ ] **Step 18.1: TODO-001'in altına ekle**

```markdown
---

## TODO-002: MMA / UFC Skor-Tabanlı Exit Kuralları

- **Durum**: DEFERRED
- **Tarih**: 2026-04-20
- **Sebep**: MMA'da canlı skor sistemi yok; judge decision maç sonunda gelir.
  Round-by-round kontrol data var mı araştırılmalı (ESPN MMA endpoint, alternatif provider).
- **Önkoşul**: Canlı skor source bulunmalı. ESPN MMA ham veride round winner,
  strike count, control time gibi field'lar incelenmeli.
- **Öncelik**: P2 (MVP stabil olduktan sonra)
- **Mevcut durum**: MMA entry gate'te "sport_not_in_mvp" reason ile reddediliyor.
  sport_rules.py'dan entry silindi.

## TODO-003: Golf Skor-Tabanlı Exit Kuralları

- **Durum**: DEFERRED
- **Tarih**: 2026-04-20
- **Sebep**: ESPN golf canlı leaderboard endpoint'i yok.
- **Önkoşul**: Canlı leaderboard provider araştırılmalı (alternatif: PGA.com, Golf Channel API).
  Playoff-aware config (ham veride hole-by-hole data) gerekli.
- **Öncelik**: P3 (niş spor, volume düşük)
- **Mevcut durum**: Golf entry gate'te "sport_not_in_mvp" reason ile reddediliyor.
  sport_rules.py'dan entry silindi.
```

- [ ] **Step 18.2: Commit**

```bash
git add TODO.md
git commit -m "docs(todo): TODO-002 (MMA) + TODO-003 (Golf) eklendi (A3 spec sonrasi)"
```

---

## Task 19: Final Test Regression + Grep Drift Verification

**Files:** Yok (sadece doğrulama)

- [ ] **Step 19.1: Tüm test suite**

Run: `pytest -q`
Expected: tümü PASS

- [ ] **Step 19.2: Coverage kontrolü**

Run: `pytest --cov=src --cov-report=term-missing`
Expected: Strategy katmanı ≥ %75 (ARCH Kural 15). NBA/NFL exit modülleri ≥ %90 (yeni + test-driven).

- [ ] **Step 19.3: Grep drift verification**

Her biri 0 sonuç vermelidir:

```bash
grep -rn "stop_loss" src/                    # enum dışı 0
grep -rn "graduated_sl" src/                 # enum dışı 0 — artık enum da yok
grep -rn "catastrophic" src/ tests/          # 0
grep -rn "is_a_conf_hold" src/               # 0
grep -rnE "\"halftime_exit\"\|\"period_exit\":\|\"inning_exit\":\|\"set_exit\":" src/config/  # 0
grep -rn "\"mma\"\|\"golf\"" src/config/sport_rules.py  # 0
grep -rn "ExitReason\.STOP_LOSS\|ExitReason\.GRADUATED_SL\|ExitReason\.CIRCUIT_BREAKER\|ExitReason\.MANUAL\|ExitReason\.CATASTROPHIC_BOUNCE" src/  # 0
```

Eğer herhangi bir grep sonuç verirse → o noktayı incele, gerçekten artık mı yoksa kaçırılmış mı karar ver.

- [ ] **Step 19.4: Architecture guard doğrulama**

Her yeni dosyayı wc ile ölç:
```bash
wc -l src/strategy/exit/nba_score_exit.py src/strategy/exit/nfl_score_exit.py
```
Expected: her ikisi de < 100 satır (400 limit'ten çok uzak ✓)

- [ ] **Step 19.5: Bot smoke test (opsiyonel ama tavsiye)**

Bot'u kısa süre çalıştır (örn. dry-run veya canlı):
- Entry gate MMA/Golf market'i reddediyor mu? (log'da "sport_not_in_mvp" görünmeli)
- Exit monitor yeni akışla hata veriyor mu?
- Dashboard açılıyor mu, trade history yükleniyor mu?

- [ ] **Step 19.6: Spec dosyasından DRAFT → IMPLEMENTED işaretle**

Modify: `docs/superpowers/specs/2026-04-20-score-only-exits-design.md`

Header'ı güncelle:
```markdown
**Durum:** IMPLEMENTED (2026-04-XX)
```

- [ ] **Step 19.7: Commit final**

```bash
git add docs/superpowers/specs/2026-04-20-score-only-exits-design.md
git commit -m "docs(spec): A3 score-only exits IMPLEMENTED isaretledi"
```

---

## Kapanış

Plan 19 task'tan oluşuyor. Tahmini süre: 4-6 saat (her task ~15-25 dk, test yazma + uygulama + commit).

Her task kendi başına çalışan bir değişiklik bırakır; ara commit'lerde bot'u smoke-test edebilirsin.

**Kritik noktalar:**
- Task 5 (monitor.py unification) en büyük adım — dikkatli çalıştır, test'i gözlemle
- Task 7-9 silme sırası: önce catastrophic (en izole), sonra stop_loss, sonra graduated_sl
- Task 13 (gate.py) mevcut skip pattern'ini taklit etmeli — executor önce gate.py'nin mevcut akışını oku
- Task 17 (TDD.md) uzun sürebilir — titizce grep yaparak her referansı bul
