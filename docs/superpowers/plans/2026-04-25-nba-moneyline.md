# NBA Moneyline Entry + Exit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NBA moneyline için gap-based entry gate ve score-based exit (Bill James + empirical) implementasyonu.

**Architecture:**
- `src/domain/math/safe_lead.py` — saf matematik, I/O yok
- `src/strategy/exit/nba_score_exit.py` — score_info + period/clock → NbaCheckResult | None
- `src/strategy/entry/gate.py` — gap filtresi + sizing + event guard
- `src/config/settings.py` + `config.yaml` + `DECISIONS.md` drift güncellemesi

**Mimari notlar:**
- nba_score_exit.check() sadece MATH_DEAD / EMPIRICAL_DEAD / OT_DEAD / HOLD / STRUCTURAL_DAMAGE implement eder.
  Near-resolve (94¢) ve scale-out (85¢) monitor.py priority 1-2'de zaten var — tekrar yok.
- Score exit → ExitReason.SCORE_EXIT kullanır, detail string ayrıştırıcı.
- is_mathematically_dead() → multiplier dışarıdan parametre; domain I/O almaz.

**Tech Stack:** Python 3.12, dataclasses, Pydantic v2, pytest

---

## File Map

| Dosya | İşlem | Açıklama |
|---|---|---|
| `src/domain/math/__init__.py` | Oluştur | Boş init |
| `src/domain/math/safe_lead.py` | Oluştur | Bill James formülü |
| `tests/unit/domain/math/__init__.py` | Oluştur | Boş init |
| `tests/unit/domain/math/test_safe_lead.py` | Oluştur | 7 test |
| `config.yaml` | Güncelle | exit_basketball + entry yeni alanlar |
| `src/config/settings.py` | Güncelle | BasketballExitConfig + EntryConfig yeni alanlar |
| `src/strategy/exit/nba_score_exit.py` | Doldur | Tam implementasyon |
| `src/strategy/exit/monitor.py` | Güncelle | nba check çağrısına bid_price + entry_price ekle |
| `tests/unit/strategy/exit/test_nba_score_exit.py` | Oluştur | 9 test |
| `src/strategy/entry/gate.py` | Doldur | Gap-based entry + event guard |
| `tests/unit/strategy/entry/test_gate.py` | Güncelle | Stub testleri → gerçek logic testleri |
| `src/orchestration/factory.py` | Güncelle | GateConfig yeni alanlar |
| `DECISIONS.md` | Güncelle | NBA Moneyline section |

---

## Task 1: src/domain/math/ — Bill James safe_lead (TDD)

**Files:**
- Create: `src/domain/math/__init__.py`
- Create: `src/domain/math/safe_lead.py`
- Create: `tests/unit/domain/math/__init__.py`
- Create: `tests/unit/domain/math/test_safe_lead.py`

- [ ] **Step 1: Boş __init__ dosyaları yaz**

`src/domain/math/__init__.py` — boş.
`tests/unit/domain/math/__init__.py` — boş.

- [ ] **Step 2: Failing testleri yaz**

`tests/unit/domain/math/test_safe_lead.py`:

```python
"""is_mathematically_dead() unit testleri."""
from __future__ import annotations

import pytest
from src.domain.math.safe_lead import is_mathematically_dead

_M = 0.861  # NBA default multiplier


def test_dead_17_pts_240s():
    # 0.861 * sqrt(240) = 13.33 → 17 >= 13.33 → True
    assert is_mathematically_dead(deficit=17, clock_seconds=240, multiplier=_M) is True


def test_dead_13_pts_120s():
    # 0.861 * sqrt(120) = 9.43 → 13 >= 9.43 → True
    assert is_mathematically_dead(deficit=13, clock_seconds=120, multiplier=_M) is True


def test_dead_8_pts_45s():
    # 0.861 * sqrt(45) = 5.77 → 8 >= 5.77 → True
    assert is_mathematically_dead(deficit=8, clock_seconds=45, multiplier=_M) is True


def test_dead_25_pts_420s():
    # 0.861 * sqrt(420) = 17.64 → 25 >= 17.64 → True
    assert is_mathematically_dead(deficit=25, clock_seconds=420, multiplier=_M) is True


def test_alive_5_pts_240s():
    # 0.861 * sqrt(240) = 13.33 → 5 < 13.33 → False
    assert is_mathematically_dead(deficit=5, clock_seconds=240, multiplier=_M) is False


def test_zero_seconds_positive_deficit():
    # clock = 0, deficit > 0 → oyun bitti, gerideyiz → True
    assert is_mathematically_dead(deficit=1, clock_seconds=0, multiplier=_M) is True


def test_negative_deficit_is_alive():
    # Negatif deficit = biz öndeyiz → False
    assert is_mathematically_dead(deficit=-5, clock_seconds=120, multiplier=_M) is False
```

- [ ] **Step 3: Testi çalıştır — FAIL beklenir**

```
pytest tests/unit/domain/math/test_safe_lead.py -v
```
Beklenen: `ModuleNotFoundError` veya `ImportError`.

- [ ] **Step 4: Implementasyonu yaz**

`src/domain/math/safe_lead.py`:

```python
"""Bill James %99 safe lead formülü — NBA için kalibre."""
from __future__ import annotations

from math import sqrt


def is_mathematically_dead(
    deficit: int,
    clock_seconds: int,
    multiplier: float,
) -> bool:
    """Geri dönüşü matematiksel olarak imkânsız mı?

    deficit >= multiplier * sqrt(clock_seconds) → evet.
    deficit negatifse (biz öndeyiz) → False.
    """
    if deficit <= 0:
        return False
    if clock_seconds <= 0:
        return deficit > 0
    return deficit >= multiplier * sqrt(clock_seconds)
```

- [ ] **Step 5: Testleri çalıştır — PASS beklenir**

```
pytest tests/unit/domain/math/test_safe_lead.py -v
```
Beklenen: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add src/domain/math/__init__.py src/domain/math/safe_lead.py \
        tests/unit/domain/math/__init__.py tests/unit/domain/math/test_safe_lead.py
git commit -m "feat(domain/math): Bill James safe_lead — is_mathematically_dead, 7 tests"
```

---

## Task 2: config.yaml + settings.py güncellemesi

**Files:**
- Modify: `config.yaml`
- Modify: `src/config/settings.py`

- [ ] **Step 1: settings.py'e yeni config sınıfları ekle**

`src/config/settings.py`'de `EntryConfig`'ten ÖNCE şu sınıfları ekle:

```python
class EmpiricalExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q4_blowout_seconds: int = 720
    q4_blowout_deficit: int = 20
    q4_late_seconds: int = 360
    q4_late_deficit: int = 15
    q4_final_seconds: int = 180
    q4_final_deficit: int = 10
    q4_endgame_seconds: int = 60
    q4_endgame_deficit: int = 6


class OvertimeExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    seconds: int = 60
    deficit: int = 8


class BasketballExitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    bill_james_multiplier: float = 0.861
    structural_damage_ratio: float = 0.30
    empirical: EmpiricalExitConfig = EmpiricalExitConfig()
    overtime: OvertimeExitConfig = OvertimeExitConfig()
```

- [ ] **Step 2: EntryConfig'e yeni alanlar ekle**

Mevcut `EntryConfig`'i şu alanlarla genişlet (extra="ignore" sayesinde eski testler kırılmaz):

```python
class EntryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_favorite_probability: float = 0.60
    max_entry_price: float = 0.80
    min_bookmakers: int = 15
    min_sharps: int = 3
    active_sports: List[str] = []
    # Gap thresholds
    min_gap_threshold: float = 0.08
    gap_high_zone: float = 0.15
    gap_extreme_zone: float = 0.25
    # Filters
    min_polymarket_price: float = 0.15
    min_market_volume: float = 5000.0
    max_match_start_hours: float = 6.0
    # Sizing
    confidence_a_pct: float = 0.05
    confidence_b_pct: float = 0.03
    high_gap_multiplier: float = 1.2
    extreme_gap_multiplier: float = 1.3
    min_bet_usd: float = 5.0
```

- [ ] **Step 3: AppConfig'e exit_basketball ekle**

`AppConfig` sınıfına şu satırı ekle (sl: SLConfig satırından sonra):

```python
exit_basketball: BasketballExitConfig = BasketballExitConfig()
```

- [ ] **Step 4: config.yaml'a yeni section'ları ekle**

`config.yaml`'daki `entry:` bloğunu şu şekilde genişlet (mevcut alanları koru):

```yaml
entry:
  min_favorite_probability: 0.60
  max_entry_price: 0.80
  min_bookmakers: 15
  min_sharps: 3
  active_sports: []                     # Task 6'da basketball_nba eklenir
  min_gap_threshold: 0.08
  gap_high_zone: 0.15
  gap_extreme_zone: 0.25
  min_polymarket_price: 0.15
  min_market_volume: 5000.0
  max_match_start_hours: 6.0
  confidence_a_pct: 0.05
  confidence_b_pct: 0.03
  high_gap_multiplier: 1.2
  extreme_gap_multiplier: 1.3
  min_bet_usd: 5.0
```

`config.yaml`'a yeni top-level section (favored: section'ından sonra) ekle:

```yaml
exit_basketball:
  bill_james_multiplier: 0.861
  structural_damage_ratio: 0.30
  empirical:
    q4_blowout_seconds: 720
    q4_blowout_deficit: 20
    q4_late_seconds: 360
    q4_late_deficit: 15
    q4_final_seconds: 180
    q4_final_deficit: 10
    q4_endgame_seconds: 60
    q4_endgame_deficit: 6
  overtime:
    seconds: 60
    deficit: 8
```

- [ ] **Step 5: Mevcut testleri çalıştır — kırılmamalı**

```
pytest -q
```
Beklenen: 833 passed.

- [ ] **Step 6: Commit**

```bash
git add config.yaml src/config/settings.py
git commit -m "feat(config): BasketballExitConfig + EntryConfig gap/filter/sizing alanları"
```

---

## Task 3: nba_score_exit.py — tam implementasyon

**Files:**
- Modify: `src/strategy/exit/nba_score_exit.py`
- Modify: `src/strategy/exit/monitor.py` (satır 279-289 — nba check çağrısı)

**Mimari:**
- `NbaCheckResult` → `@dataclass(reason: ExitReason, detail: str)` — monitor bunu ExitSignal'a sarar
- `check()` → sadece score-based exit: MATH_DEAD, EMPIRICAL, OT_DEAD, Q1-Q3 HOLD, STRUCTURAL_DAMAGE
- Near-resolve (94¢) ve scale-out (85¢) → monitor.py'de priority 1-2'de zaten aktif; tekrar YOK

**Deficit yönü:** `score_info["deficit"] = opp_score - our_score` zaten direction-adjusted.
  Pozitif = biz gerideyiz, negatif = biz öndeyiz. (build_score_info() bunu halleder)

- [ ] **Step 1: Failing testleri yaz**

`tests/unit/strategy/exit/test_nba_score_exit.py`:

```python
"""nba_score_exit.check() unit testleri."""
from __future__ import annotations

import pytest
from src.strategy.exit.nba_score_exit import check
from src.models.enums import ExitReason


def _si(
    period_number: int = 4,
    clock_seconds: int = 300,
    deficit: int = 10,
    available: bool = True,
) -> dict:
    return {
        "available": available,
        "period_number": period_number,
        "clock_seconds": clock_seconds,
        "deficit": deficit,
        "our_score": 90,
        "opp_score": 90 + deficit,
    }


_M = 0.861


def test_period_3_always_hold():
    """Q1-Q3'te skor ne olursa olsun HOLD."""
    result = check(
        score_info=_si(period_number=3, clock_seconds=60, deficit=20),
        elapsed_pct=0.75,
        sport_tag="basketball_nba",
        bid_price=0.40,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_math_dead_q4_triggers():
    """Q4, Bill James eşiği aşıldı → MATH_DEAD."""
    # 0.861 * sqrt(240) = 13.33 → deficit=17 geçer
    result = check(
        score_info=_si(period_number=4, clock_seconds=240, deficit=17),
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "MATH_DEAD" in result.detail


def test_empirical_q4_blowout():
    """Q4, 12 dk kala 20 fark → EMPIRICAL_DEAD."""
    result = check(
        score_info=_si(period_number=4, clock_seconds=720, deficit=20),
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.25,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "EMPIRICAL" in result.detail


def test_empirical_q4_endgame():
    """Q4, son 60s, 6 fark → EMPIRICAL_DEAD."""
    result = check(
        score_info=_si(period_number=4, clock_seconds=60, deficit=6),
        elapsed_pct=0.95,
        sport_tag="basketball_nba",
        bid_price=0.20,
        entry_price=0.55,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "EMPIRICAL" in result.detail


def test_overtime_dead():
    """OT, son 60s, 8 fark → OT_DEAD."""
    result = check(
        score_info={**_si(period_number=5, clock_seconds=60, deficit=8), "available": True},
        elapsed_pct=1.1,
        sport_tag="basketball_nba",
        bid_price=0.15,
        entry_price=0.55,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "OT_DEAD" in result.detail


def test_q4_small_deficit_alive():
    """Q4, 5 dakika kala, 5 fark → geri dönülebilir, hold."""
    # 0.861 * sqrt(300) = 14.9 → 5 < 14.9 → MATH: geçmez
    # Empirical: 300s > 180s (final eşiği değil) → blowout check: 5 < 20 → geçmez
    result = check(
        score_info=_si(period_number=4, clock_seconds=300, deficit=5),
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.45,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_structural_damage_last_resort():
    """Q4, fiyat entry'nin %30'unun altına düştü + math dead → STRUCTURAL_DAMAGE."""
    # entry=0.60, bid=0.17 → 0.17/0.60 = 0.283 < 0.30
    # 0.861 * sqrt(120) = 9.43 → deficit=15 geçer
    result = check(
        score_info=_si(period_number=4, clock_seconds=120, deficit=15),
        elapsed_pct=0.95,
        sport_tag="basketball_nba",
        bid_price=0.17,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is not None
    assert "STRUCTURAL" in result.detail


def test_unavailable_score_returns_none():
    """score_info available=False → hold (skor yok)."""
    result = check(
        score_info={"available": False},
        elapsed_pct=0.90,
        sport_tag="basketball_nba",
        bid_price=0.30,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None


def test_ot_small_deficit_alive():
    """OT, son 120s, 4 fark → OT_DEAD eşiği aşılmadı, hold."""
    result = check(
        score_info={**_si(period_number=5, clock_seconds=120, deficit=4), "available": True},
        elapsed_pct=1.05,
        sport_tag="basketball_nba",
        bid_price=0.40,
        entry_price=0.60,
        bill_james_multiplier=_M,
    )
    assert result is None
```

- [ ] **Step 2: Testi çalıştır — FAIL beklenir**

```
pytest tests/unit/strategy/exit/test_nba_score_exit.py -v
```
Beklenen: ImportError veya tüm testler fail.

- [ ] **Step 3: nba_score_exit.py implementasyonunu yaz**

`src/strategy/exit/nba_score_exit.py`:

```python
"""NBA score exit — Bill James formülü + empirical Q4 eşikleri."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.math.safe_lead import is_mathematically_dead
from src.models.enums import ExitReason


@dataclass
class NbaCheckResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    elapsed_pct: float,
    sport_tag: str,
    bid_price: float = 0.0,
    entry_price: float = 0.0,
    bill_james_multiplier: float = 0.861,
    structural_damage_ratio: float = 0.30,
    ot_seconds: int = 60,
    ot_deficit: int = 8,
    q4_blowout_seconds: int = 720,
    q4_blowout_deficit: int = 20,
    q4_late_seconds: int = 360,
    q4_late_deficit: int = 15,
    q4_final_seconds: int = 180,
    q4_final_deficit: int = 10,
    q4_endgame_seconds: int = 60,
    q4_endgame_deficit: int = 6,
) -> NbaCheckResult | None:
    """NBA score-based exit kararı.

    Near-resolve (94¢) ve scale-out (85¢) monitor.py'de önce çalışır — burada yok.
    Return None → HOLD. Return NbaCheckResult → exit.
    """
    if not score_info.get("available"):
        return None

    period: int = score_info.get("period_number") or 0
    clock: int = score_info.get("clock_seconds") or 0
    deficit: int = score_info.get("deficit", 0)
    is_ot = period > 4

    # Q1-Q3: hiç tetiklenme (comeback ihtimali %5-13)
    if not is_ot and period < 4:
        return None

    # OT exit
    if is_ot and clock <= ot_seconds and deficit >= ot_deficit:
        return NbaCheckResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"OT_DEAD period={period} clock={clock}s deficit={deficit}",
        )

    # Q4 çıkışları (period == 4)
    if period == 4:
        # 1. Bill James mathematical dead
        if is_mathematically_dead(deficit, clock, bill_james_multiplier):
            return NbaCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"MATH_DEAD deficit={deficit} clock={clock}s",
            )

        # 2. Empirical backup (14-yıl NBA verisi)
        empirical = _empirical_dead(
            clock, deficit,
            q4_blowout_seconds, q4_blowout_deficit,
            q4_late_seconds, q4_late_deficit,
            q4_final_seconds, q4_final_deficit,
            q4_endgame_seconds, q4_endgame_deficit,
        )
        if empirical:
            return NbaCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"EMPIRICAL_DEAD deficit={deficit} clock={clock}s",
            )

        # 3. Structural damage — son çare
        if (
            entry_price > 0
            and bid_price > 0
            and (bid_price / entry_price) < structural_damage_ratio
            and is_mathematically_dead(deficit, clock, bill_james_multiplier)
        ):
            return NbaCheckResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"STRUCTURAL_DAMAGE price_ratio={bid_price/entry_price:.2f}",
            )

    return None


def _empirical_dead(
    clock: int,
    deficit: int,
    blowout_sec: int,
    blowout_def: int,
    late_sec: int,
    late_def: int,
    final_sec: int,
    final_def: int,
    endgame_sec: int,
    endgame_def: int,
) -> bool:
    """14-yıl NBA geri dönüş verisi — ~%1-3 ihtimal altı eşikler."""
    return (
        (clock <= blowout_sec and deficit >= blowout_def)
        or (clock <= late_sec and deficit >= late_def)
        or (clock <= final_sec and deficit >= final_def)
        or (clock <= endgame_sec and deficit >= endgame_def)
    )
```

- [ ] **Step 4: monitor.py'deki nba çağrısını güncelle**

`src/strategy/exit/monitor.py` satır 279-289'ı bul. Şu anki kod:

```python
    if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
        nba_result = nba_score_exit.check(
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            sport_tag=pos.sport_tag,
        )
```

Şu şekilde güncelle (AppConfig erişimi için cfg import'u gerekmiyor — default parametreler config'den ayrı okunmalı):

```python
    if _normalize(pos.sport_tag) == "nba" and score_info.get("available"):
        nba_result = nba_score_exit.check(
            score_info=score_info,
            elapsed_pct=elapsed_pct,
            sport_tag=pos.sport_tag,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
        )
```

NOT: config'den multiplier okumak için monitor.py'e AppConfig inject etmek yerine
nba_score_exit.check() default parametreleri config.yaml default'larıyla sync tutar.
Config değişirse hem config.yaml hem de bu default'lar güncellenir (drift tablosu).

- [ ] **Step 5: Testleri çalıştır — PASS beklenir**

```
pytest tests/unit/strategy/exit/test_nba_score_exit.py -v
pytest -q
```
Beklenen: 9 yeni passed, toplam 840 passed.

- [ ] **Step 6: Commit**

```bash
git add src/strategy/exit/nba_score_exit.py \
        src/strategy/exit/monitor.py \
        tests/unit/strategy/exit/test_nba_score_exit.py
git commit -m "feat(exit/nba): Bill James + empirical Q4 exit, 9 tests"
```

---

## Task 4: Entry gate — GateConfig genişletme + factory wire

**Files:**
- Modify: `src/strategy/entry/gate.py` (GateConfig'e yeni alanlar)
- Modify: `src/orchestration/factory.py` (GateConfig constructor)

- [ ] **Step 1: GateConfig'e yeni alanlar ekle**

`src/strategy/entry/gate.py`'deki `GateConfig` dataclass'ını güncelle:

```python
@dataclass
class GateConfig:
    # Mevcut alanlar (factory'den geliyor)
    min_favorite_probability: float
    max_entry_price: float
    max_positions: int
    max_exposure_pct: float
    confidence_bet_pct: dict
    max_single_bet_usdc: float
    max_bet_pct: float
    probability_weighted: bool
    min_bookmakers: int
    min_sharps: int
    hard_cap_overflow_pct: float = field(default=0.02)
    min_entry_size_pct: float = field(default=0.015)
    # Yeni alanlar
    active_sports: list[str] = field(default_factory=list)
    min_gap_threshold: float = field(default=0.08)
    gap_high_zone: float = field(default=0.15)
    gap_extreme_zone: float = field(default=0.25)
    min_polymarket_price: float = field(default=0.15)
    min_market_volume: float = field(default=5000.0)
    max_match_start_hours: float = field(default=6.0)
    confidence_a_pct: float = field(default=0.05)
    confidence_b_pct: float = field(default=0.03)
    high_gap_multiplier: float = field(default=1.2)
    extreme_gap_multiplier: float = field(default=1.3)
    min_bet_usd: float = field(default=5.0)
```

- [ ] **Step 2: factory.py GateConfig constructor'ını genişlet**

`src/orchestration/factory.py`'deki `gate_cfg = GateConfig(...)` bloğunu güncelle:

```python
    gate_cfg = GateConfig(
        # Mevcut (değişmedi)
        min_favorite_probability=cfg.entry.min_favorite_probability,
        max_entry_price=cfg.entry.max_entry_price,
        max_positions=cfg.risk.max_positions,
        max_exposure_pct=cfg.risk.max_exposure_pct,
        hard_cap_overflow_pct=cfg.risk.hard_cap_overflow_pct,
        min_entry_size_pct=cfg.risk.min_entry_size_pct,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_single_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
        probability_weighted=cfg.risk.probability_weighted,
        min_bookmakers=cfg.entry.min_bookmakers,
        min_sharps=cfg.entry.min_sharps,
        # Yeni
        active_sports=cfg.entry.active_sports,
        min_gap_threshold=cfg.entry.min_gap_threshold,
        gap_high_zone=cfg.entry.gap_high_zone,
        gap_extreme_zone=cfg.entry.gap_extreme_zone,
        min_polymarket_price=cfg.entry.min_polymarket_price,
        min_market_volume=cfg.entry.min_market_volume,
        max_match_start_hours=cfg.entry.max_match_start_hours,
        confidence_a_pct=cfg.entry.confidence_a_pct,
        confidence_b_pct=cfg.entry.confidence_b_pct,
        high_gap_multiplier=cfg.entry.high_gap_multiplier,
        extreme_gap_multiplier=cfg.entry.extreme_gap_multiplier,
        min_bet_usd=cfg.entry.min_bet_usd,
    )
```

- [ ] **Step 3: Mevcut testleri çalıştır**

```
pytest -q
```
Beklenen: 840 passed (GateConfig default'lar sayesinde mevcut testler kırılmaz).

- [ ] **Step 4: Commit**

```bash
git add src/strategy/entry/gate.py src/orchestration/factory.py
git commit -m "feat(entry/gate): GateConfig gap/filter/sizing alanları, factory wire"
```

---

## Task 5: Entry gate — run() implementasyonu (TDD)

**Files:**
- Modify: `src/strategy/entry/gate.py` (run() + yardımcı fonksiyonlar)
- Modify: `tests/unit/strategy/entry/test_gate.py` (stub testleri kaldır, gerçek testler ekle)

**Tasarım:**
- Saf yardımcı fonksiyonlar module-level `_` prefix ile → doğrudan test edilebilir
- `run()` bu fonksiyonları orchestrate eder
- `odds_enricher` callable: `(MarketData) -> EnrichResult` (EnrichResult.probability: BookmakerProbability | None)

**EnrichResult import:**
`from src.strategy.enrichment.odds_enricher import EnrichResult` gerekirse `TYPE_CHECKING` altında.

**BookmakerProbability alanları (src/domain/analysis/probability.py):**
- `prob: float` — bookmaker consensus P(YES)
- `has_sharp: bool`
- `num_bookmakers: float` — weighted toplam
- `num_sharps: int`

- [ ] **Step 1: Failing testleri yaz**

`tests/unit/strategy/entry/test_gate.py` içeriğini tamamen değiştir:

```python
"""EntryGate + GateConfig testleri — gap-based entry logic."""
from __future__ import annotations

from unittest.mock import MagicMock
from src.strategy.entry.gate import (
    GateConfig,
    EntryGate,
    _classify_confidence,
    _gap_multiplier,
    _compute_stake,
    _passes_filters,
)


def _make_cfg(**overrides) -> GateConfig:
    base = dict(
        min_favorite_probability=0.60,
        max_entry_price=0.80,
        max_positions=20,
        max_exposure_pct=0.50,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=75.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=15,
        min_sharps=3,
    )
    base.update(overrides)
    return GateConfig(**base)


# ── GateConfig defaults ──────────────────────────────────────────
def test_gate_config_defaults_hard_cap_overflow():
    assert _make_cfg().hard_cap_overflow_pct == 0.02


def test_gate_config_defaults_min_entry_size_pct():
    assert _make_cfg().min_entry_size_pct == 0.015


def test_gate_config_defaults_min_gap_threshold():
    assert _make_cfg().min_gap_threshold == 0.08


# ── _classify_confidence ─────────────────────────────────────────
def test_confidence_a_with_sharp():
    assert _classify_confidence(has_sharp=True, bm_weight=6.0) == "A"


def test_confidence_b_no_sharp():
    assert _classify_confidence(has_sharp=False, bm_weight=6.0) == "B"


def test_confidence_c_low_weight():
    assert _classify_confidence(has_sharp=True, bm_weight=3.0) == "C"


# ── _gap_multiplier ──────────────────────────────────────────────
def test_gap_multiplier_normal():
    cfg = _make_cfg()
    assert _gap_multiplier(gap=0.10, cfg=cfg) == 1.0


def test_gap_multiplier_high_zone():
    cfg = _make_cfg()
    assert _gap_multiplier(gap=0.20, cfg=cfg) == 1.2


def test_gap_multiplier_extreme_zone():
    cfg = _make_cfg()
    assert _gap_multiplier(gap=0.26, cfg=cfg) == 1.3


# ── _passes_filters ──────────────────────────────────────────────
def test_filters_pass_nominal():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    )
    assert reason is None


def test_filters_gap_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.05, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    )
    assert reason == "GAP_TOO_LOW"


def test_filters_price_out_of_range_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.10, bookmaker_prob=0.65,
        volume=10_000.0, cfg=cfg,
    )
    assert reason == "PRICE_OUT_OF_RANGE"


def test_filters_volume_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.65,
        volume=3_000.0, cfg=cfg,
    )
    assert reason == "VOLUME_TOO_LOW"


def test_filters_bookmaker_prob_too_low():
    cfg = _make_cfg()
    reason = _passes_filters(
        gap=0.10, polymarket_price=0.45, bookmaker_prob=0.55,
        volume=10_000.0, cfg=cfg,
    )
    assert reason == "BOOKMAKER_PROB_TOO_LOW"


# ── _compute_stake ───────────────────────────────────────────────
def test_compute_stake_confidence_a_no_gap_mult():
    cfg = _make_cfg()
    # bankroll=1000, conf_a=0.05, gap_mult=1.0, win_prob=0.65
    stake = _compute_stake(
        bankroll=1000.0, confidence="A", gap=0.10,
        win_prob=0.65, cfg=cfg,
    )
    assert abs(stake - 1000 * 0.05 * 0.65) < 0.01


def test_compute_stake_high_gap_multiplier():
    cfg = _make_cfg()
    # bankroll=1000, conf_a=0.05, gap_mult=1.2, win_prob=0.65
    stake = _compute_stake(
        bankroll=1000.0, confidence="A", gap=0.20,
        win_prob=0.65, cfg=cfg,
    )
    assert abs(stake - 1000 * 0.05 * 0.65 * 1.2) < 0.01


def test_compute_stake_hard_cap():
    cfg = _make_cfg()
    # Yüksek bankroll → hard cap (bankroll * max_bet_pct = 0.05) devreye girer
    stake = _compute_stake(
        bankroll=10_000.0, confidence="A", gap=0.30,
        win_prob=0.90, cfg=cfg,
    )
    assert stake <= 10_000 * 0.05


# ── EntryGate.run() ──────────────────────────────────────────────
def test_gate_run_empty_markets_returns_empty():
    cfg = _make_cfg()
    gate = EntryGate(
        config=cfg, portfolio=None, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=None, manipulation_checker=None,
    )
    assert gate.run([]) == []


def test_gate_run_inactive_sport_skipped():
    """active_sports boşsa tüm marketler atlanır."""
    from unittest.mock import MagicMock
    cfg = _make_cfg(active_sports=[])
    gate = EntryGate(
        config=cfg, portfolio=None, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=MagicMock(), manipulation_checker=None,
    )
    market = MagicMock()
    market.sport_tag = "basketball_nba"
    result = gate.run([market])
    assert len(result) == 1
    assert result[0].signal is None
    assert result[0].skipped_reason == "INACTIVE_SPORT"


def test_gate_run_same_event_same_direction_blocked():
    """Aynı event_id + aynı yön → BLOCKED."""
    from unittest.mock import MagicMock, patch
    from src.models.enums import Direction

    cfg = _make_cfg(active_sports=["basketball_nba"])

    mock_prob = MagicMock()
    mock_prob.prob = 0.70
    mock_prob.has_sharp = True
    mock_prob.num_bookmakers = 7.0
    mock_prob.num_sharps = 4

    mock_enrich = MagicMock()
    mock_enrich.probability = mock_prob
    mock_enrich.fail_reason = None

    existing_pos = MagicMock()
    existing_pos.event_id = "evt_001"
    existing_pos.direction = Direction.BUY_YES

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {"some_cid": existing_pos}
    mock_portfolio.bankroll.return_value = 1000.0

    gate = EntryGate(
        config=cfg, portfolio=mock_portfolio, circuit_breaker=None,
        cooldown=None, blacklist=None,
        odds_enricher=lambda m: mock_enrich,
        manipulation_checker=None,
    )

    market = MagicMock()
    market.condition_id = "new_cid"
    market.sport_tag = "basketball_nba"
    market.yes_price = 0.45       # gap = 0.70 - 0.45 = 0.25
    market.volume_24h = 10_000.0
    market.liquidity = 5_000.0
    market.event_id = "evt_001"   # aynı event

    result = gate.run([market])
    assert len(result) == 1
    assert result[0].skipped_reason == "EVENT_GUARD_SAME_DIRECTION"
```

- [ ] **Step 2: Testi çalıştır — FAIL beklenir**

```
pytest tests/unit/strategy/entry/test_gate.py -v
```
Beklenen: `ImportError` (_classify_confidence, _gap_multiplier vb. yok).

- [ ] **Step 3: gate.py run() + yardımcı fonksiyonları implement et**

`src/strategy/entry/gate.py` dosyasını tam olarak yaz:

```python
"""Entry gate — gap-based NBA entry kararı."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.config.sport_rules import _normalize
from src.models.enums import Direction, EntryReason
from src.models.signal import Signal

if TYPE_CHECKING:
    from src.models.market import MarketData


@dataclass
class GateConfig:
    min_favorite_probability: float
    max_entry_price: float
    max_positions: int
    max_exposure_pct: float
    confidence_bet_pct: dict
    max_single_bet_usdc: float
    max_bet_pct: float
    probability_weighted: bool
    min_bookmakers: int
    min_sharps: int
    hard_cap_overflow_pct: float = field(default=0.02)
    min_entry_size_pct: float = field(default=0.015)
    active_sports: list[str] = field(default_factory=list)
    min_gap_threshold: float = field(default=0.08)
    gap_high_zone: float = field(default=0.15)
    gap_extreme_zone: float = field(default=0.25)
    min_polymarket_price: float = field(default=0.15)
    min_market_volume: float = field(default=5000.0)
    max_match_start_hours: float = field(default=6.0)
    confidence_a_pct: float = field(default=0.05)
    confidence_b_pct: float = field(default=0.03)
    high_gap_multiplier: float = field(default=1.2)
    extreme_gap_multiplier: float = field(default=1.3)
    min_bet_usd: float = field(default=5.0)


@dataclass
class GateResult:
    condition_id: str
    signal: Signal | None = None
    skipped_reason: str | None = None
    skip_detail: str | None = None


# ── Saf yardımcı fonksiyonlar (test edilebilir) ──────────────────

def _classify_confidence(has_sharp: bool, bm_weight: float) -> str:
    """Bookmaker kalitesine göre A/B/C tier."""
    if bm_weight < 5.0:
        return "C"
    return "A" if has_sharp else "B"


def _gap_multiplier(gap: float, cfg: GateConfig) -> float:
    """Gap büyüklüğüne göre stake çarpanı."""
    if gap >= cfg.gap_extreme_zone:
        return cfg.extreme_gap_multiplier
    if gap >= cfg.gap_high_zone:
        return cfg.high_gap_multiplier
    return 1.0


def _passes_filters(
    gap: float,
    polymarket_price: float,
    bookmaker_prob: float,
    volume: float,
    cfg: GateConfig,
) -> str | None:
    """Tüm filtrelerden geç. None = geçti, string = skip sebebi."""
    if gap < cfg.min_gap_threshold:
        return "GAP_TOO_LOW"
    if polymarket_price < cfg.min_polymarket_price or polymarket_price > cfg.max_entry_price:
        return "PRICE_OUT_OF_RANGE"
    if bookmaker_prob < cfg.min_favorite_probability:
        return "BOOKMAKER_PROB_TOO_LOW"
    if volume < cfg.min_market_volume:
        return "VOLUME_TOO_LOW"
    return None


def _compute_stake(
    bankroll: float,
    confidence: str,
    gap: float,
    win_prob: float,
    cfg: GateConfig,
) -> float:
    """stake = bankroll × confidence_pct × gap_mult × win_prob, hard cap."""
    base_pct = cfg.confidence_a_pct if confidence == "A" else cfg.confidence_b_pct
    mult = _gap_multiplier(gap, cfg)
    raw = bankroll * base_pct * mult * win_prob
    cap = bankroll * cfg.max_bet_pct
    return min(raw, cap, cfg.max_single_bet_usdc)


def _check_event_guard(
    event_id: str | None,
    direction: Direction,
    positions: dict,
    max_per_event: int = 2,
) -> str | None:
    """Aynı event'te pozisyon guard. None = geçti."""
    if not event_id:
        return None
    same_event = [p for p in positions.values() if p.event_id == event_id]
    if len(same_event) >= max_per_event:
        return "EVENT_GUARD_MAX_POSITIONS"
    for pos in same_event:
        if pos.direction == direction:
            return "EVENT_GUARD_SAME_DIRECTION"
    return None


# ── EntryGate orchestration ──────────────────────────────────────

class EntryGate:
    def __init__(
        self,
        config: GateConfig,
        portfolio: Any,
        circuit_breaker: Any,
        cooldown: Any,
        blacklist: Any,
        odds_enricher: Any,
        manipulation_checker: Any,
        cricket_client: Any = None,
    ) -> None:
        self.config = config
        self._portfolio = portfolio
        self._enricher = odds_enricher

    def run(self, markets: list[MarketData]) -> list[GateResult]:
        if not markets:
            return []
        results: list[GateResult] = []
        active = {_normalize(s) for s in self.config.active_sports}
        positions = self._portfolio.positions if self._portfolio else {}
        bankroll = self._portfolio.bankroll() if self._portfolio else 0.0

        for market in markets:
            cid = market.condition_id

            if _normalize(market.sport_tag) not in active:
                results.append(GateResult(cid, skipped_reason="INACTIVE_SPORT"))
                continue

            enrich = self._enricher(market)
            if enrich.probability is None:
                results.append(GateResult(cid, skipped_reason=str(enrich.fail_reason)))
                continue

            prob = enrich.probability
            polymarket_price = market.yes_price
            gap = prob.prob - polymarket_price
            confidence = _classify_confidence(prob.has_sharp, prob.num_bookmakers)

            if confidence == "C":
                results.append(GateResult(cid, skipped_reason="CONFIDENCE_C"))
                continue

            skip = _passes_filters(gap, polymarket_price, prob.prob, market.volume_24h, self.config)
            if skip:
                results.append(GateResult(cid, skipped_reason=skip))
                continue

            direction = Direction.BUY_YES
            guard = _check_event_guard(market.event_id, direction, positions)
            if guard:
                results.append(GateResult(cid, skipped_reason=guard))
                continue

            win_prob = prob.prob if self.config.probability_weighted else 1.0
            stake = _compute_stake(bankroll, confidence, gap, win_prob, self.config)

            if stake < self.config.min_bet_usd:
                results.append(GateResult(cid, skipped_reason="BELOW_MIN_BET"))
                continue

            signal = Signal(
                condition_id=cid,
                direction=direction,
                anchor_probability=prob.prob,
                market_price=polymarket_price,
                confidence=confidence,
                size_usdc=stake,
                entry_reason=EntryReason.NORMAL,
                bookmaker_prob=prob.prob,
                num_bookmakers=prob.num_bookmakers,
                has_sharp=prob.has_sharp,
                sport_tag=market.sport_tag,
                event_id=market.event_id or "",
            )
            results.append(GateResult(cid, signal=signal))

        return results
```

- [ ] **Step 4: Testleri çalıştır — PASS beklenir**

```
pytest tests/unit/strategy/entry/test_gate.py -v
pytest -q
```
Beklenen: tüm yeni testler + 840 existing passed.

- [ ] **Step 5: Commit**

```bash
git add src/strategy/entry/gate.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(entry/gate): gap-based entry — _classify_confidence/_passes_filters/_compute_stake/run()"
```

---

## Task 6: DECISIONS.md NBA section + active_sports aktivasyon

**Files:**
- Modify: `DECISIONS.md`
- Modify: `config.yaml` (active_sports: [basketball_nba])

- [ ] **Step 1: DECISIONS.md'e NBA Moneyline bölümü ekle**

`DECISIONS.md`'e yeni bölüm ekle (ENTRY bölümünden sonra):

```markdown
---

## NBA MONEYLINE

### Bill James Safe Lead

- **Formül:** `deficit >= 0.861 × √(clock_seconds)` → geri dönüş matematiksel imkânsız
- **Multiplier 0.861:** NBA 14-yıl verisiyle %99 güven aralığı (orijinal formül 0.4538 × √t for college)
- **Kaynak:** Basketball Reference season data 2010-2024

### Empirical Q4 Eşikleri (14-yıl NBA)

| Durum | Kalan süre | Fark | Geri dönüş ihtimali |
|---|---|---|---|
| Blowout | ≤12 dk (720s) | ≥20 | ~%1 |
| Late | ≤6 dk (360s) | ≥15 | ~%2 |
| Final | ≤3 dk (180s) | ≥10 | ~%3 |
| Endgame | ≤1 dk (60s) | ≥6 | ~%2 |

Bill James önce kontrol edilir; pas geçerse empirical devreye girer.

### Q1-Q3 HOLD

- **Neden hold:** Q1-Q3'te 10 puanlık fark ile geri dönüş ihtimali %5-13. Erken exit edge yiyor.
- **Kural:** period < 4 AND not OT → return None.

### Overtime

- **OT < 60s + fark ≥ 8 → EXIT.** OT'da küçük farklar kapanabilir; 60s'de 8 puan imkânsız.

### Near-Resolve + Scale-Out

- Near-resolve (94¢) ve scale-out (85¢) monitor.py priority 1-2'de, sport-agnostic.
  nba_score_exit.py'de duplicate yok.

### Entry — Gap Thresholds

| Eşik | Değer | Rationale |
|---|---|---|
| min_gap | 0.08 | Ana edge zone; altında noise > signal |
| high_zone | 0.15 | Belirgin misprice; stake ×1.2 |
| extreme_zone | 0.25 | Güçlü misprice; stake ×1.3 |
| max_entry_price | 0.80 | R/R kırık (zaten EntryConfig'den) |
| min_polymarket | 0.15 | Uç outlier reddi; spike koruması |

### Entry — Sizing

- `stake = bankroll × confidence_pct × gap_mult × win_prob`
- A = 5%, B = 3% (B eski değer 4%'ten düşürüldü — gap filtresi zaten kaliteyi kısıtlıyor)
- Hard cap: `bankroll × 5%` veya `max_single_bet_usdc` ($75) hangisi küçükse

### Structural Damage

- Son çare: `bid/entry < 0.30 AND math_dead` — çift kilitlendi, spread'e kaptırmadan çık.
- price_cap SL (PLAN-014) ile örtüşebilir; önce monitor priority 3'te NBA exit tetikler.
```

- [ ] **Step 2: config.yaml active_sports'a basketball_nba ekle**

`config.yaml` `entry:` altında:

```yaml
  active_sports:
    - basketball_nba
```

- [ ] **Step 3: Final pytest**

```
pytest -q
```
Beklenen: ~848+ passed, 0 fail.

- [ ] **Step 4: Commit**

```bash
git add DECISIONS.md config.yaml
git commit -m "feat(nba): activate basketball_nba — DECISIONS.md NBA section, active_sports"
```

---

## Task 7: Doğrulama + Rapor

- [ ] **Step 1: Full test suite**

```
pytest -q
```
Beklenen: Tüm testler passed.

- [ ] **Step 2: Magic number grep**

```bash
grep -rn "0\.861\|0\.08\|0\.15\|0\.85\|0\.94\|720\|360\|180" \
     src/strategy/exit/nba_score_exit.py src/strategy/entry/gate.py
```
Beklenen: Sadece default parametre tanımlamalarında görünür; config'den geçmesi gereken yerlerde yok.

- [ ] **Step 3: Domain I/O kontrol**

```bash
grep -rn "import requests\|import os\|import pathlib\|open(" \
     src/domain/math/safe_lead.py
```
Beklenen: 0 hit.

- [ ] **Step 4: Satır sayısı kontrol**

```bash
wc -l src/domain/math/safe_lead.py \
       src/strategy/exit/nba_score_exit.py \
       src/strategy/entry/gate.py
```
Beklenen: Her biri < 400 satır.

- [ ] **Step 5: Drift tablosu kontrolü (CLAUDE.md)**

| Değişen | Güncellendi |
|---|---|
| config.yaml active_sports | ✓ Task 2 |
| DECISIONS.md NBA section | ✓ Task 6 |
| src/strategy/exit/nba_score_exit.py | ✓ Task 3 |
| src/domain/math/safe_lead.py | ✓ Task 1 |
| ARCHITECTURE_GUARD: domain I/O yok | ✓ kontrol edildi |
| 400 satır altı | ✓ kontrol edildi |

- [ ] **Step 6: Final commit**

```bash
git add -A  # sadece planlı dosyalar değiştiyse
git commit -m "chore(nba): final verification — drift tablosu temiz, 0 magic number"
```

---

## Özet

| Görev | Dosyalar | Test Sayısı |
|---|---|---|
| Task 1: safe_lead | 2 yeni | +7 |
| Task 2: config/settings | 2 modify | 0 |
| Task 3: nba_score_exit | 1 doldur + 1 yeni + monitor update | +9 |
| Task 4: GateConfig + factory | 2 modify | 0 |
| Task 5: gate.run() | 1 doldur + test update | +~15 |
| Task 6: DECISIONS + active | 2 modify | 0 |

**Önceki:** 833 test  
**Hedef:** ~864+ test, 0 fail
