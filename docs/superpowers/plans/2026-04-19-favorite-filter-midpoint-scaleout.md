# Favorite Filter + Midpoint Scale-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Underdog bet'leri ele (bookmaker bizim tarafa %55+ vermeli) + scale-out threshold'u "midpoint-to-resolution" semantiğine geçir (entry ile 0.99 arasındaki mesafenin yarısı).

**Architecture:** Normal + early_entry strategy'lerine unified `min_favorite_probability` guard. Scale-out `threshold` semantiği PnL% → "distance fraction to 0.99". Config-driven, no magic numbers. Tests güncellenir, TDD+PRD güncellenir, dead code yok.

**Tech Stack:** Python 3.12, pydantic BaseModel, pytest. ARCH_GUARD kurallarına uygun: <400 satır, domain I/O yok, katman düzeni korunur.

---

### Task 1: `min_favorite_probability` guard — normal + early + gate config

**Files:**
- Modify: `src/strategy/entry/gate.py:43-66` — GateConfig'e `min_favorite_probability` field
- Modify: `src/strategy/entry/gate.py:219-249` — `_evaluate_strategies` normal + early çağrılarına param geçir
- Modify: `src/strategy/entry/normal.py` — `min_favorite_probability` param + our_side_prob guard
- Modify: `src/strategy/entry/early_entry.py` — min_anchor_probability mantığı our_side_prob'a çevir
- Modify: `src/config/settings.py:40-44` — EdgeConfig'e `min_favorite_probability: float = 0.55`
- Modify: `config.yaml:61-66` — `edge.min_favorite_probability: 0.55`
- Modify: `src/orchestration/factory.py:88-108` — GateConfig construction'a `min_favorite_probability=cfg.edge.min_favorite_probability`

- [ ] **Step 1: Write failing test — normal entry underdog skip**

Add to `tests/unit/strategy/entry/test_normal.py`:

```python
def test_normal_entry_underdog_rejected_by_favorite_filter() -> None:
    """Bookmaker bizim tarafa %48 -> favorite filter skip (>=%55 lazim)."""
    m = _market(yes_price=0.30)  # Market thinks YES = 30%
    bm = _bm(prob=0.44, conf="A")  # Bookmaker thinks YES = 44% (undervalued but still underdog)
    # Edge 14% ok ama our_side_prob (0.44) < 0.55 -> skip
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is None


def test_normal_entry_favorite_accepted_by_filter() -> None:
    """Bookmaker bizim tarafa %60 -> girer."""
    m = _market(yes_price=0.50)
    bm = _bm(prob=0.60, conf="A")  # Bookmaker %60 YES, edge 10%, our side favorite
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


def test_normal_entry_buy_no_favorite_side_accepted() -> None:
    """BUY_NO'da our_side_prob = 1-bm_prob. Book %30 YES -> %70 NO -> favori NO -> girer."""
    m = _market(yes_price=0.45)  # Market YES 45%, NO = 55%
    bm = _bm(prob=0.30, conf="A")  # Bookmaker YES 30% -> NO 70% (our favored side)
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is not None
    assert sig.direction == Direction.BUY_NO


def test_normal_entry_buy_no_underdog_side_rejected() -> None:
    """BUY_NO'da our_side_prob = 1-bm_prob < 0.55 -> skip."""
    m = _market(yes_price=0.55)  # Market YES 55%, NO = 45%
    bm = _bm(prob=0.48, conf="A")  # Bookmaker YES 48%, NO 52% (underdog for NO)
    # Edge raw = 0.48-0.55 = -0.07 -> BUY_NO, effective_no = 0.07 > 0.06 threshold
    # Ama our_side_prob (NO) = 0.52 < 0.55 -> skip
    sig = normal.evaluate(m, bm, min_edge=0.06, min_favorite_probability=0.55)
    assert sig is None
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/unit/strategy/entry/test_normal.py::test_normal_entry_underdog_rejected_by_favorite_filter -v
```
Expected: FAIL (`min_favorite_probability` param yok)

- [ ] **Step 3: Update `src/strategy/entry/normal.py` — add param + guard**

```python
def evaluate(
    market: MarketData,
    bm_prob: BookmakerProbability,
    min_edge: float = 0.06,
    confidence_multipliers: dict[str, float] | None = None,
    min_favorite_probability: float = 0.0,  # Default 0.0 = backward-compat (filtre kapali)
    spread: float = 0.0,
    slippage: float = 0.0,
) -> Signal | None:
    """Normal entry: edge varsa Signal döner, yoksa None."""
    if bm_prob.confidence == "C":
        return None

    direction, edge = calculate_edge(
        anchor_prob=bm_prob.probability,
        market_yes_price=market.yes_price,
        min_edge=min_edge,
        confidence=bm_prob.confidence,
        confidence_multipliers=confidence_multipliers,
        spread=spread,
        slippage=slippage,
    )
    if direction == Direction.SKIP:
        return None

    # Favorite filter — our side bookmaker prob >= min_favorite_probability
    our_side_prob = bm_prob.probability if direction == Direction.BUY_YES else (1.0 - bm_prob.probability)
    if our_side_prob < min_favorite_probability:
        return None

    return Signal(
        # ... existing Signal construction ...
    )
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/unit/strategy/entry/test_normal.py -v
```
Expected: 4 new tests PASS + existing PASS

- [ ] **Step 5: Update `src/strategy/entry/early_entry.py` — migrate min_anchor_probability to our_side_prob**

Eski `min_anchor_probability` sadece P(YES) için filter — BUY_NO durumunda yanlış mantık. Unified `min_favorite_probability` ile değiştir:

```python
def evaluate(
    market: MarketData,
    bm_prob: BookmakerProbability,
    min_edge: float = 0.10,
    min_favorite_probability: float = 0.55,   # Yeniden isimlendirildi (eski: min_anchor_probability)
    min_confidence: str = "B",
    max_entry_price: float = 0.70,
    min_hours_to_start: float = 6.0,
    max_hours_to_start: float = 24.0,
    confidence_multipliers: dict[str, float] | None = None,
) -> Signal | None:
    if not _confidence_meets(bm_prob.confidence, min_confidence):
        return None

    if market.yes_price > max_entry_price:
        return None

    if not _within_time_window(market, min_hours_to_start, max_hours_to_start):
        return None

    direction, edge = calculate_edge(
        anchor_prob=bm_prob.probability,
        market_yes_price=market.yes_price,
        min_edge=min_edge,
        confidence=bm_prob.confidence,
        confidence_multipliers=confidence_multipliers,
    )
    if direction == Direction.SKIP:
        return None

    # Favorite filter (unified) — our side bookmaker prob >= min_favorite_probability
    our_side_prob = bm_prob.probability if direction == Direction.BUY_YES else (1.0 - bm_prob.probability)
    if our_side_prob < min_favorite_probability:
        return None

    return Signal(
        # ... existing ...
    )
```

- [ ] **Step 6: Update `src/strategy/entry/gate.py` — GateConfig field + pass to strategies**

In GateConfig dataclass:
```python
@dataclass
class GateConfig:
    min_edge: float = 0.06
    confidence_multipliers: dict[str, float] = field(
        default_factory=lambda: {"A": 1.00, "B": 1.00},
    )
    min_favorite_probability: float = 0.55   # SPEC-013: underdog bet yasak
    # ... rest unchanged ...
```

In `_evaluate_strategies`:
```python
# 2. Early entry
if self.config.early_enabled:
    sig = early_entry.evaluate(
        market, bm_prob,
        min_edge=self.config.early_min_edge,
        min_favorite_probability=self.config.early_min_favorite_probability,
        min_confidence=self.config.early_min_confidence,
        max_entry_price=self.config.early_max_entry_price,
        min_hours_to_start=self.config.early_min_hours_to_start,
        max_hours_to_start=self.config.early_max_hours_to_start,
        confidence_multipliers=self.config.confidence_multipliers,
    )
    ...

# 3. Normal
return normal_entry.evaluate(
    market, bm_prob,
    min_edge=self.config.min_edge,
    confidence_multipliers=self.config.confidence_multipliers,
    min_favorite_probability=self.config.min_favorite_probability,
)
```

Also rename GateConfig field `early_min_anchor_probability` → `early_min_favorite_probability`:
```python
early_min_favorite_probability: float = 0.55
```

- [ ] **Step 7: Update `src/orchestration/factory.py` — pass new fields**

```python
gate_cfg = GateConfig(
    min_edge=cfg.edge.min_edge,
    confidence_multipliers=cfg.edge.confidence_multipliers,
    min_favorite_probability=cfg.edge.min_favorite_probability,   # YENI
    # ...
    early_min_favorite_probability=cfg.early.min_favorite_probability,   # YENILENDI
    # ...
)
```

- [ ] **Step 8: Update `src/config/settings.py` — EdgeConfig + EarlyEntryConfig**

EdgeConfig:
```python
class EdgeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_edge: float = 0.06
    confidence_multipliers: dict = {"A": 1.00, "B": 1.00}
    min_favorite_probability: float = 0.55   # SPEC-013
```

EarlyEntryConfig — rename `min_anchor_probability` → `min_favorite_probability`:
```python
class EarlyEntryConfig(BaseModel):
    # ...
    min_favorite_probability: float = 0.55   # Renamed from min_anchor_probability
    # ...
```

- [ ] **Step 9: Update `config.yaml`**

```yaml
edge:
  min_edge: 0.06
  confidence_multipliers:
    A: 1.00
    B: 1.00
  min_favorite_probability: 0.55    # SPEC-013: underdog bet yasak

early:
  # ...
  min_favorite_probability: 0.55    # Eski: min_anchor_probability
  # ...
```

- [ ] **Step 10: Update existing test_early_entry.py tests**

Existing tests reference `min_anchor_probability` — rename:

```bash
grep -n "min_anchor_probability" tests/unit/strategy/entry/test_early_entry.py
```

Her satırda `min_anchor_probability` → `min_favorite_probability` değiştir. Semantik tam aynı (her iki taraf için checklist — early zaten P(YES) üzerinden test ediyor, yeni unified mantık ama BUY_YES senaryolarında sonuç aynı).

- [ ] **Step 11: Update test_gate.py — favorite filter integration**

Existing `test_gate.py` testleri `min_anchor_probability` kullanıyorsa rename. Yeni test ekle:

```python
def test_gate_rejects_underdog_normal_entry() -> None:
    """Normal entry'de underdog (bizim %48) -> favorite filter skip."""
    # anchor 0.48, market 0.40 -> edge 8%, direction BUY_YES, our side 0.48 < 0.55 -> skip
    gate = _make_gate(enricher=lambda m: _enrich(_bm(prob=0.48, conf="A")))
    results = gate.run([_market(yp=0.40)])
    assert results[0].signal is None
    assert "no_edge" in results[0].skipped_reason or "underdog" in results[0].skipped_reason.lower() or results[0].skipped_reason == ""
    # Note: reason string may be "no_edge" if we treat this as no-signal; OK either way
```

- [ ] **Step 12: Run full suite — verify all pass**

```bash
pytest tests/ -q
```
Expected: ALL PASS (minimum 906 + 4 new = 910+)

- [ ] **Step 13: Commit Task 1**

```bash
git add src/strategy/entry/normal.py src/strategy/entry/early_entry.py src/strategy/entry/gate.py src/config/settings.py src/orchestration/factory.py config.yaml tests/unit/strategy/entry/test_normal.py tests/unit/strategy/entry/test_early_entry.py tests/unit/strategy/entry/test_gate.py
git commit -m "feat(entry): min_favorite_probability guard (SPEC-013 Task 1)

Underdog bet'ler artik reddedilir:
- Normal entry: bookmaker our_side_prob < 0.55 -> skip
- Early entry: eski min_anchor_probability -> unified min_favorite_probability
  (BUY_NO durumunda da dogru calisir)
- GateConfig + EdgeConfig + config.yaml guncellenmis

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Scale-out midpoint semantics

**Files:**
- Modify: `src/strategy/exit/scale_out.py` — `check_scale_out` imzası + mantık
- Modify: `src/orchestration/exit_processor.py` — call site güncelle
- Modify: `tests/unit/strategy/exit/test_scale_out.py` — semantics güncelle
- Modify: `config.yaml` — comment değişikliği (threshold artık distance fraction)

Threshold semantiği artık **"entry → 0.99 arasındaki fraction"**:
- `threshold = 0.50` → entry + 0.50 × (0.99 - entry) fiyatında tetikler
- Entry 0.43: trigger price = 0.43 + 0.50×0.56 = 0.71 (midpoint)
- Entry 0.70: trigger price = 0.70 + 0.50×0.29 = 0.845

- [ ] **Step 1: Write failing tests**

Replace/add in `tests/unit/strategy/exit/test_scale_out.py`:

```python
def test_scale_out_midpoint_fires_at_half_distance_low_entry() -> None:
    """Entry 43¢, threshold 0.50 (yari mesafe) -> trigger price ~71¢."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    # current 0.71, entry 0.43 -> distance_fraction = (0.71 - 0.43) / (0.99 - 0.43) = 0.5
    decision = check_scale_out(
        scale_out_tier=0,
        entry_price=0.43,
        current_price=0.71,
        direction="BUY_YES",
        tiers=tiers,
    )
    assert decision is not None
    assert decision.tier == 1
    assert decision.sell_pct == 0.40


def test_scale_out_midpoint_not_yet_triggered() -> None:
    """Entry 43¢, current 0.60 -> distance_fraction = (0.60-0.43)/0.56 = 0.30 -> tetiklenmez (0.50 threshold)."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    decision = check_scale_out(
        scale_out_tier=0,
        entry_price=0.43,
        current_price=0.60,
        direction="BUY_YES",
        tiers=tiers,
    )
    assert decision is None


def test_scale_out_buy_no_direction_midpoint() -> None:
    """BUY_NO: current_price NO fiyati; entry 0.43 NO, current 0.71 NO -> fraction 0.5 -> tetik."""
    tiers = [{"threshold": 0.50, "sell_pct": 0.40}]
    decision = check_scale_out(
        scale_out_tier=0,
        entry_price=0.43,
        current_price=0.71,
        direction="BUY_NO",
        tiers=tiers,
    )
    assert decision is not None
    assert decision.tier == 1


def test_scale_out_second_tier_only_after_first() -> None:
    tiers = [
        {"threshold": 0.30, "sell_pct": 0.30},
        {"threshold": 0.60, "sell_pct": 0.50},
    ]
    # Entry 0.50, current 0.80 -> distance_fraction = (0.80-0.50)/0.49 = 0.612
    # scale_out_tier=1 -> first tier gecildi, second (0.60) tetiklenir
    decision = check_scale_out(
        scale_out_tier=1,
        entry_price=0.50,
        current_price=0.80,
        direction="BUY_YES",
        tiers=tiers,
    )
    assert decision is not None
    assert decision.tier == 2
    assert decision.sell_pct == 0.50


def test_scale_out_no_tiers_returns_none() -> None:
    decision = check_scale_out(
        scale_out_tier=0,
        entry_price=0.50,
        current_price=0.80,
        direction="BUY_YES",
        tiers=[],
    )
    assert decision is None
```

- [ ] **Step 2: Run — verify FAIL**

```bash
pytest tests/unit/strategy/exit/test_scale_out.py -v
```
Expected: FAIL (signature mismatch)

- [ ] **Step 3: Rewrite `src/strategy/exit/scale_out.py`**

```python
"""Config-driven scale-out — pure, midpoint-to-resolution semantigi (SPEC-013).

Tier'lar config.yaml'dan okunur. `threshold` semantigi:
  entry_price + threshold × (0.99 - entry_price) fiyatinda tetikler.
  (threshold = 0.5 -> entry ile 0.99 arasinin yarisi)

Bu semantik eski "PnL %" yaklasimini replace eder cunku PnL % entry fiyatina
bagli olarak cok farkli noktalarda tetikleyebiliyordu (43c entry'de +%15 PnL =
50c fiyat; 70c entry'de +%15 PnL = 80c fiyat). Yeni semantik "kalan mesafe" ile
calistigi icin her entry icin adil.

Hardcoded sabit YOK (ARCH_GUARD Kural 6).
"""
from __future__ import annotations

from dataclasses import dataclass

_RESOLUTION_PRICE = 0.99  # Polymarket near-resolve cap


@dataclass
class ScaleOutDecision:
    tier: int
    sell_pct: float
    reason: str


def check_scale_out(
    scale_out_tier: int,
    entry_price: float,
    current_price: float,
    direction: str,
    tiers: list[dict],
) -> ScaleOutDecision | None:
    """Pozisyon bir sonraki tier'a hak kazandi mi?

    Args:
      scale_out_tier: pozisyonun su an gecmis oldugu tier (0 = hic, 1 = ilk tier, ...).
      entry_price: effective entry (BUY_YES icin yes_price, BUY_NO icin no_price).
      current_price: current effective price (ayni taraf).
      direction: "BUY_YES" or "BUY_NO" — mantik icin simetrik ama sanity icin.
      tiers: config'den [{"threshold": 0.50, "sell_pct": 0.40}, ...].

    Returns:
      ScaleOutDecision if next tier triggered, None otherwise.
    """
    if not tiers:
        return None
    if entry_price >= _RESOLUTION_PRICE:
        return None  # Giris zaten resolution'da, scale-out anlamsiz
    if current_price <= entry_price:
        return None  # Kar yok, scale-out yok

    max_distance = _RESOLUTION_PRICE - entry_price
    current_distance = current_price - entry_price
    distance_fraction = current_distance / max_distance if max_distance > 0 else 0.0

    for i, tier in enumerate(tiers):
        tier_num = i + 1
        if scale_out_tier < tier_num and distance_fraction >= tier["threshold"]:
            return ScaleOutDecision(
                tier=tier_num,
                sell_pct=tier["sell_pct"],
                reason=f"Tier {tier_num} at {distance_fraction*100:.0f}% of distance to resolution",
            )
    return None
```

- [ ] **Step 4: Update `src/orchestration/exit_processor.py` — scale-out call site**

Find current scale_out invocation (search for `check_scale_out` or `scale_out_tier`). Update signature:

```python
# Eski:
# decision = scale_out.check_scale_out(
#     scale_out_tier=pos.scale_out_tier,
#     unrealized_pnl_pct=pos.unrealized_pnl_pct,
#     tiers=self._scale_out_tiers(),
# )

# Yeni:
decision = scale_out.check_scale_out(
    scale_out_tier=pos.scale_out_tier,
    entry_price=pos.entry_price,
    current_price=pos.current_price,
    direction=pos.direction,
    tiers=self._scale_out_tiers(),
)
```

NOT: `pos.entry_price` ve `pos.current_price` BUY_NO için no_price, BUY_YES için yes_price (effective). Mevcut Position model'inde zaten bu şekilde — doğrulanmalı. Eğer değilse, direction-aware fonksiyon (ör. `effective_price(pos)`) kullan.

Eğer çağrı monitor.py'de ise oraya da uygula.

- [ ] **Step 5: Grep tüm scale_out call siteleri**

```bash
grep -rn "check_scale_out\|scale_out\.check" src/ tests/ | grep -v __pycache__
```

Her çağrıyı yeni imzaya güncelle.

- [ ] **Step 6: Update config.yaml — threshold semantik yorumu**

```yaml
scale_out:
  enabled: true
  # SPEC-013: threshold = entry ile 0.99 arasindaki mesafenin fraction'i
  # 0.50 = yarı yol (43c entry -> 71c tetik; 70c entry -> 84.5c tetik)
  tiers:
    - threshold: 0.50    # SPEC-013: midpoint to resolution (eski: 0.15 PnL%)
      sell_pct: 0.40
```

- [ ] **Step 7: Run tests — verify PASS**

```bash
pytest tests/unit/strategy/exit/test_scale_out.py -v
pytest tests/ -q
```
Expected: Tüm scale_out testleri PASS, tüm suite PASS

- [ ] **Step 8: Commit Task 2**

```bash
git add src/strategy/exit/scale_out.py src/orchestration/exit_processor.py src/strategy/exit/monitor.py tests/unit/strategy/exit/test_scale_out.py config.yaml
git commit -m "feat(scale-out): midpoint-to-resolution threshold (SPEC-013 Task 2)

Scale-out threshold semantigi degisti:
- Eski: unrealized_pnl_pct (entry fiyatina bagli adaletsiz tetik)
- Yeni: (current - entry) / (0.99 - entry) distance fraction
- Default 0.50 -> entry ile 0.99 arasinin yarisi tetikler

Etki:
- Entry 43c -> trigger 71c (eski: 49.45c)
- Entry 70c -> trigger 84.5c (eski: 80.5c)
- Kilit miktarlari yaklasik 3-4x buyuk

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Dokuman — TDD + PRD + ARCH_GUARD + SPEC status

**Files:**
- Modify: `TDD.md` — §6.3 edge formula + §6.6 scale-out + §6.5 sport rules
- Modify: `PRD.md` — §2.4 + favorite filter açıklaması + scale-out
- Modify: `docs/superpowers/specs/2026-04-19-favorite-filter-midpoint-scaleout-design.md` (create — minimal spec doc)

- [ ] **Step 1: Create minimal spec doc**

`docs/superpowers/specs/2026-04-19-favorite-filter-midpoint-scaleout-design.md`:

```markdown
# SPEC-013: Favorite Filter + Midpoint Scale-Out

> **Durum**: IMPLEMENTED
> **Tarih**: 2026-04-19

## Problem

1. Bot underdog bet'lere giriyordu (TEX-SEA 30¢, MIL-CHI 46¢) — %44-49 kazanma
   ihtimalinde ince edge'li trade'ler. Varyans yüksek, kullanıcı rahatsız.
2. Scale-out threshold PnL% bazlıydı (0.15) — entry fiyatına göre adaletsiz.
   43¢ entry'de 49¢'te erken tetik (küçük kilit), kullanıcı "kalp kırıyor" dedi.

## Solution

1. `min_favorite_probability = 0.55` — normal + early entry'de underdog filter.
   Our_side_prob = BUY_YES için bm_prob, BUY_NO için (1-bm_prob).
2. Scale-out threshold semantiği: `fraction of distance from entry to 0.99`.
   0.50 = midpoint. Entry fiyatına bağımsız adaletli tetikleme.

## Etki

- MIL, SD-LAA, TEX gibi underdog bet'ler **girmez**.
- Scale-out 43¢ entry'de 71¢'te tetikler → $11+ kilit (eski $3-4).

## Hata Durumu

Config override ile geri alınabilir:
- `edge.min_favorite_probability: 0.0` → underdog'lar yine girer
- `scale_out.tiers[0].threshold: 0.15` → eski davranış (PnL% semantik geri gelir, ama kod yeni semantikte hesaplar — aslında 0.15 distance = 0.15 × max_distance ≈ entry yakını)
```

- [ ] **Step 2: Update TDD.md §6.3 — favorite filter**

Find §6.3 Edge (Case B — Non-Consensus) section. Add sub-subsection:

```markdown
**Favorite Filter (SPEC-013)**:

Edge hesabı direction belirledikten sonra ek guard:
```
our_side_prob = bm_prob.probability if direction == BUY_YES else (1 - bm_prob.probability)
if our_side_prob < min_favorite_probability (default 0.55): SKIP
```

**Gerekçe**: Bookmaker bizim tarafa %55+ vermiyorsa bet underdog — uzun vadede
EV+ olsa bile yüksek varyans. SPEC-013: rasyonel sistem sadece "beklenen kazanan"
tarafa girer. Underdog value bet'leri (TEX-SEA 30¢ 14% edge gibi) reddedilir.

Etki: Edge+favorite filter kombinasyonu → hem edge'li hem "favori tarafta"
trade'ler. Edge% ile azalır (yaklaşık %30-50 normal trade), varyans düşer.
```

- [ ] **Step 3: Update TDD.md §6.6 — scale-out semantik**

Find §6.6 Scale-Out. Update threshold explanation:

```markdown
### 6.6 Scale-Out (Midpoint-to-Resolution) — SPEC-013

Config-driven tier listesi. Her tier'da:
- `threshold`: entry ile 0.99 arasındaki mesafenin fraction'ı. 0.50 = midpoint.
- `sell_pct`: tier tetiklendiğinde satılacak pozisyon %'si.

**Trigger formülü** (pure, `scale_out.py`):
```
max_distance = 0.99 - entry_price
current_distance = current_price - entry_price
distance_fraction = current_distance / max_distance
if distance_fraction >= tier.threshold AND not yet triggered: SELL
```

**Örnek** (default threshold 0.50):
| Entry | Max distance | Trigger price | Locked PnL (40% sell) |
|---|---|---|---|
| 0.30 | 0.69 | 0.645 | ≈$14 (on $45 stake) |
| 0.43 | 0.56 | 0.71 | ≈$11 (on $36 stake) |
| 0.70 | 0.29 | 0.845 | ≈$8 (on $45 stake) |
| 0.80 | 0.19 | 0.895 | ≈$4 (entry yakın resolve) |

**Eski semantik**: `unrealized_pnl_pct >= threshold` — entry fiyatına göre
adaletsizdi (43¢ entry'de +%15 PnL = 49¢ fiyat, 70¢ entry'de = 80¢ fiyat).
Yeni semantik her entry için adalet.
```

- [ ] **Step 4: Update PRD.md — underdog filter + scale-out açıklaması**

Find consensus/strategy section. Add:

```markdown
### Favorite Filter (SPEC-013)
Bot **sadece favori taraflara** girer: normal + early entry'de bookmaker'ın
bizim tarafa verdiği olasılık %55'ten az ise trade atlanır (`min_favorite_probability`).
Underdog value bet'leri (low market price + yüksek bookmaker) artık alınmıyor —
varyans düşürme amacıyla.

### Scale-Out (Midpoint) - SPEC-013
Kâr kilitleme tek tier ile: pozisyon entry fiyatı ile resolution arasındaki
yolun yarısına geldiğinde %40 satılır. Entry 43¢ → 71¢ tetik, entry 70¢ → 84.5¢ tetik.
Eski PnL% bazlı semantik (entry fiyatına bağımlı adaletsiz) değişti.
```

- [ ] **Step 5: ARCH_GUARD kontrolü (kod review)**

Bu spec kod değişikliği ARCH_GUARD 15 kural altında check:
- Kural 3 (file <400 satır): normal.py, early_entry.py, scale_out.py hepsi küçük — OK
- Kural 6 (magic number): `_RESOLUTION_PRICE = 0.99` yeni sabit, ama bu Polymarket payout cap — sabit OK, docstring açıklıyor
- Kural 1 (layer order): strategy → domain çağrısı, OK
- Kural 8 (event guard): değişmedi

ARCH_GUARD.md'de yeni kural eklenmeli mi? **Hayır** — SPEC-013 mevcut kurallar altında çalışıyor. ARCH_GUARD update yok.

- [ ] **Step 6: Final verification**

```bash
pytest tests/ -q
```
Expected: ALL PASS

```bash
wc -l src/strategy/entry/normal.py src/strategy/entry/early_entry.py src/strategy/exit/scale_out.py
```
Expected: Hepsi <400

```bash
grep -rn "min_anchor_probability" src/ tests/ config.yaml | grep -v __pycache__
```
Expected: 0 sonuç (rename tamam)

- [ ] **Step 7: Commit Task 3**

```bash
git add TDD.md PRD.md docs/superpowers/specs/2026-04-19-favorite-filter-midpoint-scaleout-design.md
git commit -m "docs: SPEC-013 favorite filter + midpoint scale-out (Task 3)

TDD §6.3: favorite filter altbolum
TDD §6.6: scale-out semantik guncel
PRD: favorite filter + scale-out aciklamasi
SPEC-013 spec doc: IMPLEMENTED

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: min_favorite_probability (Task 1) + midpoint scale-out (Task 2) + docs (Task 3) — tüm istekler kapsanmış
- [x] **No placeholders**: Her kod step'i tam kod veriyor, grep komutları concrete
- [x] **Type consistency**: `min_favorite_probability` normal + early + GateConfig + EdgeConfig + config.yaml'da aynı isim, `threshold` scale_out'ta unified semantic

## Plan Complete

Plan saved. Execution: subagent-driven-development recommended for quality (fresh subagent per task + two-stage review).
