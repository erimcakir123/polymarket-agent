# Probability-Weighted Position Sizing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Position sizing'i win_probability ile doğrudan orantılı hale getir — yüksek-olasılıklı girişler daha büyük, düşük-olasılıklı girişler daha küçük stake alır.

**Architecture:** Domain layer'daki `confidence_position_size()` formülü değişir. Yeni bir `effective_win_prob()` helper (domain/direction.py) direction-adjusted win_prob döner. Strategy katmanı (gate.py) bu helper'ı çağırıp sizer'a geçirir. Config flag `probability_weighted` ile kademeli açma.

**Tech Stack:** Python 3.12+, Pydantic (config), pytest (unit tests). Mevcut 5-katman mimarisine uygun.

---

## Task 1: `effective_win_prob()` helper in domain

**Files:**
- Modify: `src/models/position.py` (mevcut `effective_price()` ile aynı modül — modüller/models layer)
- Test: `tests/unit/models/test_position.py` (mevcut `effective_price` testlerinin yanına)

- [ ] **Step 1: Kontrol — mevcut direction.py yapısı**

Run: `ls src/domain/math/ && cat src/models/position.py` (eğer yoksa yeni oluştur)

Beklenen: `effective_price(market_price, direction)` zaten var olmalı. Yeni helper onun paterniyle uyumlu olacak.

- [ ] **Step 2: Failing test yaz**

`tests/unit/models/test_position.py` (mevcut dosyaya ekle veya yeni oluştur):

```python
import pytest

from src.models.position import effective_win_prob


def test_effective_win_prob_buy_yes_returns_anchor():
    assert effective_win_prob(anchor=0.75, direction="BUY_YES") == 0.75


def test_effective_win_prob_buy_no_returns_inverse():
    assert effective_win_prob(anchor=0.30, direction="BUY_NO") == pytest.approx(0.70)


def test_effective_win_prob_boundary_zero():
    assert effective_win_prob(anchor=0.0, direction="BUY_YES") == 0.0


def test_effective_win_prob_boundary_one():
    assert effective_win_prob(anchor=1.0, direction="BUY_NO") == pytest.approx(0.0)


def test_effective_win_prob_invalid_direction_raises():
    with pytest.raises(ValueError):
        effective_win_prob(anchor=0.5, direction="HOLD")
```

- [ ] **Step 3: Run test, FAIL bekle**

Run: `pytest tests/unit/models/test_position.py::test_effective_win_prob_buy_yes_returns_anchor -v`
Expected: FAIL with "cannot import effective_win_prob"

- [ ] **Step 4: Minimal implementation**

`src/models/position.py`:

```python
def effective_win_prob(anchor: float, direction: str) -> float:
    """Direction-adjusted win probability.

    P(YES) her zaman anchor (ARCH_GUARD Kural 8). Bu fonksiyon sadece
    sizing hesabında direction-adjustment uygular.

    Args:
        anchor: P(YES) from model [0.0, 1.0]
        direction: "BUY_YES" veya "BUY_NO"

    Returns:
        win probability for the bet side.

    Raises:
        ValueError: direction "BUY_YES"/"BUY_NO" dışında ise.
    """
    if direction == "BUY_YES":
        return anchor
    if direction == "BUY_NO":
        return 1.0 - anchor
    raise ValueError(f"Invalid direction: {direction!r}")
```

- [ ] **Step 5: Tests passing**

Run: `pytest tests/unit/models/test_position.py -v`
Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add src/models/position.py tests/unit/models/test_position.py
git commit -m "feat(sizing): add effective_win_prob direction helper (SPEC-016 T1)"
```

---

## Task 2: `confidence_position_size()` win_probability param

**Files:**
- Modify: `src/domain/risk/position_sizer.py`
- Test: `tests/unit/domain/risk/test_position_sizer.py`

- [ ] **Step 1: Failing test yaz**

`tests/unit/domain/risk/test_position_sizer.py`'a ekle:

```python
def test_position_size_probability_weighted_scales_by_win_prob():
    # bankroll=1000, bet_pct=0.05 → base=$50. win_prob=0.60 → $30.
    size = confidence_position_size(
        confidence="A",
        bankroll=1000.0,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        win_probability=0.60,
    )
    assert size == 30.0


def test_position_size_probability_weighted_high_prob_respects_cap():
    # base=$50 × 0.95 = $47.50 < cap $50 → $47.50
    size = confidence_position_size(
        confidence="A",
        bankroll=1000.0,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        win_probability=0.95,
        max_bet_usdc=50.0,
    )
    assert size == 47.50


def test_position_size_probability_weighted_low_prob_floors_to_zero():
    # base=$50 × 0.05 = $2.50 < $5 min-order → 0
    size = confidence_position_size(
        confidence="A",
        bankroll=1000.0,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        win_probability=0.05,
    )
    assert size == 0.0


def test_position_size_default_win_prob_preserves_legacy():
    # win_probability default = 1.0 → eski davranış
    size = confidence_position_size(
        confidence="A",
        bankroll=1000.0,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
    )
    assert size == 50.0


def test_position_size_probability_weighted_buy_no_case():
    # BUY_NO direction → caller effective_win_prob ile 1-anchor verir.
    # Sizer bu değeri direkt kullanır (0.80 anchor → caller 0.20 verir değil,
    # caller zaten 1-0.20 = 0.80 verir). Test: 0.80 input → $40.
    size = confidence_position_size(
        confidence="A",
        bankroll=1000.0,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        win_probability=0.80,
    )
    assert size == 40.0
```

- [ ] **Step 2: Run test, FAIL bekle**

Run: `pytest tests/unit/domain/risk/test_position_sizer.py -v -k "probability_weighted or preserves_legacy"`
Expected: FAIL (unexpected kwarg `win_probability`)

- [ ] **Step 3: Implementation**

`src/domain/risk/position_sizer.py`:

```python
def confidence_position_size(
    confidence: str,
    bankroll: float,
    confidence_bet_pct: dict[str, float],
    max_bet_usdc: float = 50.0,
    max_bet_pct: float = 0.05,
    is_reentry: bool = False,
    win_probability: float = 1.0,
) -> float:
    """Confidence tier + probability-weighted pozisyon boyutu (SPEC-016).

    Formula: stake = bankroll × bet_pct × win_probability

    Args:
        confidence_bet_pct: {"A": 0.05, "B": 0.04}.
        max_bet_usdc: tek-bet cap.
        max_bet_pct: bankroll % cap.
        win_probability: direction-adjusted win prob (default 1.0 = legacy).

    Floor: size < POLYMARKET_MIN_ORDER_USDC → 0 (entry blocked).
    """
    bet_pct = confidence_bet_pct.get(confidence, 0.0)
    if bet_pct == 0.0:
        return 0.0

    if is_reentry:
        bet_pct *= REENTRY_MULTIPLIER

    size = bankroll * bet_pct * win_probability
    size = min(size, max_bet_usdc, bankroll * max_bet_pct, bankroll)
    size = round(size, 2)

    if size < POLYMARKET_MIN_ORDER_USDC:
        return 0.0
    return max(0.0, size)
```

- [ ] **Step 4: Tests passing (new + existing)**

Run: `pytest tests/unit/domain/risk/test_position_sizer.py -v`
Expected: TÜM testler PASS (yeni 5 + mevcut hepsi)

- [ ] **Step 5: Commit**

```bash
git add src/domain/risk/position_sizer.py tests/unit/domain/risk/test_position_sizer.py
git commit -m "feat(sizing): probability-weighted stake in position_sizer (SPEC-016 T2)"
```

---

## Task 3: Config flag `probability_weighted`

**Files:**
- Modify: `src/config/settings.py`
- Modify: `config.yaml`
- Test: `tests/unit/config/test_settings.py`

- [ ] **Step 1: Failing test yaz**

`tests/unit/config/test_settings.py`'a ekle:

```python
def test_risk_config_probability_weighted_default_true():
    cfg = RiskConfig()
    assert cfg.probability_weighted is True


def test_risk_config_probability_weighted_explicit_false():
    cfg = RiskConfig(probability_weighted=False)
    assert cfg.probability_weighted is False
```

- [ ] **Step 2: Run test, FAIL bekle**

Run: `pytest tests/unit/config/test_settings.py::test_risk_config_probability_weighted_default_true -v`
Expected: FAIL (`probability_weighted` yok)

- [ ] **Step 3: Implementation**

`src/config/settings.py` — `RiskConfig` class'ına ekle (mevcut field'ların sonuna):

```python
class RiskConfig(BaseModel):
    # ... mevcut field'lar ...
    stop_loss_pct: float = 0.30
    probability_weighted: bool = True  # SPEC-016: stake = base × win_prob
```

`config.yaml` — `risk:` bölümüne ekle (stop_loss_pct altına):

```yaml
risk:
  # ... mevcut ...
  stop_loss_pct: 0.30
  probability_weighted: true  # SPEC-016: stake win_prob ile çarpılır
```

- [ ] **Step 4: Tests passing**

Run: `pytest tests/unit/config/test_settings.py -v`
Expected: TÜM testler PASS

- [ ] **Step 5: Commit**

```bash
git add src/config/settings.py config.yaml tests/unit/config/test_settings.py
git commit -m "feat(sizing): probability_weighted config flag (SPEC-016 T3)"
```

---

## Task 4: `gate.py` win_prob wiring

**Files:**
- Modify: `src/strategy/entry/gate.py`
- Test: `tests/unit/strategy/entry/test_gate.py`

- [ ] **Step 1: Mevcut gate.py call site'larını incele**

Grep: `confidence_position_size(` in `src/strategy/entry/gate.py`

Beklenen: 2 çağrı noktası (normal entry ~line 220, early entry ~line 314).

- [ ] **Step 2: Failing test yaz**

`tests/unit/strategy/entry/test_gate.py`'a ekle:

```python
def test_gate_passes_win_prob_when_flag_enabled(factory, portfolio):
    # Signal: BUY_YES, probability=0.70. Flag enabled.
    # Expected stake = 1000 × 0.05 × 0.70 = $35
    cfg = _make_config(probability_weighted=True)
    gate = EntryGate(config=cfg, portfolio=portfolio, ...)
    signal = _make_signal(direction="BUY_YES", probability=0.70, confidence="A")
    result = gate._evaluate_signal(signal, ...)
    assert result.size_usdc == pytest.approx(35.0)


def test_gate_skips_win_prob_when_flag_disabled(factory, portfolio):
    # Flag off → base sizing ($50)
    cfg = _make_config(probability_weighted=False)
    gate = EntryGate(config=cfg, portfolio=portfolio, ...)
    signal = _make_signal(direction="BUY_YES", probability=0.70, confidence="A")
    result = gate._evaluate_signal(signal, ...)
    assert result.size_usdc == 50.0


def test_gate_buy_no_uses_inverse_prob(factory, portfolio):
    # BUY_NO, anchor=0.20 → win_prob=0.80 → stake=$40
    cfg = _make_config(probability_weighted=True)
    gate = EntryGate(config=cfg, portfolio=portfolio, ...)
    signal = _make_signal(direction="BUY_NO", probability=0.20, confidence="A")
    result = gate._evaluate_signal(signal, ...)
    assert result.size_usdc == pytest.approx(40.0)
```

(Not: test helper'lar `_make_config`, `_make_signal` mevcut fixture'lar — yoksa ekle)

- [ ] **Step 3: Run test, FAIL bekle**

Run: `pytest tests/unit/strategy/entry/test_gate.py -v -k "win_prob"`
Expected: FAIL (stake hâlâ $50)

- [ ] **Step 4: Implementation**

`src/strategy/entry/gate.py`:

Import ekle (mevcut import'ların yanına):

```python
from src.models.position import effective_win_prob
```

2 çağrı noktasında (normal + early entry), `confidence_position_size()` çağrısını şu şekilde güncelle:

```python
win_prob = effective_win_prob(
    signal.probability, signal.direction
) if self.config.probability_weighted else 1.0

raw_size = confidence_position_size(
    confidence=signal.confidence,
    bankroll=self.portfolio.bankroll,
    confidence_bet_pct=self.config.confidence_bet_pct,
    max_bet_usdc=self.config.max_single_bet_usdc,
    max_bet_pct=self.config.max_bet_pct,
    win_probability=win_prob,
)
```

- [ ] **Step 5: Tests passing**

Run: `pytest tests/unit/strategy/entry/test_gate.py -v`
Expected: TÜM testler PASS

- [ ] **Step 6: Full test suite**

Run: `pytest -q`
Expected: 987+ PASS (regression yok)

- [ ] **Step 7: Commit**

```bash
git add src/strategy/entry/gate.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(sizing): gate wires win_prob to sizer (SPEC-016 T4)"
```

---

## Task 5: TDD + PRD doc updates

**Files:**
- Modify: `TDD.md` (§6.5 veya yeni alt bölüm)
- Modify: `PRD.md` (Risk bölümü)
- Modify: `docs/superpowers/specs/2026-04-20-probability-weighted-sizing-design.md` (status → IMPLEMENTED)

- [ ] **Step 1: TDD §6.5 güncelle**

TDD.md'de mevcut §6.5 "Position Sizing" bölümünü bul. Formül satırını güncelle:

```markdown
### 6.5 Position Sizing

Stake hesabı:
```
stake = bankroll × confidence_bet_pct × win_prob   (SPEC-016)
      capped by max_single_bet_usdc ($50)
      capped by bankroll × max_bet_pct (%5)
      floored by Polymarket $5 min-order
```

win_prob = direction-adjusted probability:
- BUY_YES → anchor_probability (P(YES))
- BUY_NO  → 1 - anchor_probability

**Neden win_prob ile çarpılır:** Yüksek-olasılıklı girişler daha büyük stake alır, düşük-olasılıklı girişler daha küçük. Zamana göre sıralı bet-pct sizing'in yarattığı "kaybetme ihtimali yüksek olana çok para" anomalisini çözer. Variance contribution favori pozisyonlarda artar, underdog'larda azalır (Quarter-Kelly benzeri muhafazakâr ağırlıklandırma).

Config flag: `risk.probability_weighted: true` (false → eski base-only formül, rollback).
```

- [ ] **Step 2: PRD'ye yeni bölüm ekle**

PRD.md'de "Risk" bölümünün altına ekle (2.X numarası olarak):

```markdown
### 2.X Probability-Weighted Sizing (SPEC-016)

**Demir kural:** Stake, model'in win probability'si ile doğrudan orantılıdır.

Formül: `stake = bankroll × bet_pct × win_prob`

Bu, "kazanma ihtimali yüksek olana daha çok para, düşük olana daha az" prensibini enforce eder. Yüksek-varyans düşük-prob girişlerin bankroll üzerindeki marjinal etkisi azaltılır.

**Etkisi:** Portföy ortalama stake'i ~%30 düşer → daha çok pozisyon alma alanı → diversification artar. Expected value %3-5 düşer ama variance ciddi azalır (kazanma oranı stabilleşir).

**Rollback:** `risk.probability_weighted: false` → eski base-only formül.
```

- [ ] **Step 3: Spec status → IMPLEMENTED**

`docs/superpowers/specs/2026-04-20-probability-weighted-sizing-design.md` dosyasında:

```markdown
**Status:** IMPLEMENTED (2026-04-20)
```

Commit listesi ekle (sonuna):
```markdown
## Implementation Commits

- T1: `<sha1>` feat(sizing): add effective_win_prob direction helper
- T2: `<sha2>` feat(sizing): probability-weighted stake in position_sizer
- T3: `<sha3>` feat(sizing): probability_weighted config flag
- T4: `<sha4>` feat(sizing): gate wires win_prob to sizer
- T5: `<sha5>` docs(tdd/prd): sync docs with SPEC-016
```

- [ ] **Step 4: Commit**

```bash
git add TDD.md PRD.md docs/superpowers/specs/2026-04-20-probability-weighted-sizing-design.md
git commit -m "docs(tdd/prd): SPEC-016 probability-weighted sizing"
```

---

## Final Verification

- [ ] `pytest -q` → tüm testler geçer (0 regression)
- [ ] `grep -r "bankroll \* bet_pct" src/` → sadece yeni formül (× win_probability içerir)
- [ ] `config.yaml` → `probability_weighted: true` var
- [ ] Spec status IMPLEMENTED

## Rollback Plan

Sorun çıkarsa:
```bash
# config.yaml
risk:
  probability_weighted: false
```
Reload bot → eski davranışa döner. Kod revertinе gerek yok.
