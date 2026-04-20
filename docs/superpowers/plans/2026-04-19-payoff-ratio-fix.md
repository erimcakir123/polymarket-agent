# Payoff Ratio Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scale-out tier'larini config-driven yapip Tier 1'i yumusatmak, max_single_bet_usdc'yi kaldirmak, confidence bet yuzdesini config'e tasimak, score exit dosyalarini tutarli isimlendirmek, ve trade silme protokolunu CLAUDE.md'ye eklemek.

**Architecture:** Pure fonksiyon degisiklikleri (scale_out.py, position_sizer.py) + config migration + dosya rename. Bot core akisi degismez. TDD: once test, sonra implementasyon.

**Tech Stack:** Python 3.12+, Pydantic config, pytest

---

### Task 1: Scale-out — config-driven + Tier 1 yumusatma

**Files:**
- Modify: `src/strategy/exit/scale_out.py`
- Modify: `config.yaml:107-113`
- Modify: `src/config/settings.py:100-106`
- Test: `tests/unit/strategy/exit/test_scale_out.py`

- [ ] **Step 1: config.yaml'da scale_out tiers'i guncelle**

```yaml
scale_out:
  enabled: true
  tiers:
    - threshold: 0.35
      sell_pct: 0.25
    - threshold: 0.50
      sell_pct: 0.50
```

- [ ] **Step 2: scale_out.py'yi config-driven yap**

`src/strategy/exit/scale_out.py` dosyasinin TAMAMI:

```python
"""Config-driven scale-out (TDD $6.6) -- pure.

Tier'lar config.yaml'dan okunur. Hardcoded sabit YOK (ARCH_GUARD Kural 6).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScaleOutDecision:
    tier: int
    sell_pct: float
    reason: str


def check_scale_out(
    scale_out_tier: int,
    unrealized_pnl_pct: float,
    tiers: list[dict],
) -> ScaleOutDecision | None:
    """Pozisyon bir sonraki tier'a hak kazandi mi? None -> hayir.

    tiers: config'den gelen [{"threshold": 0.35, "sell_pct": 0.25}, ...] listesi.
    scale_out_tier: pozisyonun su an gecmis oldugu tier (0 = hic, 1 = ilk tier, ...).
    """
    for i, tier in enumerate(tiers):
        tier_num = i + 1
        if scale_out_tier < tier_num and unrealized_pnl_pct >= tier["threshold"]:
            return ScaleOutDecision(
                tier=tier_num,
                sell_pct=tier["sell_pct"],
                reason=f"Tier {tier_num} at +{unrealized_pnl_pct:.0%}",
            )
    return None
```

- [ ] **Step 3: Testleri guncelle**

`tests/unit/strategy/exit/test_scale_out.py` dosyasinin TAMAMI:

```python
"""scale_out.py icin birim testler (TDD $6.6) -- config-driven."""
from __future__ import annotations

from src.strategy.exit.scale_out import ScaleOutDecision, check_scale_out

TIERS = [
    {"threshold": 0.35, "sell_pct": 0.25},
    {"threshold": 0.50, "sell_pct": 0.50},
]


def test_tier1_fires_at_35pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.35, tiers=TIERS)
    assert isinstance(r, ScaleOutDecision)
    assert r.tier == 1
    assert r.sell_pct == 0.25


def test_tier1_fires_above_35pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.40, tiers=TIERS)
    assert r is not None
    assert r.tier == 1


def test_tier1_skipped_below_35pct() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.34, tiers=TIERS)
    assert r is None


def test_tier2_fires_at_50pct_after_tier1() -> None:
    r = check_scale_out(scale_out_tier=1, unrealized_pnl_pct=0.50, tiers=TIERS)
    assert r is not None
    assert r.tier == 2
    assert r.sell_pct == 0.50


def test_tier2_needs_tier1_done() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, tiers=TIERS)
    assert r is not None
    assert r.tier == 1  # Tier 1 once tetiklenir


def test_beyond_max_tier_returns_none() -> None:
    r = check_scale_out(scale_out_tier=2, unrealized_pnl_pct=0.80, tiers=TIERS)
    assert r is None


def test_empty_tiers_returns_none() -> None:
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, tiers=[])
    assert r is None


def test_single_tier_works() -> None:
    single = [{"threshold": 0.50, "sell_pct": 0.50}]
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, tiers=single)
    assert r is not None
    assert r.tier == 1
    assert r.sell_pct == 0.50


def test_old_tier1_threshold_no_trigger() -> None:
    """Eski +%25 esigi artik tetiklenmez."""
    r = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.25, tiers=TIERS)
    assert r is None
```

- [ ] **Step 4: Testleri calistir**

Run: `pytest tests/unit/strategy/exit/test_scale_out.py -v`
Expected: ALL PASS

- [ ] **Step 5: monitor.py'de check_scale_out cagrisina tiers ekle**

`src/strategy/exit/monitor.py` satir 152-156'yi degistir:

Eski:
```python
    so = scale_out.check_scale_out(
        scale_out_tier=pos.scale_out_tier,
        unrealized_pnl_pct=pos.unrealized_pnl_pct,
    )
```

Yeni:
```python
    so = scale_out.check_scale_out(
        scale_out_tier=pos.scale_out_tier,
        unrealized_pnl_pct=pos.unrealized_pnl_pct,
        tiers=scale_out_tiers,
    )
```

Ayrica `evaluate()` fonksiyon imzasina `scale_out_tiers` parametresi ekle:

Eski (satir 123):
```python
def evaluate(
    pos: Position,
    score_info: dict | None = None,
    near_resolve_threshold_cents: int = 94,
    near_resolve_guard_min: int = 10,
    catastrophic_config: dict | None = None,
) -> MonitorResult:
```

Yeni:
```python
def evaluate(
    pos: Position,
    score_info: dict | None = None,
    near_resolve_threshold_cents: int = 94,
    near_resolve_guard_min: int = 10,
    catastrophic_config: dict | None = None,
    scale_out_tiers: list[dict] | None = None,
) -> MonitorResult:
```

Ve fonksiyonun basinda default ekle:
```python
    scale_out_tiers = scale_out_tiers or []
```

- [ ] **Step 6: exit_processor.py'de evaluate cagrisina tiers gecir**

`src/orchestration/exit_processor.py`'da `evaluate()` cagrisini bul ve `scale_out_tiers` ekle. Config'den `self.config.scale_out.tiers` seklinde alinir. Tier'lari dict listesine cevir:

```python
scale_out_tiers = [{"threshold": t.threshold, "sell_pct": t.sell_pct} for t in self.config.scale_out.tiers]
```

Bu listeyi `evaluate()` cagrisina `scale_out_tiers=scale_out_tiers` olarak gecir.

- [ ] **Step 7: Tum testleri calistir**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add src/strategy/exit/scale_out.py src/strategy/exit/monitor.py src/orchestration/exit_processor.py config.yaml tests/unit/strategy/exit/test_scale_out.py
git commit -m "feat(scale-out): config-driven tiers + Tier 1 yumusatma (SPEC-008 2a)"
```

---

### Task 2: Position sizer — max_single_bet kaldir + confidence_bet_pct config'e tasi

**Files:**
- Modify: `src/domain/risk/position_sizer.py`
- Modify: `config.yaml:70-71`
- Modify: `src/config/settings.py:48-51`
- Modify: `src/strategy/entry/gate.py:47,175`
- Modify: `src/orchestration/factory.py:89-90`
- Test: `tests/unit/domain/risk/test_position_sizer.py`

- [ ] **Step 1: config.yaml'i guncelle**

`config.yaml` risk bolumunde:

Eski:
```yaml
risk:
  max_single_bet_usdc: 75
  max_bet_pct: 0.05
```

Yeni:
```yaml
risk:
  max_bet_pct: 0.05
  confidence_bet_pct:
    A: 0.05
    B: 0.04
```

`max_single_bet_usdc` satirini SIL.

- [ ] **Step 2: settings.py'de RiskConfig guncelle**

`src/config/settings.py` RiskConfig'den `max_single_bet_usdc` fieldini sil, `confidence_bet_pct` ekle:

Eski:
```python
class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_single_bet_usdc: float = 75
    max_bet_pct: float = 0.05
```

Yeni:
```python
class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_bet_pct: float = 0.05
    confidence_bet_pct: dict[str, float] = {"A": 0.05, "B": 0.04}
```

- [ ] **Step 3: position_sizer.py'yi guncelle**

`src/domain/risk/position_sizer.py` dosyasinin TAMAMI:

```python
"""Confidence-based position sizing (TDD $6.5) -- pure, no I/O.

Confidence bet yuzdeleri config'den gelir (ARCH_GUARD Kural 6).
Sabit tavan (max_single_bet_usdc) KALDIRILDI -- yuzde bazli cap yeterli.
"""
from __future__ import annotations

REENTRY_MULTIPLIER = 0.80
POLYMARKET_MIN_ORDER_USDC = 5.0


def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
) -> float:
    """Confidence tier bazli pozisyon boyutu.

    confidence_bet_pct: config'den gelen {"A": 0.05, "B": 0.04} dict.
    Tabloda olmayan confidence -> 0 (entry bloklanir).
    Cap: bankroll x max_bet_pct. Sabit USDC tavan YOK.
    """
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct
    size = min(size, bankroll * max_bet_pct, bankroll)
    return max(0.0, round(size, 2))
```

- [ ] **Step 4: gate.py'den max_single_bet_usdc kaldir**

`src/strategy/entry/gate.py` degisiklikleri:

GateConfig'den sil (satir 47):
```python
    # max_single_bet_usdc: float = 75.0  ← SIL
```

`confidence_bet_pct` ekle:
```python
    confidence_bet_pct: dict[str, float] = {"A": 0.05, "B": 0.04}
```

Sizing cagrisini guncelle (satir 172-177):

Eski:
```python
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            max_bet_usdc=self.config.max_single_bet_usdc,
            max_bet_pct=self.config.max_bet_pct,
        )
```

Yeni:
```python
        raw_size = confidence_position_size(
            confidence=signal.confidence,
            bankroll=self.portfolio.bankroll,
            confidence_bet_pct=self.config.confidence_bet_pct,
            max_bet_pct=self.config.max_bet_pct,
        )
```

- [ ] **Step 5: factory.py'den max_single_bet_usdc gecisini kaldir, confidence_bet_pct ekle**

`src/orchestration/factory.py` satir 89:

Eski:
```python
        max_single_bet_usdc=cfg.risk.max_single_bet_usdc,
```

Yeni:
```python
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
```

- [ ] **Step 6: Testleri guncelle**

`tests/unit/domain/risk/test_position_sizer.py` dosyasinin TAMAMI:

```python
"""position_sizer.py icin birim testler (TDD $6.5) -- config-driven."""
from __future__ import annotations

from src.domain.risk.position_sizer import (
    POLYMARKET_MIN_ORDER_USDC,
    confidence_position_size,
)

BET_PCT = {"A": 0.05, "B": 0.04}


def test_A_confidence_5pct_of_bankroll() -> None:
    assert confidence_position_size("A", bankroll=1000, confidence_bet_pct=BET_PCT) == 50.0


def test_B_confidence_4pct_of_bankroll() -> None:
    assert confidence_position_size("B", bankroll=1000, confidence_bet_pct=BET_PCT) == 40.0


def test_C_confidence_returns_zero() -> None:
    assert confidence_position_size("C", bankroll=1000, confidence_bet_pct=BET_PCT) == 0.0


def test_no_hard_cap() -> None:
    """max_single_bet_usdc kaldirildi -- $75 cap yok."""
    result = confidence_position_size("A", bankroll=10_000, confidence_bet_pct=BET_PCT)
    assert result == 500.0  # %5 x $10,000, eski $75 cap yok


def test_max_bet_pct_cap() -> None:
    result = confidence_position_size(
        "A", bankroll=10_000, confidence_bet_pct=BET_PCT, max_bet_pct=0.01,
    )
    assert result == 100.0  # %1 x $10,000


def test_reentry_multiplier() -> None:
    result = confidence_position_size(
        "B", bankroll=1000, confidence_bet_pct=BET_PCT, is_reentry=True,
    )
    assert result == 32.0  # %4 x 0.80 x $1000


def test_zero_bankroll_returns_zero() -> None:
    assert confidence_position_size("A", bankroll=0, confidence_bet_pct=BET_PCT) == 0.0


def test_unknown_confidence_returns_zero() -> None:
    assert confidence_position_size("X", bankroll=1000, confidence_bet_pct=BET_PCT) == 0.0


def test_polymarket_min_constant() -> None:
    assert POLYMARKET_MIN_ORDER_USDC == 5.0
```

- [ ] **Step 7: Testleri calistir**

Run: `pytest tests/unit/domain/risk/test_position_sizer.py -v`
Expected: ALL PASS

- [ ] **Step 8: Tum testleri calistir (entegrasyon kontrol)**

Run: `pytest tests/ -x -q`
Expected: ALL PASS (gate, factory, exit_processor testleri de gecmeli)

- [ ] **Step 9: Commit**

```bash
git add src/domain/risk/position_sizer.py src/config/settings.py src/strategy/entry/gate.py src/orchestration/factory.py config.yaml tests/unit/domain/risk/test_position_sizer.py
git commit -m "feat(sizing): config-driven confidence_bet_pct + max_single_bet_usdc kaldirildi (SPEC-008 2b)"
```

---

### Task 3: Score exit dosya isimlendirme

**Files:**
- Rename: `src/strategy/exit/score_exit.py` -> `src/strategy/exit/hockey_score_exit.py`
- Rename: `src/strategy/exit/tennis_exit.py` -> `src/strategy/exit/tennis_score_exit.py`
- Modify: `src/strategy/exit/monitor.py:22`
- Rename: `tests/unit/strategy/exit/test_score_exit.py` -> `tests/unit/strategy/exit/test_hockey_score_exit.py`
- Rename: `tests/unit/strategy/exit/test_tennis_exit.py` -> `tests/unit/strategy/exit/test_tennis_score_exit.py`

- [ ] **Step 1: Kaynak dosyalari rename et**

```bash
git mv src/strategy/exit/score_exit.py src/strategy/exit/hockey_score_exit.py
git mv src/strategy/exit/tennis_exit.py src/strategy/exit/tennis_score_exit.py
```

- [ ] **Step 2: Test dosyalarini rename et**

```bash
git mv tests/unit/strategy/exit/test_score_exit.py tests/unit/strategy/exit/test_hockey_score_exit.py
git mv tests/unit/strategy/exit/test_tennis_exit.py tests/unit/strategy/exit/test_tennis_score_exit.py
```

- [ ] **Step 3: monitor.py import'larini guncelle**

`src/strategy/exit/monitor.py` satir 22:

Eski:
```python
from src.strategy.exit import a_conf_hold, catastrophic_watch, favored, graduated_sl, near_resolve, scale_out, score_exit, stop_loss, tennis_exit
```

Yeni:
```python
from src.strategy.exit import a_conf_hold, catastrophic_watch, favored, graduated_sl, near_resolve, scale_out, hockey_score_exit, stop_loss, tennis_score_exit
```

Satir 185'te `score_exit.check` -> `hockey_score_exit.check`:

Eski:
```python
            sc_result = score_exit.check(
```

Yeni:
```python
            sc_result = hockey_score_exit.check(
```

Satir 201'de `tennis_exit.check` -> `tennis_score_exit.check`:

Eski:
```python
            t_result = tennis_exit.check(
```

Yeni:
```python
            t_result = tennis_score_exit.check(
```

- [ ] **Step 4: Test dosyalarindaki import'lari guncelle**

`tests/unit/strategy/exit/test_hockey_score_exit.py`:
```python
from src.strategy.exit.hockey_score_exit import ...  # eski: score_exit
```

`tests/unit/strategy/exit/test_tennis_score_exit.py`:
```python
from src.strategy.exit.tennis_score_exit import ...  # eski: tennis_exit
```

- [ ] **Step 5: Testleri calistir**

Run: `pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(exit): score exit dosyalari tutarli isimlendirme (SPEC-008 2c)"
```

---

### Task 4: Trade silme protokolunu CLAUDE.md'ye ekle

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md'ye Trade Silme Protokolu bolumu ekle**

`CLAUDE.md`'nin "Restart Protokolu" bolumunden ONCE, su bolumu ekle:

```markdown
---

## Trade Silme / Duzeltme Protokolu

Kullanici "bu trade'i sil" veya "su trade'de X olsaydi, onu yansit" dediginde
asagidaki dosyalarin HEPSI guncellenir. Eksik dosya = veri tutarsizligi.

### Etkilenen Dosyalar

| # | Dosya | Ne yapilir |
|---|---|---|
| 1 | `logs/positions.json` | Acik pozisyonsa sil. `realized_pnl`'i trade PnL kadar duzelt. |
| 2 | `logs/trade_history.jsonl` | Ilgili satiri sil (slug + entry_timestamp). |
| 3 | `logs/equity_history.jsonl` | entry_timestamp sonrasi TUM snapshot'larda realized_pnl duzelt. |
| 4 | `logs/positions.json` -> `high_water_mark` | Duzeltilmis snapshot'lardan yeniden hesapla. |
| 5 | `logs/circuit_breaker_state.json` | Trade PnL'i gunluk/saatlik toplamdan cikar. |
| 6 | `logs/bot.log` | DEGISTIRME (audit trail). |

### Islem Turleri

**Tam Silme** ("hic olmamis gibi"):
1. trade_history.jsonl'den sil
2. positions.json'dan sil (aciksa) + realized_pnl duzelt
3. equity_history.jsonl retroaktif duzelt
4. HWM yeniden hesapla
5. circuit_breaker_state guncelle

**What-If Duzeltme** ("SL tetiklenseydi"):
1. trade_history.jsonl'de exit_price/exit_pnl_usdc guncelle
2. delta = yeni_pnl - eski_pnl
3. positions.json realized_pnl'e delta ekle
4. equity_history.jsonl'de exit_timestamp sonrasi duzelt
5. HWM yeniden hesapla

### Dogrulama (her islem sonrasi)

1. `SUM(trade_history exit_pnl + partial_pnl) == positions.json realized_pnl`
2. Silinen trade'in slug'i hicbir JSON'da kalmamali (bot.log haric)
3. equity_history son snapshot ile positions.json uyumlu olmali
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: trade silme/duzeltme protokolu eklendi (SPEC-008 2d)"
```

---

### Task 5: TDD.md + PRD.md guncelle

**Files:**
- Modify: `TDD.md` (§6.5 sizing + §6.6 scale-out)
- Modify: `PRD.md` (risk parametreleri)

- [ ] **Step 1: TDD.md'de §6.5 (position sizing) bolumunu guncelle**

Degisiklikler:
- `max_single_bet_usdc` referanslarini kaldir
- `CONF_BET_PCT` hardcoded referansini `confidence_bet_pct (config)` olarak guncelle
- "Cap: tek trade max $75" → "Cap: bankroll x max_bet_pct (%5). Sabit USDC tavan YOK."

- [ ] **Step 2: TDD.md'de §6.6 (scale-out) bolumunu guncelle**

Degisiklikler:
- Tier 1: threshold 0.25 -> 0.35, sell_pct 0.40 -> 0.25
- "Sabitler config.yaml'dan okunur (ARCH_GUARD Kural 6)"
- Tier tablosunu yeni degerlere guncelle

- [ ] **Step 3: PRD.md'de risk parametrelerini guncelle**

max_single_bet_usdc referanslarini kaldir. Scale-out tier degerlerini guncelle.

- [ ] **Step 4: Commit**

```bash
git add TDD.md PRD.md
git commit -m "docs: TDD + PRD risk/sizing parametreleri guncellendi (SPEC-008)"
```

---

### Task 6: Final entegrasyon testi + spec durumu guncelle

**Files:**
- Modify: `docs/superpowers/specs/2026-04-19-payoff-ratio-fix-design.md`

- [ ] **Step 1: Tum testleri calistir**

Run: `pytest tests/ -v`
Expected: ALL PASS, no failures

- [ ] **Step 2: Config degerlerini dogrula**

```bash
grep -n "threshold\|sell_pct\|max_single_bet\|confidence_bet_pct\|max_bet_pct" config.yaml
```

Beklenen: max_single_bet_usdc YOK, confidence_bet_pct VAR, scale_out tiers 0.35/0.25 + 0.50/0.50.

- [ ] **Step 3: Import dogrulamasi**

```bash
grep -rn "score_exit\|tennis_exit" src/ --include="*.py" | grep -v hockey_score_exit | grep -v tennis_score_exit | grep -v baseball_score_exit | grep -v __pycache__
```

Beklenen: Eski isim hicbir yerde kalmamali (0 sonuc).

```bash
grep -rn "max_single_bet_usdc\|CONF_BET_PCT" src/ --include="*.py" | grep -v __pycache__
```

Beklenen: 0 sonuc (tamamen kaldirilmis olmali).

- [ ] **Step 4: Spec durumunu APPROVED yap**

`docs/superpowers/specs/2026-04-19-payoff-ratio-fix-design.md`'de:
```
> **Durum**: DRAFT
```
->
```
> **Durum**: IMPLEMENTED
```

- [ ] **Step 5: Final commit**

```bash
git add docs/superpowers/specs/2026-04-19-payoff-ratio-fix-design.md
git commit -m "feat: SPEC-008 payoff ratio fix tamamlandi"
```
