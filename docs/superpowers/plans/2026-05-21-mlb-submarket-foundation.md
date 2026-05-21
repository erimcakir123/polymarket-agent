# MLB Submarket Foundation — Implementation Plan (Plan 1 / 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ana bot'a MLB submarket (totals + run-line) trade'leri için altyapı kur — sport_rules anchor dispatch, model-anchor giriş API'si (`EntryProcessor.process_signals`), portfolio_guards refactor, scanner dispatch, config-gated factory hook. Bu plan bittiğinde bot mock bir engine ile MLB submarket signal alabilir.

**Architecture:** Sport_rules her sport+market_type için `anchor_source` (`"bookmaker"` / `"model"`) tutar. Scanner anchor source'a göre ya mevcut bookmaker enrichment path'ine ya da yeni `MlbSubmarketEngine` path'ine yönlenir. Gate.py'daki 8 portfolio guard ayrı modüle (`portfolio_guards.py`) extract edilir — gate ve yeni `process_signals` API ortak kullanır (DRY).

**Tech Stack:** Python 3.12+, Pydantic, pytest, mevcut bot kod tabanı (master branch).

**Spec Reference:** [`docs/superpowers/specs/2026-05-21-mlb-submarket-mainbot-integration-design.md`](../specs/2026-05-21-mlb-submarket-mainbot-integration-design.md)

**Önemli prensipler:**
- TDD: her task'ta önce test, sonra implementasyon.
- ARCH_GUARD self-check her dosya değişikliği öncesi.
- Drift yok: her edit'ten sonra grep ile eski referans kontrolü.
- Dead code yok: kullanılmayan import/değişken/fonksiyon ekleme; ekledikten sonra kullanmıyorsa sil.

---

## File Structure

**Yeni dosyalar:**
```
src/orchestration/portfolio_guards.py                       # 8 sport-agnostic guard helper
src/strategy/entry/mlb_submarket_engine_protocol.py         # Engine duck-type protocol
tests/unit/orchestration/test_portfolio_guards.py
tests/unit/orchestration/test_entry_processor_signals.py
tests/unit/orchestration/test_scanner_anchor_dispatch.py
tests/unit/orchestration/test_factory_mlb_submarket.py
tests/unit/config/test_sport_rules_anchor.py
tests/unit/config/test_settings_mlb_submarket.py
tests/unit/models/test_enums_mlb_submarket.py
tests/integration/test_mlb_submarket_smoke.py
```

**Modifiye dosyalar:**
```
src/models/enums.py                                          # EntryReason.MLB_SUBMARKET
src/config/sport_rules.py                                    # submarket_anchor + anchor_source()
src/config/settings.py                                       # MlbSubmarketConfig
config.yaml                                                  # mlb_submarket block (disabled)
src/strategy/entry/gate.py                                   # portfolio_guards kullanır
src/orchestration/entry_processor.py                         # process_signals public API
src/orchestration/scanner.py                                 # anchor_source dispatch
src/orchestration/factory.py                                 # MlbSubmarketEngine None inject
DECISIONS.md                                                 # §A.7 sport rules + §B SPEC-R
```

---

## Task 1: EntryReason.MLB_SUBMARKET enum

**Files:**
- Modify: `src/models/enums.py:19-22`
- Test: `tests/unit/models/test_enums_mlb_submarket.py` (yeni)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/models/test_enums_mlb_submarket.py
from src.models.enums import EntryReason


def test_mlb_submarket_entry_reason_exists() -> None:
    assert EntryReason.MLB_SUBMARKET == "mlb_submarket"
    assert EntryReason.MLB_SUBMARKET.value == "mlb_submarket"


def test_mlb_submarket_in_enum_iteration() -> None:
    values = {r.value for r in EntryReason}
    assert "mlb_submarket" in values
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/models/test_enums_mlb_submarket.py -v
```
Expected: FAIL — `AttributeError: MLB_SUBMARKET` veya `KeyError`.

- [ ] **Step 3: Add enum value**

```python
# src/models/enums.py
class EntryReason(str, Enum):
    NORMAL = "normal"
    EARLY = "early"
    CONSENSUS = "consensus"
    MLB_SUBMARKET = "mlb_submarket"  # SPEC-R: model-anchor MLB totals/run-line entries
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/models/test_enums_mlb_submarket.py -v
```
Expected: PASS (2/2).

- [ ] **Step 5: Drift check**

```bash
grep -rn "EntryReason\." src/ tests/ | grep -v ".pyc" | wc -l
```
Mevcut tüm `EntryReason.X` referansları çalışmaya devam etmeli — enum genişledi, daraltılmadı. Drift yok.

- [ ] **Step 6: Commit**

```bash
git add src/models/enums.py tests/unit/models/test_enums_mlb_submarket.py
git commit -m "feat(enums): EntryReason.MLB_SUBMARKET — model-anchor MLB submarket entries"
```

---

## Task 2: sport_rules `anchor_source` dispatch

**Files:**
- Modify: `src/config/sport_rules.py`
- Test: `tests/unit/config/test_sport_rules_anchor.py` (yeni)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/config/test_sport_rules_anchor.py
from src.config.sport_rules import anchor_source


def test_mlb_moneyline_uses_bookmaker() -> None:
    assert anchor_source("baseball_mlb", "moneyline") == "bookmaker"


def test_mlb_totals_uses_model() -> None:
    assert anchor_source("baseball_mlb", "totals") == "model"


def test_mlb_run_line_uses_model() -> None:
    assert anchor_source("baseball_mlb", "run_line") == "model"


def test_nba_totals_uses_bookmaker_default() -> None:
    # NBA submarket_anchor override etmedi → bookmaker default
    assert anchor_source("basketball_nba", "totals") == "bookmaker"


def test_unknown_sport_defaults_to_bookmaker() -> None:
    assert anchor_source("foosball_xyz", "moneyline") == "bookmaker"


def test_alias_normalization() -> None:
    # "mlb" direct rule entry'si + "baseball_npb" alias ile aynı sonuç vermeli
    assert anchor_source("mlb", "totals") == anchor_source("baseball_npb", "totals")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/config/test_sport_rules_anchor.py -v
```
Expected: FAIL — `ImportError: cannot import name 'anchor_source'`.

- [ ] **Step 3: Add submarket_anchor + helper**

```python
# src/config/sport_rules.py — mlb rule'una ekle
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
        # SPEC-R: submarket'ler için bookmaker bypass. Diğer sport+market_type
        # kombinasyonları default "bookmaker" (anchor_source helper'a bak).
        "submarket_anchor": {
            "totals": "model",
            "run_line": "model",
        },
    },

# Dosyanın altına ekle (is_spread_blocked'tan sonra)
def anchor_source(sport_tag: str, market_type: str) -> str:
    """Sport+market_type için anchor kaynağı: 'bookmaker' veya 'model'.

    Default 'bookmaker' — geriye uyumlu (mevcut tüm sport+market kombinasyonları
    Odds API bookmaker probability kullanıyor). 'model' override eden sport'lar
    SPORT_RULES içinde `submarket_anchor` dict'iyle ilan eder (SPEC-R).
    """
    overrides = get_sport_rule(sport_tag, "submarket_anchor", {})
    if not isinstance(overrides, dict):
        return "bookmaker"
    return str(overrides.get(market_type, "bookmaker"))
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/config/test_sport_rules_anchor.py -v
```
Expected: PASS (6/6).

- [ ] **Step 5: Drift check + existing test regression**

```bash
pytest tests/unit/config/ -q
```
Mevcut sport_rules testleri tümü geçmeli (yeni alan eklendi, mevcut alanlar etkilenmedi).

```bash
grep -rn "anchor_source\|submarket_anchor" src/ tests/
```
Sadece yeni eklenenler görünmeli; başka modül anchor_source kullanmıyor henüz.

- [ ] **Step 6: Commit**

```bash
git add src/config/sport_rules.py tests/unit/config/test_sport_rules_anchor.py
git commit -m "feat(sport_rules): anchor_source dispatch — MLB totals/run_line → model"
```

---

## Task 3: MlbSubmarketConfig Pydantic model

**Files:**
- Modify: `src/config/settings.py`
- Test: `tests/unit/config/test_settings_mlb_submarket.py` (yeni)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/config/test_settings_mlb_submarket.py
from src.config.settings import MlbSubmarketConfig, AppConfig


def test_mlb_submarket_config_defaults() -> None:
    cfg = MlbSubmarketConfig()
    assert cfg.enabled is False
    assert cfg.min_edge == 0.05
    assert cfg.statsapi_timeout_sec == 10.0
    assert cfg.rate_cache_path == "data/mlb_rate_cache.jsonl"


def test_mlb_submarket_config_custom() -> None:
    cfg = MlbSubmarketConfig(enabled=True, min_edge=0.08)
    assert cfg.enabled is True
    assert cfg.min_edge == 0.08


def test_app_config_has_mlb_submarket_field() -> None:
    # AppConfig.mlb_submarket optional, None default (config.yaml ile override)
    fields = AppConfig.model_fields
    assert "mlb_submarket" in fields


def test_min_edge_must_be_positive() -> None:
    import pytest
    with pytest.raises(Exception):
        MlbSubmarketConfig(min_edge=-0.01)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/config/test_settings_mlb_submarket.py -v
```
Expected: FAIL — `ImportError: cannot import name 'MlbSubmarketConfig'`.

- [ ] **Step 3: Add Pydantic model + AppConfig field**

```python
# src/config/settings.py — uygun bir Config class'ı yakınına ekle
from pydantic import BaseModel, Field


class MlbSubmarketConfig(BaseModel):
    """MLB submarket model entegrasyonu (SPEC-R). Disabled by default."""
    enabled: bool = False
    min_edge: float = Field(0.05, gt=0.0, description="Model edge eşiği — 0'dan büyük olmalı")
    statsapi_timeout_sec: float = Field(10.0, gt=0.0)
    rate_cache_path: str = "data/mlb_rate_cache.jsonl"


# AppConfig içine ekle (mevcut alanların yakınına)
class AppConfig(BaseModel):
    # ...mevcut alanlar...
    mlb_submarket: MlbSubmarketConfig = Field(default_factory=MlbSubmarketConfig)
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/config/test_settings_mlb_submarket.py -v
```
Expected: PASS (4/4).

- [ ] **Step 5: Verify no regression**

```bash
pytest tests/unit/config/ -q
```
Tüm config testleri yeşil.

- [ ] **Step 6: Commit**

```bash
git add src/config/settings.py tests/unit/config/test_settings_mlb_submarket.py
git commit -m "feat(config): MlbSubmarketConfig — disabled by default, min_edge=0.05"
```

---

## Task 4: config.yaml mlb_submarket block

**Files:**
- Modify: `config.yaml`
- Test: dummy integration — AppConfig yükleyip default'u kontrol et.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/config/test_settings_mlb_submarket.py — aynı dosyaya yeni test
import yaml
from pathlib import Path

from src.config.settings import AppConfig


def test_root_config_yaml_loads_mlb_submarket_disabled(tmp_path: Path) -> None:
    """config.yaml yüklendiğinde mlb_submarket.enabled = False (production safe default)."""
    root_cfg = Path(__file__).parents[4] / "config.yaml"
    data = yaml.safe_load(root_cfg.read_text(encoding="utf-8"))
    cfg = AppConfig(**data)
    assert cfg.mlb_submarket.enabled is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/config/test_settings_mlb_submarket.py::test_root_config_yaml_loads_mlb_submarket_disabled -v
```
Expected: PASS (Pydantic default_factory zaten False) — bu test ileride config.yaml'ı yanlışlıkla enabled bırakmayı önler.

> Not: Bu test başarıyla geçecek, ancak `config.yaml`'a explicit block eklemek **dokümantasyon ve operatör görünürlüğü** için gerekli. Kaydın hâlâ yazılmasını sağla.

- [ ] **Step 3: Add explicit block to config.yaml**

```yaml
# config.yaml — dosyanın altına (mevcut blokların yanına)
mlb_submarket:
  enabled: false              # SPEC-R: model-anchor MLB totals/run-line. Manuel aç.
  min_edge: 0.05              # Model edge eşiği (Tennis Lab paritesi)
  statsapi_timeout_sec: 10.0
  rate_cache_path: data/mlb_rate_cache.jsonl
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/config/test_settings_mlb_submarket.py -v
```
Expected: PASS (5/5).

- [ ] **Step 5: Commit**

```bash
git add config.yaml tests/unit/config/test_settings_mlb_submarket.py
git commit -m "feat(config.yaml): mlb_submarket block — disabled default"
```

---

## Task 5: portfolio_guards module (refactor extract)

**Files:**
- Create: `src/orchestration/portfolio_guards.py`
- Modify: `src/strategy/entry/gate.py` (guard'ları portfolio_guards'tan çağıracak şekilde refactor)
- Test: `tests/unit/orchestration/test_portfolio_guards.py` (yeni)

**Amaç:** gate.py'da inline yazılı 5 sport-agnostic guard'ı (global halts + per-market guards) ortak modüle taşı. gate.py refactor edilir ama davranışı değişmez (regression yok). process_signals API'si (Task 6) bu modülü reuse edecek.

**Sport-agnostic guard'lar:**
1. Circuit breaker (global halt)
2. Cooldown (global halt)
3. max_positions (global halt)
4. event_cap (per-market)
5. Blacklist (per-market)

> Manipulation guard ve enrichment/edge bookmaker-spesifik — gate.py'da kalır, portfolio_guards'a taşınmaz (model anchor bu adımları atlar).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_portfolio_guards.py
from dataclasses import dataclass
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.orchestration.portfolio_guards import (
    GuardSkip,
    check_global_halts,
    check_per_market_guards,
)


@dataclass
class _MockMarket:
    condition_id: str = "cid-1"
    event_id: str = "evt-1"


def _mk_breaker(halt: bool = False, reason: str = "") -> MagicMock:
    b = MagicMock()
    b.should_halt_entries.return_value = (halt, reason)
    return b


def _mk_cooldown(active: bool = False, remaining: int = 0) -> MagicMock:
    c = MagicMock()
    c.is_active.return_value = active
    c.state.cooldown_remaining = remaining
    return c


def _mk_portfolio(count: int = 0, event_counts: dict | None = None) -> MagicMock:
    p = MagicMock()
    p.count.return_value = count
    p.count_event.side_effect = lambda eid: (event_counts or {}).get(eid, 0)
    return p


def _mk_blacklist(cid_set: set | None = None, eid_set: set | None = None) -> MagicMock:
    b = MagicMock()
    cids = cid_set or set()
    eids = eid_set or set()
    b.is_blacklisted.side_effect = lambda condition_id=None, event_id=None: (
        (condition_id is not None and condition_id in cids)
        or (event_id is not None and event_id in eids)
    )
    return b


def test_check_global_halts_breaker_active() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(halt=True, reason="breaker: daily_loss=-50"),
        cooldown=_mk_cooldown(),
        portfolio=_mk_portfolio(count=0),
        max_positions=50,
    )
    assert skip is not None
    assert skip.reason == "circuit_breaker"
    assert "daily_loss" in skip.detail


def test_check_global_halts_cooldown_active() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(),
        cooldown=_mk_cooldown(active=True, remaining=3),
        portfolio=_mk_portfolio(count=0),
        max_positions=50,
    )
    assert skip is not None
    assert skip.reason == "cooldown_active"
    assert "cycles_remaining=3" in skip.detail


def test_check_global_halts_max_positions() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(),
        cooldown=_mk_cooldown(),
        portfolio=_mk_portfolio(count=50),
        max_positions=50,
    )
    assert skip is not None
    assert skip.reason == "max_positions_reached"


def test_check_global_halts_passes() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(),
        cooldown=_mk_cooldown(),
        portfolio=_mk_portfolio(count=10),
        max_positions=50,
    )
    assert skip is None


def test_check_per_market_event_cap() -> None:
    market = _MockMarket(condition_id="cid-x", event_id="evt-x")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(event_counts={"evt-x": 2}),
        blacklist=_mk_blacklist(),
        max_positions_per_event=2,
    )
    assert skip is not None
    assert skip.reason == "event_already_held"


def test_check_per_market_blacklist_cid() -> None:
    market = _MockMarket(condition_id="cid-blocked", event_id="evt-x")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(),
        blacklist=_mk_blacklist(cid_set={"cid-blocked"}),
        max_positions_per_event=2,
    )
    assert skip is not None
    assert skip.reason == "blacklisted"
    assert "condition_id" in skip.detail


def test_check_per_market_blacklist_eid() -> None:
    market = _MockMarket(condition_id="cid-x", event_id="evt-blocked")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(),
        blacklist=_mk_blacklist(eid_set={"evt-blocked"}),
        max_positions_per_event=2,
    )
    assert skip is not None
    assert skip.reason == "blacklisted"
    assert "event_id" in skip.detail


def test_check_per_market_passes() -> None:
    market = _MockMarket(condition_id="cid-ok", event_id="evt-ok")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(event_counts={"evt-ok": 0}),
        blacklist=_mk_blacklist(),
        max_positions_per_event=2,
    )
    assert skip is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/orchestration/test_portfolio_guards.py -v
```
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Create portfolio_guards module**

```python
# src/orchestration/portfolio_guards.py
"""Sport-agnostic portfolio guard helpers (SPEC-R).

Hem bookmaker-anchor entry path'i (gate.py) hem de model-anchor entry path'i
(entry_processor.process_signals) tarafından ortak kullanılır. DRY refactor —
davranış değişmez, sadece extract.

Bookmaker-spesifik guard'lar (manipulation, enrichment, no_edge, entry_price_cap)
bu modülde değil — gate.py kendi başına yapar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GuardSkip:
    """Bir guard'ın market'i reddetme kararı. None döndürmek = guard geçildi."""
    reason: str
    detail: str = ""


# Duck-type protocols — gerçek import'lar gate.py veya entry_processor'da yapılır.
# Bu modül saf — pydantic, MarketData, dependency objesi import etmez.
class _BreakerLike(Protocol):
    def should_halt_entries(self) -> tuple[bool, str]: ...


class _CooldownLike(Protocol):
    def is_active(self) -> bool: ...
    @property
    def state(self): ...  # state.cooldown_remaining int


class _PortfolioLike(Protocol):
    def count(self) -> int: ...
    def count_event(self, event_id: str) -> int: ...


class _BlacklistLike(Protocol):
    def is_blacklisted(self, condition_id: str | None = None,
                       event_id: str | None = None) -> bool: ...


class _MarketLike(Protocol):
    condition_id: str
    event_id: str


def check_global_halts(
    *,
    breaker: _BreakerLike,
    cooldown: _CooldownLike,
    portfolio: _PortfolioLike,
    max_positions: int,
) -> GuardSkip | None:
    """Tüm market'ler için tek seferlik halt kontrolü.

    Returns:
        Skip ediliyorsa GuardSkip; geçildi ise None.
    """
    halt, reason = breaker.should_halt_entries()
    if halt:
        detail = reason[len("breaker: "):] if reason.startswith("breaker: ") else reason
        return GuardSkip(reason="circuit_breaker", detail=detail)

    if cooldown.is_active():
        remaining = cooldown.state.cooldown_remaining
        return GuardSkip(reason="cooldown_active", detail=f"cycles_remaining={remaining}")

    count = portfolio.count()
    if count >= max_positions:
        return GuardSkip(reason="max_positions_reached", detail=f"count={count}/{max_positions}")

    return None


def check_per_market_guards(
    *,
    market: _MarketLike,
    portfolio: _PortfolioLike,
    blacklist: _BlacklistLike,
    max_positions_per_event: int,
) -> GuardSkip | None:
    """Tek market için per-market guard kontrolleri (event_cap + blacklist).

    Returns:
        Skip ediliyorsa GuardSkip; geçildi ise None.
    """
    if market.event_id:
        event_count = portfolio.count_event(market.event_id)
        if event_count >= max_positions_per_event:
            return GuardSkip(
                reason="event_already_held",
                detail=(
                    f"event_id={market.event_id} "
                    f"count={event_count}/{max_positions_per_event}"
                ),
            )

    if blacklist.is_blacklisted(condition_id=market.condition_id):
        return GuardSkip(reason="blacklisted", detail="match=condition_id")
    if market.event_id and blacklist.is_blacklisted(event_id=market.event_id):
        return GuardSkip(reason="blacklisted", detail="match=event_id")

    return None
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/orchestration/test_portfolio_guards.py -v
```
Expected: PASS (8/8).

- [ ] **Step 5: Refactor gate.py to use portfolio_guards**

```python
# src/strategy/entry/gate.py
# Üste import ekle:
from src.orchestration.portfolio_guards import (
    check_global_halts as _check_global_halts,
    check_per_market_guards as _check_per_market_guards,
)
```

`run()` method'unun global halt bloklarını şu hale getir:

```python
    def run(self, markets: list[MarketData]) -> list[GateResult]:
        """Tüm marketleri değerlendir. Her biri için GateResult döner."""
        global_skip = _check_global_halts(
            breaker=self.breaker,
            cooldown=self.cooldown,
            portfolio=self.portfolio,
            max_positions=self.config.max_positions,
        )
        if global_skip is not None:
            logger.info("Entry gate halted: %s", global_skip.reason)
            return [
                GateResult(m.condition_id, None, global_skip.reason, skip_detail=global_skip.detail)
                for m in markets
            ]

        return [self._evaluate_one(m) for m in markets]
```

`_evaluate_one`'ın event_cap + blacklist bölümlerini şununla değiştir:

```python
    def _evaluate_one(self, market: MarketData) -> GateResult:
        cid = market.condition_id

        # 1+2. event_cap + blacklist (portfolio_guards ile DRY)
        per_market_skip = _check_per_market_guards(
            market=market,
            portfolio=self.portfolio,
            blacklist=self.blacklist,
            max_positions_per_event=self.config.max_positions_per_event,
        )
        if per_market_skip is not None:
            return GateResult(cid, None, per_market_skip.reason, skip_detail=per_market_skip.detail)

        # 3. Manipulation guard (bookmaker path'e özel — model anchor bunu farklı kontrol eder)
        manip = self._manip_check(...)
        # ...mevcut kod devam eder...
```

- [ ] **Step 6: Verify gate.py refactor zero-regression**

```bash
pytest tests/unit/strategy/entry/test_gate.py -v
```
Expected: PASS (mevcut tüm test'ler).

- [ ] **Step 7: Drift check**

```bash
grep -n "should_halt_entries\|is_active\|count_event\|is_blacklisted" src/strategy/entry/gate.py
```
gate.py içinde sadece portfolio_guards üzerinden gitmeli; doğrudan çağrı bulursan refactor eksik.

- [ ] **Step 8: Commit**

```bash
git add src/orchestration/portfolio_guards.py src/strategy/entry/gate.py tests/unit/orchestration/test_portfolio_guards.py
git commit -m "refactor(guards): portfolio_guards module — DRY extract from gate.py"
```

---

## Task 6: EntryProcessor.process_signals public API

**Files:**
- Modify: `src/orchestration/entry_processor.py`
- Test: `tests/unit/orchestration/test_entry_processor_signals.py` (yeni)

**Amaç:** Tennis Lab pattern'i — bookmaker bypass eden model-anchor giriş noktası. Yeni signal'ları alır, sport-agnostic portfolio guard'larını çalıştırır, kalanları execute eder ve persist eder. Bookmaker enrichment ve no_edge YOK (sinyal model'den gelir, edge zaten signal.edge'de).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_entry_processor_signals.py
from unittest.mock import MagicMock

from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal
from src.orchestration.entry_processor import EntryProcessor


def _mk_signal(cid: str = "cid-1", edge: float = 0.08) -> Signal:
    return Signal(
        condition_id=cid,
        direction=Direction.BUY_YES,
        anchor_probability=0.65,
        market_price=0.57,
        edge=edge,
        confidence="A",
        size_usdc=0.0,
        entry_reason=EntryReason.MLB_SUBMARKET,
        bookmaker_prob=0.0,
        num_bookmakers=0,
        has_sharp=False,
        sport_tag="baseball_mlb",
        event_id="evt-1",
    )


def _mk_market(cid: str = "cid-1") -> MarketData:
    m = MagicMock(spec=MarketData)
    m.condition_id = cid
    m.event_id = "evt-1"
    m.question = "test"
    m.liquidity = 100000.0
    m.yes_price = 0.57
    return m


def _mk_deps(circuit_halt: bool = False, max_positions: int = 50,
             portfolio_count: int = 0) -> MagicMock:
    deps = MagicMock()
    deps.state.config.mode.value = "dry_run"
    deps.gate.config.max_positions = max_positions
    deps.gate.config.max_positions_per_event = 2
    deps.state.portfolio.count.return_value = portfolio_count
    deps.state.portfolio.count_event.return_value = 0
    deps.circuit_breaker.should_halt_entries.return_value = (circuit_halt, "")
    deps.cooldown.is_active.return_value = False
    deps.cooldown.state.cooldown_remaining = 0
    deps.blacklist.is_blacklisted.return_value = False
    return deps


def test_process_signals_empty_input_no_op() -> None:
    deps = _mk_deps()
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[], signals=[])
    deps.executor.execute.assert_not_called()


def test_process_signals_length_mismatch_raises() -> None:
    import pytest
    deps = _mk_deps()
    processor = EntryProcessor(deps)
    with pytest.raises(ValueError, match="length mismatch"):
        processor.process_signals(markets=[_mk_market()], signals=[])


def test_process_signals_circuit_breaker_halts() -> None:
    deps = _mk_deps(circuit_halt=True)
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    deps.executor.execute.assert_not_called()


def test_process_signals_max_positions_halts() -> None:
    deps = _mk_deps(max_positions=10, portfolio_count=10)
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    deps.executor.execute.assert_not_called()


def test_process_signals_passes_to_executor_when_clean() -> None:
    deps = _mk_deps()
    deps.executor.execute.return_value = MagicMock(filled=True, avg_price=0.57, size_usdc=50.0)
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    assert deps.executor.execute.call_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/orchestration/test_entry_processor_signals.py -v
```
Expected: FAIL — `AttributeError: 'EntryProcessor' object has no attribute 'process_signals'`.

- [ ] **Step 3: Implement process_signals**

```python
# src/orchestration/entry_processor.py — class içine ekle (run_heavy yakını)
from src.orchestration.portfolio_guards import (
    check_global_halts,
    check_per_market_guards,
)

class EntryProcessor:
    # ...mevcut __init__ + run_heavy...

    def process_signals(
        self,
        markets: list[MarketData],
        signals: list,  # Signal
    ) -> None:
        """Model-anchor entry path (SPEC-R). Bookmaker bypass.

        Signals zaten model'den gelir, edge ve direction belirlenmiştir.
        Bu metod sport-agnostic portfolio guard'larını çalıştırır ve geçen
        signal'lar için pozisyon açar. Bookmaker enrichment ve no_edge yok.

        Args:
            markets: Source MarketData listesi.
            signals: Aynı sırada Signal listesi (markets[i] ↔ signals[i]).
        """
        if len(markets) != len(signals):
            raise ValueError(
                f"process_signals: markets/signals length mismatch "
                f"({len(markets)} vs {len(signals)})"
            )
        if not markets:
            return

        global_skip = check_global_halts(
            breaker=self.deps.circuit_breaker,
            cooldown=self.deps.cooldown,
            portfolio=self.deps.state.portfolio,
            max_positions=self.deps.gate.config.max_positions,
        )
        if global_skip is not None:
            logger.info("process_signals halted: %s (%s)",
                        global_skip.reason, global_skip.detail)
            return

        max_per_event = self.deps.gate.config.max_positions_per_event
        for market, signal in zip(markets, signals):
            per_market_skip = check_per_market_guards(
                market=market,
                portfolio=self.deps.state.portfolio,
                blacklist=self.deps.blacklist,
                max_positions_per_event=max_per_event,
            )
            if per_market_skip is not None:
                logger.info("process_signals skip %s: %s (%s)",
                            market.condition_id, per_market_skip.reason,
                            per_market_skip.detail)
                continue

            # Executor execute eder (sizing signal.size_usdc'den)
            result = self.deps.executor.execute(market, signal)
            if not result.filled:
                logger.info("process_signals execute not filled: %s", market.condition_id)
                continue

            # Persist + audit (mevcut helper'ı kullan)
            self._persist_filled(market, signal, result)
```

> Not: `_persist_filled` mevcut entry_processor'da yardımcı method varsa kullan; yoksa Tennis Lab worktree'sinden referansa bakıp aynı sırayı uygula (trade_logger.append, equity snapshot, blacklist append eğer SL ise — sadece entry için trade_logger.append yeterli). Bu noktada `process_markets`'in execute sonrası persist kısmını helper'a çıkar ve hem `process_markets` hem `process_signals` onu kullansın (DRY).

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/orchestration/test_entry_processor_signals.py -v
```
Expected: PASS (5/5).

- [ ] **Step 5: Existing test regression**

```bash
pytest tests/unit/orchestration/test_entry_processor.py tests/unit/orchestration/test_entry_processor_basketball.py -v
```
Expected: tüm mevcut testler yeşil — `process_markets` davranışı değişmedi.

- [ ] **Step 6: Drift check**

```bash
grep -n "process_signals" src/ -r
```
Sadece entry_processor.py'da görünmeli (henüz kimse çağırmıyor — Task 7'de scanner çağıracak).

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/entry_processor.py tests/unit/orchestration/test_entry_processor_signals.py
git commit -m "feat(entry): EntryProcessor.process_signals — model-anchor entry API (SPEC-R)"
```

---

## Task 7: MlbSubmarketEngine Protocol + scanner dispatch

**Files:**
- Create: `src/strategy/entry/mlb_submarket_engine_protocol.py`
- Modify: `src/orchestration/scanner.py`
- Test: `tests/unit/orchestration/test_scanner_anchor_dispatch.py` (yeni)

**Amaç:** Scanner her market için `anchor_source(sport_tag, market_type)` sorgular. "model" ise ve `mlb_submarket_engine` enjekte edilmişse, engine'in `process(market)` method'u çağrılır; geriye `EdgeCandidate | None` döner; kalan signal listesine eklenir. "bookmaker" ise mevcut yol.

Engine'in gerçek implementasyonu Plan 2+3+4'te gelecek. Plan 1'de **Protocol** ile interface sabitlenir ve mock engine ile entegrasyon test edilir.

- [ ] **Step 1: Create engine protocol**

```python
# src/strategy/entry/mlb_submarket_engine_protocol.py
"""MLB Submarket Engine protocol — Plan 1 (interface only).

Gerçek implementation Plan 2+3+4'te `src/strategy/entry/mlb_submarket_engine.py`
dosyasında yapılacak. Bu Protocol sayesinde scanner Plan 1'de mock engine ile
test edilebilir, gerçek engine eklendiğinde signature uyumu garanti.
"""
from __future__ import annotations

from typing import Protocol

from src.models.market import MarketData
from src.models.signal import Signal


class MlbSubmarketEngineProtocol(Protocol):
    """MLB totals/run-line için model-anchor signal üretici."""

    def process(self, market: MarketData) -> Signal | None:
        """Bir market'i değerlendirir.

        Returns:
            Signal: edge ≥ min_edge ise; sizing 0.0 (downstream hesaplar).
            None: edge yok, lineup belirsiz, veri eksik, vs.
        """
        ...
```

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/orchestration/test_scanner_anchor_dispatch.py
from unittest.mock import MagicMock

from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


def _mk_market(cid: str, sport: str, mtype: str) -> MagicMock:
    m = MagicMock(spec=MarketData)
    m.condition_id = cid
    m.sport_tag = sport
    m.sports_market_type = mtype
    return m


def _mk_signal(cid: str) -> Signal:
    return Signal(
        condition_id=cid, direction=Direction.BUY_YES, anchor_probability=0.6,
        market_price=0.5, edge=0.08, confidence="A", size_usdc=0.0,
        entry_reason=EntryReason.MLB_SUBMARKET, bookmaker_prob=0.0,
        num_bookmakers=0, has_sharp=False, sport_tag="baseball_mlb", event_id="evt-x",
    )


def test_scanner_routes_mlb_totals_to_engine() -> None:
    from src.orchestration.scanner import classify_anchor_path

    mlb_totals = _mk_market("c1", "baseball_mlb", "totals")
    path = classify_anchor_path(mlb_totals)
    assert path == "model"


def test_scanner_routes_mlb_moneyline_to_bookmaker() -> None:
    from src.orchestration.scanner import classify_anchor_path

    mlb_ml = _mk_market("c2", "baseball_mlb", "moneyline")
    assert classify_anchor_path(mlb_ml) == "bookmaker"


def test_scanner_routes_nba_totals_to_bookmaker() -> None:
    from src.orchestration.scanner import classify_anchor_path

    nba_totals = _mk_market("c3", "basketball_nba", "totals")
    assert classify_anchor_path(nba_totals) == "bookmaker"


def test_scanner_collects_model_signals_when_engine_present() -> None:
    from src.orchestration.scanner import collect_model_signals

    mlb_totals = _mk_market("cid-x", "baseball_mlb", "totals")
    mlb_ml = _mk_market("cid-y", "baseball_mlb", "moneyline")

    engine = MagicMock()
    engine.process.return_value = _mk_signal("cid-x")

    markets, signals = collect_model_signals(
        candidates=[mlb_totals, mlb_ml], engine=engine,
    )

    # Sadece totals → engine path; moneyline → bookmaker path (ayrı liste değil).
    assert len(markets) == 1
    assert markets[0].condition_id == "cid-x"
    assert signals[0].condition_id == "cid-x"
    engine.process.assert_called_once_with(mlb_totals)


def test_scanner_skips_when_engine_none() -> None:
    from src.orchestration.scanner import collect_model_signals

    mlb_totals = _mk_market("cid-x", "baseball_mlb", "totals")
    markets, signals = collect_model_signals(candidates=[mlb_totals], engine=None)
    assert markets == []
    assert signals == []


def test_scanner_skips_when_engine_returns_none() -> None:
    from src.orchestration.scanner import collect_model_signals

    mlb_totals = _mk_market("cid-x", "baseball_mlb", "totals")
    engine = MagicMock()
    engine.process.return_value = None  # edge yok
    markets, signals = collect_model_signals(candidates=[mlb_totals], engine=engine)
    assert markets == []
    assert signals == []
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/unit/orchestration/test_scanner_anchor_dispatch.py -v
```
Expected: FAIL — `ImportError` veya `AttributeError`.

- [ ] **Step 4: Add classify_anchor_path + collect_model_signals to scanner**

```python
# src/orchestration/scanner.py — modül üst seviyesine ekle
from src.config.sport_rules import anchor_source
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol


def classify_anchor_path(market) -> str:
    """Bir market için anchor kaynağını döndür: 'bookmaker' veya 'model'.

    Wrapper around sport_rules.anchor_source — scanner içinde ortak nokta.
    """
    return anchor_source(market.sport_tag, market.sports_market_type)


def collect_model_signals(
    *,
    candidates,
    engine: MlbSubmarketEngineProtocol | None,
) -> tuple[list, list]:
    """Model-anchor signal toplama.

    Args:
        candidates: Scan'den gelen market listesi (filtered: anchor='model' olanlar
                    + diğerleri — bu fonksiyon kendi içinde filter eder).
        engine: MlbSubmarketEngine instance (config-gated; None ise hiçbir şey
                döndürmez).

    Returns:
        (markets, signals) — engine.process'in edge ürettiği market/signal
        çiftleri. Diğerleri (bookmaker path) bu listede yer almaz.
    """
    if engine is None:
        return [], []
    markets = []
    signals = []
    for m in candidates:
        if classify_anchor_path(m) != "model":
            continue
        signal = engine.process(m)
        if signal is None:
            continue
        markets.append(m)
        signals.append(signal)
    return markets, signals
```

- [ ] **Step 5: Verify test passes**

```bash
pytest tests/unit/orchestration/test_scanner_anchor_dispatch.py -v
```
Expected: PASS (6/6).

- [ ] **Step 6: Scanner regression**

```bash
pytest tests/unit/orchestration/test_scanner.py -v
```
Expected: PASS (mevcut testler — yeni helper'lar inert).

- [ ] **Step 7: Commit**

```bash
git add src/orchestration/scanner.py src/strategy/entry/mlb_submarket_engine_protocol.py tests/unit/orchestration/test_scanner_anchor_dispatch.py
git commit -m "feat(scanner): anchor_source dispatch + collect_model_signals (SPEC-R)"
```

---

## Task 8: Factory composition (config-gated mlb_submarket_engine)

**Files:**
- Modify: `src/orchestration/factory.py`
- Test: `tests/unit/orchestration/test_factory_mlb_submarket.py` (yeni)

**Amaç:** AppConfig.mlb_submarket.enabled `True` ise engine inject edilir (şu an Protocol-only — Plan 4'te gerçek instance). `False` ise None geçer; bot mevcut bookmaker akışıyla çalışır.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_factory_mlb_submarket.py
from src.config.settings import AppConfig, MlbSubmarketConfig
from src.orchestration.factory import build_agent_deps


def test_factory_engine_none_when_disabled() -> None:
    cfg = AppConfig(mlb_submarket=MlbSubmarketConfig(enabled=False))
    deps = build_agent_deps(cfg)
    assert deps.mlb_submarket_engine is None


def test_factory_engine_none_when_enabled_but_no_impl_yet() -> None:
    """Plan 1: enabled=True dahi olsa engine_impl Plan 4'te eklenecek.

    Plan 1'de protocol-only — factory hâlâ None geçer ve TODO log'lar.
    """
    cfg = AppConfig(mlb_submarket=MlbSubmarketConfig(enabled=True))
    deps = build_agent_deps(cfg)
    # Plan 4'te: assert deps.mlb_submarket_engine is not None
    assert deps.mlb_submarket_engine is None  # Plan 1 placeholder
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/orchestration/test_factory_mlb_submarket.py -v
```
Expected: FAIL — `AttributeError: deps has no 'mlb_submarket_engine'`.

- [ ] **Step 3: Add engine field to deps + wire factory**

```python
# src/orchestration/factory.py
# Üste import
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol

# AgentDeps dataclass'a alan ekle (bulunduğu yerde):
@dataclass
class AgentDeps:
    # ...mevcut alanlar...
    mlb_submarket_engine: MlbSubmarketEngineProtocol | None = None


# build_agent_deps fonksiyonu içinde, döndürmeden önce:
def build_agent_deps(config: AppConfig, ...) -> AgentDeps:
    # ...mevcut composition...

    mlb_engine: MlbSubmarketEngineProtocol | None = None
    if config.mlb_submarket.enabled:
        # Plan 4'te gerçek instance burada inject edilecek
        logger.warning(
            "mlb_submarket.enabled=True ama engine impl Plan 4'te gelecek — "
            "şu an None inject ediliyor (SPEC-R Plan 1)."
        )

    return AgentDeps(
        # ...mevcut alanlar...
        mlb_submarket_engine=mlb_engine,
    )
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/orchestration/test_factory_mlb_submarket.py -v
```
Expected: PASS (2/2).

- [ ] **Step 5: Factory regression**

```bash
pytest tests/unit/orchestration/ -q
```
Expected: tüm orchestration testleri yeşil.

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/factory.py tests/unit/orchestration/test_factory_mlb_submarket.py
git commit -m "feat(factory): mlb_submarket_engine config-gated injection (None until Plan 4)"
```

---

## Task 9: Wire scanner → process_signals in agent heavy cycle

**Files:**
- Modify: `src/orchestration/entry_processor.py` (run_heavy içinde model path tetikleme)
- Test: `tests/unit/orchestration/test_entry_processor.py` (mevcut dosyaya yeni test)

**Amaç:** Heavy cycle'da scan sonrası, `collect_model_signals` çağrılıp `process_signals` ile geçirilir. Mock engine ile end-to-end işlevsel.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/orchestration/test_entry_processor.py — yeni test ekle
from unittest.mock import MagicMock, patch

def test_run_heavy_calls_process_signals_when_engine_present(monkeypatch) -> None:
    """Heavy cycle MLB submarket engine'den signal alır ve process_signals çağırır."""
    # ...mevcut test boilerplate'i taklit et — deps build et...
    deps = MagicMock()
    deps.mlb_submarket_engine = MagicMock()
    deps.mlb_submarket_engine.process.return_value = MagicMock(
        condition_id="cid-mlb", entry_reason="mlb_submarket",
    )
    # scanner.scan() bir MLB totals market döndürsün
    mlb_market = MagicMock()
    mlb_market.condition_id = "cid-mlb"
    mlb_market.sport_tag = "baseball_mlb"
    mlb_market.sports_market_type = "totals"
    deps.scanner.scan.return_value = [mlb_market]
    deps.state.portfolio.count.return_value = 0
    deps.gate.config.max_positions = 50

    from src.orchestration.entry_processor import EntryProcessor
    processor = EntryProcessor(deps)
    with patch.object(processor, "process_signals") as mock_ps:
        with patch.object(processor, "process_markets"):
            processor.run_heavy()
    mock_ps.assert_called_once()
    call_args = mock_ps.call_args
    assert call_args.kwargs.get("markets") == [mlb_market] or call_args.args[0] == [mlb_market]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/orchestration/test_entry_processor.py::test_run_heavy_calls_process_signals_when_engine_present -v
```
Expected: FAIL — process_signals çağrılmıyor.

- [ ] **Step 3: Modify run_heavy to dispatch model signals**

`src/orchestration/entry_processor.py` `run_heavy` method'unun başında, scan sonrası ekle:

```python
        scan_fresh = self.deps.scanner.scan()
        scan_by_cid = {m.condition_id: m for m in scan_fresh}

        # Model-anchor path (SPEC-R MLB submarket). Engine None ise no-op.
        from src.orchestration.scanner import collect_model_signals
        model_markets, model_signals = collect_model_signals(
            candidates=scan_fresh, engine=self.deps.mlb_submarket_engine,
        )
        if model_markets:
            self.process_signals(markets=model_markets, signals=model_signals)
            # Model-path market'leri bookmaker akışından çıkar (çift trade yok)
            model_cids = {m.condition_id for m in model_markets}
            scan_fresh = [m for m in scan_fresh if m.condition_id not in model_cids]
            scan_by_cid = {m.condition_id: m for m in scan_fresh}

        # ...mevcut bookmaker path devam eder...
```

- [ ] **Step 4: Verify test passes**

```bash
pytest tests/unit/orchestration/test_entry_processor.py -v
```
Expected: PASS (tümü, yeni test dahil).

- [ ] **Step 5: Heavy cycle regression**

```bash
pytest tests/unit/orchestration/test_agent.py tests/unit/orchestration/test_agent_heavy_stages.py -q
```
Expected: tüm mevcut testler yeşil.

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/entry_processor.py tests/unit/orchestration/test_entry_processor.py
git commit -m "feat(entry): heavy cycle dispatches model signals → process_signals"
```

---

## Task 10: End-to-end smoke test + DECISIONS update

**Files:**
- Create: `tests/integration/test_mlb_submarket_smoke.py`
- Modify: `DECISIONS.md` (§A.7 sport rules + §B SPEC-R kaydı)

- [ ] **Step 1: Write smoke test**

```python
# tests/integration/test_mlb_submarket_smoke.py
"""Smoke test: MLB submarket engine (mock) → process_signals → trade audit.

Plan 1 end-to-end: gerçek model olmadan da pipeline çalışıyor mu?
"""
from unittest.mock import MagicMock

from src.config.settings import AppConfig, MlbSubmarketConfig
from src.models.enums import Direction, EntryReason
from src.models.signal import Signal


def test_mlb_submarket_signal_flows_through_process_signals() -> None:
    """Mock engine → process_signals → executor.execute çağrılır."""
    from src.orchestration.entry_processor import EntryProcessor

    market = MagicMock()
    market.condition_id = "cid-mlb"
    market.event_id = "evt-mlb"
    market.sport_tag = "baseball_mlb"
    market.sports_market_type = "totals"
    market.question = "MLB total 8.5"
    market.liquidity = 100000.0
    market.yes_price = 0.55

    signal = Signal(
        condition_id="cid-mlb", direction=Direction.BUY_YES,
        anchor_probability=0.62, market_price=0.55, edge=0.07,
        confidence="A", size_usdc=50.0,
        entry_reason=EntryReason.MLB_SUBMARKET,
        bookmaker_prob=0.0, num_bookmakers=0, has_sharp=False,
        sport_tag="baseball_mlb", event_id="evt-mlb",
    )

    deps = MagicMock()
    deps.gate.config.max_positions = 50
    deps.gate.config.max_positions_per_event = 2
    deps.state.portfolio.count.return_value = 0
    deps.state.portfolio.count_event.return_value = 0
    deps.circuit_breaker.should_halt_entries.return_value = (False, "")
    deps.cooldown.is_active.return_value = False
    deps.cooldown.state.cooldown_remaining = 0
    deps.blacklist.is_blacklisted.return_value = False
    deps.executor.execute.return_value = MagicMock(
        filled=True, avg_price=0.55, size_usdc=50.0,
    )

    processor = EntryProcessor(deps)
    processor.process_signals(markets=[market], signals=[signal])

    deps.executor.execute.assert_called_once()
```

- [ ] **Step 2: Run smoke test**

```bash
pytest tests/integration/test_mlb_submarket_smoke.py -v
```
Expected: PASS.

- [ ] **Step 3: Full test suite verification**

```bash
pytest -q
```
Expected: tüm test'ler yeşil. Eğer regression varsa task'i tamamlamadan düzelt.

- [ ] **Step 4: DECISIONS.md güncelle**

```markdown
# DECISIONS.md §A.7 (Sport Rules) — mlb satırına eklemek:
- `submarket_anchor`: {`totals`: model, `run_line`: model} — SPEC-R model-anchor entry path.

# DECISIONS.md §B en üste yeni SPEC-R kaydı:

## SPEC-R: MLB Submarket Foundation — Model-Anchor Entry Path (2026-05-21)

**Karar:** Sport+market_type kombinasyonu için anchor kaynağı seçilebilir hale getirildi (`anchor_source(sport_tag, market_type) → 'bookmaker'|'model'`). MLB totals/run-line için model anchor. `EntryProcessor.process_signals` public API model-path için bookmaker bypass entry noktası. Gate.py'daki 8 portfolio guard `portfolio_guards.py` modülüne extract edildi (DRY refactor, zero-regression).

**Neden:** Odds API baseball için sadece moneyline probability sağlıyor; totals/run-line bookmaker yok. Eski DRAFT (sandbox lab) rejected; kullanıcı ana bot entegrasyonu istedi. Bu plan altyapıyı kurar — Plan 2-3-4 modeli ve veri katmanlarını ekler.

**Etki:**
- Yeni: `src/orchestration/portfolio_guards.py`, `src/strategy/entry/mlb_submarket_engine_protocol.py`
- Modifiye: `src/models/enums.py` (EntryReason.MLB_SUBMARKET), `src/config/sport_rules.py` (anchor_source), `src/config/settings.py` (MlbSubmarketConfig), `config.yaml` (disabled default), `src/strategy/entry/gate.py` (portfolio_guards kullanır), `src/orchestration/entry_processor.py` (process_signals), `src/orchestration/scanner.py` (anchor dispatch), `src/orchestration/factory.py` (engine inject)
- 10 task TDD ile uygulandı, mock engine ile end-to-end smoke test PASS.

**Sonraki:** Plan 2 (domain model), Plan 3 (infrastructure data), Plan 4 (wire-up + backtest).
```

- [ ] **Step 5: Final commit**

```bash
git add tests/integration/test_mlb_submarket_smoke.py DECISIONS.md
git commit -m "test(integration): MLB submarket smoke + docs(SPEC-R) — Plan 1 done"
```

- [ ] **Step 6: Plan dosyasını sil**

Plan 1 tamamlandı (CLAUDE.md "uygulama bittikten sonra durum: DONE → bu dosyadan sil"):

```bash
rm docs/superpowers/plans/2026-05-21-mlb-submarket-foundation.md
git add docs/superpowers/plans/2026-05-21-mlb-submarket-foundation.md
git commit -m "chore(plans): SPEC-R Plan 1 (foundation) tamamlandı — kayıt DECISIONS §B"
```

---

## Done

Plan 1 tamamlandığında bot şu durumda:
- MLB totals/run-line market'leri için scanner anchor='model' yolunu seçer
- Eğer engine inject edilmişse (Plan 4'te), `process_signals` ile pozisyon açar
- `portfolio_guards.py` DRY: gate ve process_signals aynı modülü kullanır
- `config.mlb_submarket.enabled = False` default → mevcut bot davranışı değişmez
- 10 task, ~30-40 commit, tüm testler yeşil

**Sonraki adım:** Plan 2 yazımı (domain model — rate shrinker, Log5, Markov, simulators, pricers).
