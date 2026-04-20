# Directional Entry Implementation Plan (SPEC-017)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Edge-tabanlı 3 entry stratejisini (normal/early/consensus) silip tek `directional.py` stratejisine geç. Bookmaker favoriye fiyat aralığında doğrudan giriş.

**Architecture:** Strategy katmanında tek entry path, domain katmanındaki edge modülü tamamen silinir. Config basitleşir (3 blok → 1 blok). Risk/exit sistemi dokunulmaz.

**Tech Stack:** Python 3.12+, Pydantic config, pytest.

**Branch:** master (mevcut workflow).

---

## Task 1: Create `directional.py` + `EntryConfig` (additive)

**Files:**
- Create: `src/strategy/entry/directional.py`
- Create: `tests/unit/strategy/entry/test_directional.py`
- Modify: `src/config/settings.py` (add `EntryConfig`, integrate to `AppConfig`)
- Modify: `config.yaml` (add `entry:` block — henüz eski bloklar silinmiyor)
- Modify: `tests/unit/config/test_settings.py`

Bu task sadece YENİ şeyler ekler, mevcut kodu bozmaz. Eski stratejiler hâlâ aktif, sadece yan yana yeni kod üretilir.

- [ ] **Step 1: Failing tests for `EntryConfig`**

`tests/unit/config/test_settings.py`'a ekle:

```python
def test_entry_config_defaults():
    cfg = EntryConfig()
    assert cfg.min_favorite_probability == 0.55
    assert cfg.min_entry_price == 0.60
    assert cfg.max_entry_price == 0.85


def test_entry_config_custom_values():
    cfg = EntryConfig(min_favorite_probability=0.60, min_entry_price=0.65, max_entry_price=0.80)
    assert cfg.min_favorite_probability == 0.60
    assert cfg.min_entry_price == 0.65
    assert cfg.max_entry_price == 0.80
```

Ayrıca mevcut `EntryConfig` import'u test dosyasına eklenmeli.

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/unit/config/test_settings.py -v -k "entry_config" `
Expected: FAIL (import error)

- [ ] **Step 3: Add `EntryConfig` to `src/config/settings.py`**

`RiskConfig`'den sonra ekle:

```python
class EntryConfig(BaseModel):
    """Directional entry (SPEC-017) — edge-free entry kararı."""
    model_config = ConfigDict(extra="ignore")
    min_favorite_probability: float = 0.55  # güçlü favori eşiği
    min_entry_price: float = 0.60           # çok düşük fiyatlı girişi engelle
    max_entry_price: float = 0.85           # aşırı pahalı girişi engelle
```

`AppConfig` class'ına field ekle:

```python
class AppConfig(BaseModel):
    # ... mevcut field'lar ...
    entry: EntryConfig = EntryConfig()
```

**Dikkat:** `edge: EdgeConfig`, `early: EarlyEntryConfig`, `consensus: ConsensusConfig` field'ları HÂLÂ DURUYOR. Bu task sadece ekleme yapar.

- [ ] **Step 4: Add `entry:` to `config.yaml`**

`risk:` bloğundan sonra, `early:` bloğundan önce ekle:

```yaml
entry:
  min_favorite_probability: 0.55   # SPEC-017: güçlü favori eşiği
  min_entry_price: 0.60            # SPEC-017: min effective entry price
  max_entry_price: 0.85            # SPEC-017: max effective entry price
```

**Dikkat:** `edge:`, `early:`, `consensus:` blokları kalır.

- [ ] **Step 5: Run config tests, expect PASS**

Run: `pytest tests/unit/config/test_settings.py -v`
Expected: All PASS including new 2 tests.

- [ ] **Step 6: Failing tests for `directional.py`**

`tests/unit/strategy/entry/test_directional.py` oluştur:

```python
"""Directional entry (SPEC-017) unit tests."""
from __future__ import annotations

import pytest

from src.models.enums import Direction
from src.models.market import MarketData
from src.strategy.entry.directional import evaluate_directional


def _make_market(yes_price: float = 0.70, liquidity: float = 10_000.0) -> MarketData:
    return MarketData(
        condition_id="0xabc",
        token_yes_id="tkYES",
        token_no_id="tkNO",
        slug="test-match-2026-04-20",
        question="Team A vs Team B",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=liquidity,
        volume_24h=1000.0,
        sport_tag="test",
        event_id="evt1",
        end_date_iso="2026-04-27T00:00:00Z",
        match_start_iso="2026-04-20T12:00:00Z",
    )


def test_directional_buy_yes_when_anchor_above_50():
    market = _make_market(yes_price=0.70)
    signal = evaluate_directional(
        market=market,
        anchor=0.75,
        confidence="A",
        min_favorite_probability=0.55,
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_YES.value
    assert signal.probability == 0.75


def test_directional_buy_no_when_anchor_below_50():
    market = _make_market(yes_price=0.30)
    signal = evaluate_directional(
        market=market,
        anchor=0.25,
        confidence="A",
        min_favorite_probability=0.55,
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_NO.value
    assert signal.probability == 0.25
    # effective entry = 1 - 0.30 = 0.70


def test_directional_skips_when_win_prob_below_threshold():
    # anchor 0.52 < 0.55 threshold
    market = _make_market(yes_price=0.65)
    signal = evaluate_directional(
        market=market,
        anchor=0.52,
        confidence="A",
        min_favorite_probability=0.55,
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is None


def test_directional_skips_when_effective_price_below_min():
    # BUY_YES, yes_price=0.58, below 0.60 floor
    market = _make_market(yes_price=0.58)
    signal = evaluate_directional(
        market=market,
        anchor=0.65,
        confidence="A",
        min_favorite_probability=0.55,
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is None


def test_directional_skips_when_effective_price_above_max():
    # BUY_YES, yes_price=0.90, above 0.85 ceiling
    market = _make_market(yes_price=0.90)
    signal = evaluate_directional(
        market=market,
        anchor=0.92,
        confidence="A",
        min_favorite_probability=0.55,
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is None


def test_directional_buy_no_effective_price_computed_correctly():
    # BUY_NO path. yes_price=0.20 → effective entry = 0.80, within range
    market = _make_market(yes_price=0.20)
    signal = evaluate_directional(
        market=market,
        anchor=0.18,
        confidence="A",
        min_favorite_probability=0.55,
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_NO.value


def test_directional_anchor_exactly_fifty_chooses_yes():
    # Edge case: anchor=0.50 tie-breaker → BUY_YES
    market = _make_market(yes_price=0.65)
    signal = evaluate_directional(
        market=market,
        anchor=0.50,  # tie
        confidence="A",
        min_favorite_probability=0.50,  # lower threshold to pass
        min_entry_price=0.60,
        max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_YES.value
```

- [ ] **Step 7: Run, expect FAIL**

Run: `pytest tests/unit/strategy/entry/test_directional.py -v`
Expected: FAIL (directional.py yok)

- [ ] **Step 8: Implement `src/strategy/entry/directional.py`**

```python
"""Directional entry (SPEC-017) — bookmaker favoriye fiyat aralığında giriş.

Edge hesabı YOK. Favori + fiyat aralığı + existing guards.

Direction seçimi bookmaker anchor'dan:
  anchor >= 0.50 → BUY_YES
  anchor <  0.50 → BUY_NO

Effective entry price = market side we're buying:
  BUY_YES → yes_price
  BUY_NO  → 1 - yes_price

Min/max entry price checks effective side.
"""
from __future__ import annotations

from src.models.enums import Direction
from src.models.market import MarketData
from src.models.position import effective_win_prob
from src.models.signal import Signal


def evaluate_directional(
    market: MarketData,
    anchor: float,
    confidence: str,
    min_favorite_probability: float = 0.55,
    min_entry_price: float = 0.60,
    max_entry_price: float = 0.85,
) -> Signal | None:
    """Directional entry kararı.

    Returns Signal eligible ise, None değilse.
    """
    direction = Direction.BUY_YES if anchor >= 0.50 else Direction.BUY_NO
    win_prob = effective_win_prob(anchor, direction.value)

    if win_prob < min_favorite_probability:
        return None

    effective_price = (
        market.yes_price if direction == Direction.BUY_YES
        else 1.0 - market.yes_price
    )
    if not (min_entry_price <= effective_price <= max_entry_price):
        return None

    return Signal(
        condition_id=market.condition_id,
        direction=direction.value,
        probability=anchor,
        confidence=confidence,
        market_price=market.yes_price,
    )
```

**Not:** `Signal` modelinin mevcut zorunlu field'larına uy. Signal'de `edge: float` field'ı varsa (Task 2'de silinecek), geçici olarak `edge=0.0` geç ya da Task 2'de field'ı sildikten sonra bu dosyayı güncelle.

**BU TASK'TA `Signal.edge=0.0` GEÇİCİ OLARAK KULLAN** — Task 2'de field tamamen siliniyor.

- [ ] **Step 9: Run, expect PASS**

Run: `pytest tests/unit/strategy/entry/test_directional.py -v`
Expected: 7 PASS

- [ ] **Step 10: Full suite — no regressions**

Run: `pytest -q`
Expected: Tüm mevcut testler + 9 yeni test (2 config + 7 directional) PASS.

- [ ] **Step 11: ARCH_GUARD self-check + Commit**

ARCH_GUARD 8-item (tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok (config), ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor).

```bash
git add src/strategy/entry/directional.py \
        src/config/settings.py \
        config.yaml \
        tests/unit/strategy/entry/test_directional.py \
        tests/unit/config/test_settings.py
git commit -m "feat(entry): add directional strategy + EntryConfig (SPEC-017 T1)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Gate + Three-way refactor (switch to directional, remove 3 old strategies)

**Files:**
- Modify: `src/strategy/entry/gate.py`
- Modify: `src/strategy/entry/three_way.py`
- Modify: `src/orchestration/factory.py`
- Modify: `tests/unit/strategy/entry/test_gate.py`
- Modify: `tests/unit/strategy/entry/test_three_way.py`

Bu task gate.py'ı tek directional path'e çevirir, three_way.py'dan edge check kaldırır. Eski dosyalar (normal.py, early_entry.py, consensus.py, edge.py) henüz silinmez — Task 3.

- [ ] **Step 1: Tests — gate uses directional only**

`tests/unit/strategy/entry/test_gate.py` güncellemesi:
- Mevcut gate testlerinde normal/early/consensus'e bağımlı testleri dönüştür: aynı senaryo directional ile test edilecek (BUY_YES anchor, price range, favorite filter).
- Yeni testler:
  - `test_gate_directional_enters_when_favorite_and_price_in_range`
  - `test_gate_directional_skips_when_below_fav_prob`
  - `test_gate_directional_skips_when_price_out_of_range`
  - `test_gate_no_edge_related_skip_reasons` — skip_reason artık `"no_edge"` olamaz

Mevcut `test_gate_passes_win_prob_when_flag_enabled` (SPEC-016) ve `test_gate_buy_no_uses_inverse_prob` kalır — directional'de de geçerli.

Tüm `min_edge`, `early_min_edge`, `bookmaker_pre_screen_edge` referansları test fixture'larından silinir.

- [ ] **Step 2: three_way tests — remove edge checks**

`tests/unit/strategy/entry/test_three_way.py`:
- `test_three_way_skips_when_edge_below_min` → SİL (artık edge yok)
- Diğer testler: `min_edge` parametresi kaldırılır
- Yeni test: `test_three_way_skips_when_fav_prob_below_threshold` (favorite filter korundu)

- [ ] **Step 3: Run tests, expect FAIL**

Run: `pytest tests/unit/strategy/entry/test_gate.py tests/unit/strategy/entry/test_three_way.py -v`
Expected: Çok sayıda FAIL (code henüz güncellenmedi)

- [ ] **Step 4: Refactor `src/strategy/entry/gate.py`**

**Siliniyor:**
- `min_edge`, `early_min_edge`, `bookmaker_pre_screen_edge` field'ları `GateConfig`'den
- `calculate_edge()` importu ve kullanımı
- `_evaluate_normal()`, `_evaluate_early()`, `_evaluate_consensus()` metotları
- `normal_entry`, `early_entry`, `consensus_entry` module import'ları
- `no_edge` skip reason (yerine `below_fav_prob`, `price_out_of_range`)

**Ekleniyor:**
- `from src.strategy.entry.directional import evaluate_directional`
- `_evaluate_directional()` metot ya da inline gate logic
- `GateConfig` field'ları: `min_favorite_probability`, `min_entry_price`, `max_entry_price`
- `EntryConfig` parametreleri geçirilir factory'den

**3-way path:** `three_way.py.evaluate()` çağrısında `min_edge` argümanı kaldırılır. Three-way hâlâ 3 outcome arasından favori seçip favorite filter + yeni price range uygular.

**`Signal.edge` kullanımı:** Gate artık sizing'de Signal.edge'i kullanmıyor (SPEC-016 `signal.probability` kullanıyor). Kod tarafında edge referansları temizlenir.

- [ ] **Step 5: Refactor `src/strategy/entry/three_way.py`**

**Siliniyor:**
- `min_edge: float = 0.06` parametresi
- `edge = fav_prob - market_yes` hesabı
- `if edge < min_edge: ... no_edge` branch
- Log mesajlarında edge referansları
- Signal'de `edge=edge` field'ı → `edge=0.0` geçici (Task 3'te tamamen siliniyor)

**Kalıyor:**
- Tie-break, favorite filter (absolute + margin)
- Favori market seçimi
- Price range check (yeni: min_entry_price, max_entry_price)

**Yeni imza:**
```python
def evaluate(
    home_market, draw_market, away_market,
    probs,
    min_favorite_probability: float = 0.40,
    favorite_margin: float = 0.07,
    min_entry_price: float = 0.60,
    max_entry_price: float = 0.85,
) -> Signal | None:
    ...
```

- [ ] **Step 6: Update `src/orchestration/factory.py`**

`EntryGate` constructor'a geçirilen parametreleri güncelle:
- **Sil**: `min_edge`, `early_min_edge`, `bookmaker_pre_screen_edge`, `confidence_multipliers` (edge'le ilgili), `early_*` tüm field'lar, `consensus_*` tüm field'lar
- **Ekle**: `min_favorite_probability=cfg.entry.min_favorite_probability`, `min_entry_price=cfg.entry.min_entry_price`, `max_entry_price=cfg.entry.max_entry_price`
- `min_favorite_probability` config'i artık `cfg.entry`'den, `cfg.edge`'den DEĞİL

- [ ] **Step 7: Run tests, expect PASS**

Run: `pytest tests/unit/strategy/entry/test_gate.py tests/unit/strategy/entry/test_three_way.py -v`
Expected: All PASS.

- [ ] **Step 8: Full suite — normal.py/early/consensus testleri hâlâ var ve hâlâ geçiyor olmalı (code silinmedi)**

Run: `pytest -q`
Expected: All PASS (eski strateji dosyaları hâlâ mevcut, gate onları çağırmıyor ama testler bağımsız çalışıyor).

- [ ] **Step 9: ARCH_GUARD self-check + Commit**

```bash
git add src/strategy/entry/gate.py src/strategy/entry/three_way.py \
        src/orchestration/factory.py \
        tests/unit/strategy/entry/test_gate.py \
        tests/unit/strategy/entry/test_three_way.py
git commit -m "refactor(entry): gate uses directional only, three_way edge-free (SPEC-017 T2)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Dead code removal + Signal cleanup + references

**Files:**
- Delete: `src/domain/analysis/edge.py`
- Delete: `src/strategy/entry/normal.py`
- Delete: `src/strategy/entry/early_entry.py`
- Delete: `src/strategy/entry/consensus.py`
- Delete: `tests/unit/domain/analysis/test_edge.py`
- Delete: `tests/unit/strategy/entry/test_normal.py`
- Delete: `tests/unit/strategy/entry/test_early_entry.py`
- Delete: `tests/unit/strategy/entry/test_consensus.py`
- Modify: `src/models/signal.py` (remove `edge` field)
- Modify: `src/config/settings.py` (remove EdgeConfig, EarlyEntryConfig, ConsensusConfig)
- Modify: `config.yaml` (remove edge:, early:, consensus: blocks)
- Modify: `src/orchestration/stock_queue.py` (rename `no_edge_attempts` → `stale_attempts`)
- Modify: `src/infrastructure/persistence/skipped_trade_logger.py` (update skip reason taxonomy)
- Modify: `src/infrastructure/persistence/stock_snapshot.py` (rename field)
- Modify: `src/presentation/notifier.py` (remove edge from message)
- Modify: `src/strategy/entry/directional.py` (remove temp `edge=0.0`)
- Modify: `src/strategy/entry/three_way.py` (remove temp `edge=0.0`)
- Modify: Tests — all references updated

- [ ] **Step 1: Delete old entry strategy files**

```bash
git rm src/domain/analysis/edge.py
git rm src/strategy/entry/normal.py
git rm src/strategy/entry/early_entry.py
git rm src/strategy/entry/consensus.py
git rm tests/unit/domain/analysis/test_edge.py
git rm tests/unit/strategy/entry/test_normal.py
git rm tests/unit/strategy/entry/test_early_entry.py
git rm tests/unit/strategy/entry/test_consensus.py
```

- [ ] **Step 2: Remove `Signal.edge` field**

`src/models/signal.py`: `edge: float` field'ını sil. Tüm referansları güncelle (directional.py, three_way.py, gate.py, notifier.py, tests).

- [ ] **Step 3: Remove old config classes**

`src/config/settings.py`:
- Delete `EdgeConfig`
- Delete `EarlyEntryConfig`
- Delete `ConsensusConfig`
- Remove from `AppConfig`: `edge`, `early`, `consensus` fields

`config.yaml`:
- Delete `edge:` block (lines 136-141)
- Delete `early:` block
- Delete `consensus:` block

`tests/unit/config/test_settings.py`: Remove tests for deleted configs.

- [ ] **Step 4: Rename `no_edge_attempts` → `stale_attempts` in stock_queue**

`src/orchestration/stock_queue.py`:
- `StockEntry.no_edge_attempts` → `stale_attempts`
- `max_no_edge_attempts` → `max_stale_attempts`
- All string literals `"no_edge"` → `"stale"` (or use new skip reasons)
- Logic: any skip_reason counts toward staleness (not just `no_edge`)

`src/infrastructure/persistence/stock_snapshot.py`: same rename.

`src/config/settings.py` → `StockConfig.max_no_edge_attempts` → `max_stale_attempts`.

`config.yaml` → `stock.max_no_edge_attempts` → `stock.max_stale_attempts`.

`tests/unit/orchestration/test_stock_queue.py`: update references.

- [ ] **Step 5: Update skip reason taxonomy**

`src/infrastructure/persistence/skipped_trade_logger.py`: comment/enum listesinde:
- Remove: `"no_edge"`
- Add: `"below_fav_prob"`, `"price_out_of_range"`

All callers (gate.py) use new reasons.

- [ ] **Step 6: Update notifier**

`src/presentation/notifier.py`:
- Line 66-70: remove `edge` parameter from signal handler
- Line 70: message format — remove `Edge {edge:.1%}`, keep confidence + entry reason

Tests: update `tests/unit/presentation/test_notifier.py`.

- [ ] **Step 7: Remove temporary `edge=0.0`**

`src/strategy/entry/directional.py` ve `src/strategy/entry/three_way.py`: Signal construction'dan `edge=0.0` kaldır (field artık yok).

- [ ] **Step 8: Run full suite**

Run: `pytest -q`
Expected: All PASS. Test count reduced (deleted tests removed).

- [ ] **Step 9: Grep sanity check**

```bash
grep -r "min_edge\|calculate_edge\|EdgeConfig\|EarlyEntryConfig\|ConsensusConfig\|no_edge_attempts\|Signal.edge" src/ tests/
```

Expected: No matches (or only in docs referenced in Task 4).

- [ ] **Step 10: ARCH_GUARD self-check + Commit**

```bash
git add -A
git commit -m "refactor(entry): delete dead code — edge, normal, early, consensus (SPEC-017 T3)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: TDD + PRD + SPEC docs sync

**Files:**
- Modify: `TDD.md`
- Modify: `PRD.md`
- Modify: `docs/superpowers/specs/2026-04-20-directional-entry-design.md` (status → IMPLEMENTED)

- [ ] **Step 1: TDD.md updates**

Sections to DELETE entirely:
- §6.3 Edge hesabı (calculate_edge)
- §6.4 Consensus strategy
- Any references to `min_edge`, `calculate_edge`, early strategy, normal strategy

Sections to UPDATE:
- §6.4b Three-way: remove edge check reference, replace with "favorite filter + price range"
- §6.5 Position sizing: already SPEC-016 updated, no change needed

Section to ADD (replacing deleted sections):

```markdown
### 6.3 Directional Entry (SPEC-017)

Edge-tabanlı karar yok. Tek strateji:

1. **Direction**: bookmaker anchor'dan
   - `anchor >= 0.50` → BUY_YES, `win_prob = anchor`
   - `anchor < 0.50` → BUY_NO, `win_prob = 1 - anchor`

2. **Favorite filter**: `win_prob >= min_favorite_probability` (default %55)
   Toss-up'lar bloklu.

3. **Price range**: `min_entry_price <= effective_entry_price <= max_entry_price`
   - effective = BUY_YES ? yes_price : 1 - yes_price
   - Default aralık: 60¢ - 85¢
   - Altta: underdog girişi engellenir
   - Üstte: R/R kötü (max payout 99¢ - entry)

4. **Diğer guards** (event, liquidity, manipulation, exposure cap): değişmez

5. **Stake** (SPEC-016): `bankroll × bet_pct × win_prob`

**Neden edge kaldırıldı:** Market efficient dönemlerde (Polymarket ≈ bookmaker) edge eşiği çok az maçı geçiriyor, volume düşüyor. Directional entry bookmaker lider varsayımıyla favoriye girer, stake win_prob ile orantılı olduğu için varyans kontrollü kalır.

**Config:** `entry.min_favorite_probability`, `entry.min_entry_price`, `entry.max_entry_price`.
```

- [ ] **Step 2: PRD.md updates**

DELETE all edge-related rules:
- Line 12: "pozitif beklenen değer (edge) tespit eder" → "bookmaker favoriyi tespit eder"
- Line 97: "3× no_edge" → "3× stale"
- Line 101: "edge" referansı scroll; directional'e update
- Line 104: "edge + entry_price_cap" → "favorite_filter + entry_price_range"
- Line 148: 3 strateji bahsi → "directional entry" tek strateji
- Line 373: edge definition → "win_prob = direction-adjusted bookmaker probability"
- All other edge references

ADD new rule: Directional Entry (SPEC-017) — tek strateji özet paragrafı.

- [ ] **Step 3: SPEC doc status + commit list**

`docs/superpowers/specs/2026-04-20-directional-entry-design.md`:
- `**Status:** DRAFT` → `**Status:** IMPLEMENTED (2026-04-20)`
- Append commit list:

```markdown
## Implementation Commits

- T1: `<sha1>` feat(entry): add directional strategy + EntryConfig
- T2: `<sha2>` refactor(entry): gate uses directional only, three_way edge-free
- T3: `<sha3>` refactor(entry): delete dead code — edge, normal, early, consensus
- T4: `<sha4>` docs(tdd/prd): sync docs with SPEC-017
```

- [ ] **Step 4: Final verification**

```bash
pytest -q
grep -rn "min_edge\|calculate_edge\|EdgeConfig\|EarlyEntryConfig\|ConsensusConfig" src/ tests/ config.yaml
```

Expected: pytest PASS, grep only matches in docs (TDD.md, PRD.md, SPEC, plan — expected).

- [ ] **Step 5: Commit**

```bash
git add TDD.md PRD.md docs/superpowers/specs/2026-04-20-directional-entry-design.md
git commit -m "docs(tdd/prd): SPEC-017 directional entry

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Rollback Plan

Eğer directional entry ciddi kayıplara yol açarsa (ilk 24 saat dry_run izleme):

```bash
git revert <SPEC-017 commits> # T1-T4
```

Sonra bot'u reload. Eski 3-strateji yapısına döner.

Daha hafif rollback (config-only): mümkün değil. Directional'den edge'e dönüş kod değişikliği ister.

## Success Criteria

- [ ] Tüm testler PASS (0 regression)
- [ ] `calculate_edge` grep src/'da 0 sonuç
- [ ] `normal.py`, `early_entry.py`, `consensus.py`, `edge.py` dosyaları git'te yok
- [ ] `Signal.edge` field'ı yok
- [ ] `edge:`, `early:`, `consensus:` yaml bloklari yok
- [ ] TDD §6.3 Directional Entry bölümü var
- [ ] PRD edge'den arınmış
- [ ] Bot dry_run'da başlıyor, 1 cycle sonrası yeni mantıkla pozisyon açıyor
