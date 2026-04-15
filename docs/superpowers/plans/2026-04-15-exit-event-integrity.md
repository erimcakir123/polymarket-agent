# Exit Event Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap'te realized PnL'i `trade_history.jsonl`'den reconcile et + scale-out partial exit'leri trade_history'e yaz, böylece bot crash sonrası realized değer doğru restore olur.

**Architecture:** TradeRecord'a `partial_exits` listesi eklenir; `TradeHistoryLogger` `_rewrite_matching` private helper'ı ile DRY atomic rewrite yapar (`update_on_exit` ve yeni `log_partial_exit` paylaşır). `PortfolioManager` `recalculate_bankroll(initial)` public metodu kazanır; bootstrap'teki `_reconcile_realized_pnl` true realized hesaplayıp uyumsuzsa snapshot'ı düzeltir. Agent scale-out branch'ı `_execute_partial_exit` adıyla ayrı metoda extract edilir, içine logger çağrısı eklenir.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, JSONL append-only log.

**Spec:** [docs/superpowers/specs/2026-04-15-exit-event-integrity-design.md](../specs/2026-04-15-exit-event-integrity-design.md)

---

## File Structure

**Backend:**
- Modify: `src/infrastructure/persistence/trade_logger.py` — `TradeRecord.partial_exits` field, `_rewrite_matching` helper, `log_partial_exit` metod, `update_on_exit` helper'ı kullansın
- Modify: `src/domain/portfolio/manager.py` — `recalculate_bankroll(initial_bankroll)` public metod, `from_snapshot` onu kullansın
- Modify: `src/orchestration/agent.py` — scale-out branch'ı `_execute_partial_exit` ayrı metoda çıkar + logger çağrısı
- Modify: `src/orchestration/startup.py` — `_reconcile_realized_pnl` + bootstrap çağrısı; trade_logger dependency

**Tests (yeni veya güncellenecek):**
- Modify: `tests/unit/infrastructure/persistence/test_trade_logger.py` — `log_partial_exit` testleri + backward-compat
- Modify: `tests/unit/domain/portfolio/test_manager.py` — `recalculate_bankroll` testleri
- Create: `tests/unit/orchestration/test_startup_reconcile.py` — reconcile senaryoları
- Create: `tests/unit/orchestration/test_agent_scale_out_log.py` — partial exit'te logger çağrısı

---

## Task 1: TradeRecord.partial_exits field

**Files:**
- Modify: `src/infrastructure/persistence/trade_logger.py` (TradeRecord class)
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py`

### ARCH_GUARD self-check (her Edit/Write öncesi yazılır)
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

- [ ] **Step 1: Failing testi yaz**

`tests/unit/infrastructure/persistence/test_trade_logger.py` dosyasının sonuna ekle:

```python
def test_trade_record_default_partial_exits_is_empty_list():
    """Yeni TradeRecord oluşturulduğunda partial_exits varsayılan boş liste."""
    from src.infrastructure.persistence.trade_logger import TradeRecord
    record = TradeRecord(
        slug="x", condition_id="cid", event_id="e", token_id="t",
        sport_tag="mlb", sport_category="mlb", league="",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        confidence="A", bookmaker_prob=0.6, anchor_probability=0.6,
        entry_reason="consensus", entry_timestamp="2026-04-15T00:00:00Z",
    )
    assert record.partial_exits == []


def test_trade_record_accepts_partial_exits():
    """TradeRecord partial_exits listesi kabul etmeli."""
    from src.infrastructure.persistence.trade_logger import TradeRecord
    pe_data = [{"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
                "timestamp": "2026-04-15T01:00:00Z"}]
    record = TradeRecord(
        slug="x", condition_id="cid", event_id="e", token_id="t",
        sport_tag="mlb", sport_category="mlb", league="",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        confidence="A", bookmaker_prob=0.6, anchor_probability=0.6,
        entry_reason="consensus", entry_timestamp="2026-04-15T00:00:00Z",
        partial_exits=pe_data,
    )
    assert record.partial_exits == pe_data
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py::test_trade_record_default_partial_exits_is_empty_list tests/unit/infrastructure/persistence/test_trade_logger.py::test_trade_record_accepts_partial_exits -v`
Expected: FAIL — `Pydantic ValidationError: extra field 'partial_exits' not allowed`

- [ ] **Step 3: Implementation — TradeRecord'a field ekle**

`src/infrastructure/persistence/trade_logger.py` dosyasında `TradeRecord` class içinde "Resolution" bloğunun ÖNCESİNE (yaklaşık satır 73, `# ── Resolution ──` yorumundan önce) ekle:

```python
    # ── Scale-out partial exit'ler (her tier için bir kayıt) ──
    partial_exits: list[dict] = []
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v`
Expected: tüm testler PASS (yeni 2 + mevcut testler).

- [ ] **Step 5: Commit**

```bash
git -c user.email=dev@local -c user.name=dev add src/infrastructure/persistence/trade_logger.py tests/unit/infrastructure/persistence/test_trade_logger.py
git -c user.email=dev@local -c user.name=dev commit -m "feat(trade_logger): add partial_exits field to TradeRecord"
```

---

## Task 2: _rewrite_matching DRY helper

**Files:**
- Modify: `src/infrastructure/persistence/trade_logger.py` (TradeHistoryLogger class)

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

- [ ] **Step 1: Mevcut test'leri çalıştır (regression baseline)**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -q`
Expected: PASS. Bu sayı baseline.

- [ ] **Step 2: TradeHistoryLogger.update_on_exit'i private helper'a refactor et**

`src/infrastructure/persistence/trade_logger.py` dosyasında mevcut `update_on_exit` metodunu (yaklaşık satır 110-129) ŞU KODLA DEĞİŞTİR:

```python
    def _rewrite_matching(self, condition_id: str, mutator) -> bool:
        """En son açık (exit_price=None) kaydı bul, mutator(rec) çağır, atomic rewrite et.

        Atomic = tmp dosyaya yaz + replace. Crash-safe.
        Return: matching record bulundu mu.
        """
        records = self.read_all()
        updated = False
        for rec in reversed(records):
            if rec.get("condition_id") == condition_id and rec.get("exit_price") is None:
                mutator(rec)
                updated = True
                break
        if not updated:
            return False
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
        tmp.replace(self.path)
        return True

    def update_on_exit(self, condition_id: str, exit_data: dict[str, Any]) -> bool:
        """condition_id için en son açık (exit_price=None) kaydı exit verisiyle günceller.
        Atomic rewrite. Return: güncellendi mi?
        """
        return self._rewrite_matching(condition_id, lambda rec: rec.update(exit_data))
```

- [ ] **Step 3: Mevcut test'leri çalıştır (davranış aynı kalmalı)**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -q`
Expected: PASS — refactor davranışı korumalı.

- [ ] **Step 4: Commit**

```bash
git -c user.email=dev@local -c user.name=dev add src/infrastructure/persistence/trade_logger.py
git -c user.email=dev@local -c user.name=dev commit -m "refactor(trade_logger): extract _rewrite_matching helper from update_on_exit"
```

---

## Task 3: TradeHistoryLogger.log_partial_exit

**Files:**
- Modify: `src/infrastructure/persistence/trade_logger.py`
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py`

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (yeni metod _rewrite_matching kullanır), ✓ <400 satır, ✓ domain I/O yok (infrastructure), ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok (return False explicit), ✓ P(YES) anchor."

- [ ] **Step 1: Failing testleri yaz**

`tests/unit/infrastructure/persistence/test_trade_logger.py` dosyasının sonuna ekle:

```python
def test_log_partial_exit_appends_to_open_record(tmp_path):
    """Açık trade kaydının partial_exits listesine yeni partial eklenir."""
    from src.infrastructure.persistence.trade_logger import (
        TradeHistoryLogger, TradeRecord,
    )
    logger = TradeHistoryLogger(str(tmp_path / "trades.jsonl"))
    open_rec = TradeRecord(
        slug="x", condition_id="cid", event_id="e", token_id="t",
        sport_tag="mlb", sport_category="mlb", league="",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        confidence="A", bookmaker_prob=0.6, anchor_probability=0.6,
        entry_reason="consensus", entry_timestamp="2026-04-15T00:00:00Z",
    )
    logger.log(open_rec)

    ok = logger.log_partial_exit(
        condition_id="cid", tier=1, sell_pct=0.4,
        realized_pnl_usdc=5.0, timestamp="2026-04-15T01:00:00Z",
    )
    assert ok is True

    records = logger.read_all()
    assert len(records) == 1
    assert records[0]["partial_exits"] == [
        {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
         "timestamp": "2026-04-15T01:00:00Z"}
    ]


def test_log_partial_exit_appends_multiple_tiers(tmp_path):
    """Aynı pozisyona iki kez partial exit (Tier1 + Tier2) eklenebilir."""
    from src.infrastructure.persistence.trade_logger import (
        TradeHistoryLogger, TradeRecord,
    )
    logger = TradeHistoryLogger(str(tmp_path / "trades.jsonl"))
    logger.log(TradeRecord(
        slug="x", condition_id="cid", event_id="e", token_id="t",
        sport_tag="mlb", sport_category="mlb", league="",
        direction="BUY_YES", entry_price=0.5, size_usdc=50.0, shares=100.0,
        confidence="A", bookmaker_prob=0.6, anchor_probability=0.6,
        entry_reason="consensus", entry_timestamp="2026-04-15T00:00:00Z",
    ))
    logger.log_partial_exit(condition_id="cid", tier=1, sell_pct=0.4,
                            realized_pnl_usdc=5.0, timestamp="t1")
    logger.log_partial_exit(condition_id="cid", tier=2, sell_pct=0.5,
                            realized_pnl_usdc=8.0, timestamp="t2")
    records = logger.read_all()
    assert len(records[0]["partial_exits"]) == 2
    assert records[0]["partial_exits"][0]["tier"] == 1
    assert records[0]["partial_exits"][1]["tier"] == 2


def test_log_partial_exit_returns_false_if_no_open_record(tmp_path):
    """Eşleşen açık kayıt yoksa False döner, dosya değişmez."""
    from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
    logger = TradeHistoryLogger(str(tmp_path / "trades.jsonl"))
    ok = logger.log_partial_exit(
        condition_id="missing", tier=1, sell_pct=0.4,
        realized_pnl_usdc=5.0, timestamp="t1",
    )
    assert ok is False
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py::test_log_partial_exit_appends_to_open_record -v`
Expected: FAIL — `AttributeError: 'TradeHistoryLogger' object has no attribute 'log_partial_exit'`

- [ ] **Step 3: Implementation — log_partial_exit ekle**

`src/infrastructure/persistence/trade_logger.py` dosyasında `update_on_exit` metodunun ALTINA ekle:

```python
    def log_partial_exit(self, condition_id: str, tier: int, sell_pct: float,
                         realized_pnl_usdc: float, timestamp: str) -> bool:
        """En son açık trade kaydının partial_exits listesine bir partial ekle.
        Atomic rewrite. Return: kayıt bulundu mu.
        """
        entry = {
            "tier": tier,
            "sell_pct": sell_pct,
            "realized_pnl_usdc": realized_pnl_usdc,
            "timestamp": timestamp,
        }

        def append_partial(rec: dict) -> None:
            existing = rec.get("partial_exits") or []
            existing.append(entry)
            rec["partial_exits"] = existing

        return self._rewrite_matching(condition_id, append_partial)
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v`
Expected: tüm testler PASS (3 yeni + mevcut).

- [ ] **Step 5: Commit**

```bash
git -c user.email=dev@local -c user.name=dev add src/infrastructure/persistence/trade_logger.py tests/unit/infrastructure/persistence/test_trade_logger.py
git -c user.email=dev@local -c user.name=dev commit -m "feat(trade_logger): add log_partial_exit for scale-out events"
```

---

## Task 4: PortfolioManager.recalculate_bankroll (DRY)

**Files:**
- Modify: `src/domain/portfolio/manager.py`
- Test: `tests/unit/domain/portfolio/test_manager.py`

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (formül tek yerde), ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni (domain), ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

- [ ] **Step 1: Failing testleri yaz**

`tests/unit/domain/portfolio/test_manager.py` dosyasının sonuna ekle:

```python
def test_recalculate_bankroll_no_positions():
    """Hiç pozisyon yok: bankroll = initial + realized."""
    from src.domain.portfolio.manager import PortfolioManager
    mgr = PortfolioManager(initial_bankroll=1000.0)
    mgr.realized_pnl = -50.0
    mgr.recalculate_bankroll(1000.0)
    assert mgr.bankroll == 950.0


def test_recalculate_bankroll_with_invested_positions():
    """Açık pozisyon size_usdc'leri çıkarılır: bankroll = initial + realized - invested."""
    from src.domain.portfolio.manager import PortfolioManager
    from src.models.position import Position
    mgr = PortfolioManager(initial_bankroll=1000.0)
    mgr.realized_pnl = -20.0
    mgr.positions["a"] = Position(
        condition_id="a", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=100.0, shares=200.0,
        slug="a", entry_timestamp="2026-04-15T00:00:00Z",
        entry_reason="consensus", confidence="A",
        anchor_probability=0.5, current_price=0.5,
        sport_tag="mlb", event_id="e1",
    )
    mgr.recalculate_bankroll(1000.0)
    # 1000 - 20 - 100 = 880
    assert mgr.bankroll == 880.0
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/domain/portfolio/test_manager.py::test_recalculate_bankroll_no_positions -v`
Expected: FAIL — `AttributeError: 'PortfolioManager' object has no attribute 'recalculate_bankroll'`

- [ ] **Step 3: Implementation**

`src/domain/portfolio/manager.py` dosyasında `from_snapshot` metodunun ALTINA ekle (yaklaşık satır 50'den sonra):

```python
    def recalculate_bankroll(self, initial_bankroll: float) -> None:
        """Bankroll'u baştan türet: initial + realized − açık pozisyonların toplam size'ı.

        Crash recovery sonrası state düzeltmeleri için kullanılır.
        """
        invested = sum(p.size_usdc for p in self.positions.values())
        self.bankroll = initial_bankroll + self.realized_pnl - invested
        self.high_water_mark = max(self.high_water_mark, self.bankroll)
```

Şimdi `from_snapshot` (satır 39-49) içindeki manuel hesaplamayı bu metoda DELEGE et. Mevcut:

```python
    @classmethod
    def from_snapshot(cls, data: dict, initial_bankroll: float = 1000.0) -> "PortfolioManager":
        mgr = cls(initial_bankroll=initial_bankroll)
        mgr.realized_pnl = data.get("realized_pnl", 0.0)
        for cid, pos_data in data.get("positions", {}).items():
            mgr.positions[cid] = Position(**pos_data)
        # Bankroll: initial + realized − yatırılan
        invested = sum(p.size_usdc for p in mgr.positions.values())
        mgr.bankroll = initial_bankroll + mgr.realized_pnl - invested
        mgr.high_water_mark = max(data.get("high_water_mark", initial_bankroll), mgr.bankroll)
        return mgr
```

ŞU KODLA DEĞİŞTİR:

```python
    @classmethod
    def from_snapshot(cls, data: dict, initial_bankroll: float = 1000.0) -> "PortfolioManager":
        mgr = cls(initial_bankroll=initial_bankroll)
        mgr.realized_pnl = data.get("realized_pnl", 0.0)
        for cid, pos_data in data.get("positions", {}).items():
            mgr.positions[cid] = Position(**pos_data)
        mgr.high_water_mark = data.get("high_water_mark", initial_bankroll)
        mgr.recalculate_bankroll(initial_bankroll)
        return mgr
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/domain/portfolio/test_manager.py -v`
Expected: tüm testler PASS (yeni 2 + mevcut from_snapshot testleri korunur).

- [ ] **Step 5: Regression**

Run: `pytest tests/unit/ -q`
Expected: 619+ testler PASS.

- [ ] **Step 6: Commit**

```bash
git -c user.email=dev@local -c user.name=dev add src/domain/portfolio/manager.py tests/unit/domain/portfolio/test_manager.py
git -c user.email=dev@local -c user.name=dev commit -m "refactor(portfolio): extract recalculate_bankroll for DRY across from_snapshot+reconcile"
```

---

## Task 5: Agent _execute_partial_exit extract + scale-out log

**Files:**
- Modify: `src/orchestration/agent.py` (mevcut `_execute_exit` scale-out branch)
- Test: `tests/unit/orchestration/test_agent_scale_out_log.py` (yeni)

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (extract), ✓ <400 satır (refactor net düşürür), ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor."

- [ ] **Step 1: Failing testi yaz**

Oluştur: `tests/unit/orchestration/test_agent_scale_out_log.py`

```python
"""Agent scale-out branch — partial exit'te trade_logger.log_partial_exit çağrılmalı."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import AppConfig
from src.models.position import Position
from src.orchestration.agent import Agent, AgentDeps
from src.strategy.exit.monitor import ExitSignal
from src.strategy.exit.scale_out import ExitReason


def _make_deps_with_position():
    state = MagicMock()
    state.config = AppConfig()
    pos = Position(
        condition_id="cid",
        token_id="t",
        direction="BUY_YES",
        entry_price=0.5,
        size_usdc=100.0,
        shares=200.0,
        current_price=0.6,
        anchor_probability=0.5,
        entry_reason="consensus",
        confidence="A",
        sport_tag="mlb",
        event_id="e1",
        slug="a",
        entry_timestamp="2026-04-15T00:00:00Z",
    )
    state.portfolio.positions = {"cid": pos}
    state.portfolio.bankroll = 1000.0
    state.portfolio.add_position.return_value = True
    return AgentDeps(
        state=state,
        scanner=MagicMock(),
        cycle_manager=MagicMock(),
        executor=MagicMock(),
        odds_client=MagicMock(),
        trade_logger=MagicMock(),
        gate=MagicMock(),
        cooldown=MagicMock(),
        equity_logger=MagicMock(),
        skipped_logger=MagicMock(),
        eligible_snapshot=MagicMock(),
        bot_status_writer=MagicMock(),
        price_feed=None,
    ), pos


def test_execute_partial_exit_calls_trade_logger_with_tier_and_pnl():
    """Scale-out partial exit'te trade_logger.log_partial_exit doğru argümanlarla çağrılır."""
    deps, pos = _make_deps_with_position()
    agent = Agent(deps)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT_TIER1,
        partial=True,
        sell_pct=0.4,
        tier=1,
    )
    agent._execute_exit(pos, signal)

    assert deps.trade_logger.log_partial_exit.called
    kwargs = deps.trade_logger.log_partial_exit.call_args.kwargs
    assert kwargs["condition_id"] == "cid"
    assert kwargs["tier"] == 1
    assert kwargs["sell_pct"] == 0.4
    # pos.unrealized_pnl_usdc * 0.4 — pozisyon entry 0.5, current 0.6, shares 200
    # unrealized = 200 * (0.6 - 0.5) = 20; partial = 20 * 0.4 = 8.0
    assert abs(kwargs["realized_pnl_usdc"] - 8.0) < 0.01
    assert "timestamp" in kwargs


def test_execute_partial_exit_does_not_call_remove_position():
    """Partial exit pozisyonu silmemeli."""
    deps, pos = _make_deps_with_position()
    agent = Agent(deps)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT_TIER1,
        partial=True,
        sell_pct=0.4,
        tier=1,
    )
    agent._execute_exit(pos, signal)

    assert not deps.state.portfolio.remove_position.called
    assert deps.state.portfolio.apply_partial_exit.called
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/orchestration/test_agent_scale_out_log.py -v`
Expected: FAIL — `assert deps.trade_logger.log_partial_exit.called` (logger çağrılmıyor).

- [ ] **Step 3: Implementation — _execute_partial_exit extract + log çağrısı**

`src/orchestration/agent.py` dosyasını oku, `_execute_exit` metodunu bul (yaklaşık satır 291). Mevcut yapı:

```python
    def _execute_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Exit sinyalini execute et — full veya partial (scale-out)."""
        if signal.partial:
            shares_to_sell = pos.shares * signal.sell_pct
            realized = pos.unrealized_pnl_usdc * signal.sell_pct
            pos.shares -= shares_to_sell
            pos.size_usdc *= (1 - signal.sell_pct)
            pos.scale_out_tier = signal.tier or pos.scale_out_tier
            pos.scale_out_realized_usdc += realized
            self.deps.state.portfolio.apply_partial_exit(pos.condition_id, realized_usdc=realized)
            logger.info("SCALE-OUT %s: tier=%d sold=%.1f shares realized=$%.2f remaining=$%.2f",
                        pos.slug[:35], signal.tier, shares_to_sell, realized, pos.size_usdc)
            return
        # Full exit
        # ... (geri kalan tüm full exit kodu olduğu gibi kalır)
```

ŞU KODLA DEĞİŞTİR (sadece scale-out branch'ı extract et, full exit kodu olduğu gibi kalır):

```python
    def _execute_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Exit sinyalini execute et — full veya partial (scale-out)."""
        if signal.partial:
            self._execute_partial_exit(pos, signal)
            return

        # Full exit
        self.deps.executor.exit_position(pos, reason=signal.reason.value)
        # ... (mevcut full exit kodu burada DEĞİŞMEDEN devam eder)
```

(Dikkat: yukarıdaki `# ...` mevcut full exit kodunun bütünlüğünü temsil eder. Implementasyon sırasında tüm satırlar korunur.)

`_execute_exit` altına yeni metod EKLE:

```python
    def _execute_partial_exit(self, pos: Position, signal: ExitSignal) -> None:
        """Scale-out partial exit: pozisyon korunur, tier/shares/realized güncellenir,
        trade_history'e partial kayıt yazılır.
        """
        shares_to_sell = pos.shares * signal.sell_pct
        realized = pos.unrealized_pnl_usdc * signal.sell_pct
        pos.shares -= shares_to_sell
        pos.size_usdc *= (1 - signal.sell_pct)
        pos.scale_out_tier = signal.tier or pos.scale_out_tier
        pos.scale_out_realized_usdc += realized
        self.deps.state.portfolio.apply_partial_exit(pos.condition_id, realized_usdc=realized)
        self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(
            "SCALE-OUT %s: tier=%d sold=%.1f shares realized=$%.2f remaining=$%.2f",
            pos.slug[:35], signal.tier, shares_to_sell, realized, pos.size_usdc,
        )
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/orchestration/test_agent_scale_out_log.py -v`
Expected: 2 yeni test PASS.

- [ ] **Step 5: Regression**

Run: `pytest tests/unit/ -q`
Expected: tüm testler PASS.

- [ ] **Step 6: Satır sayısı kontrolü**

Run: `wc -l src/orchestration/agent.py`
Expected: < 400. Refactor sonucu ana _execute_exit kısaldı, yeni _execute_partial_exit eklendi → net küçük artış (~5-7 satır), 400 altında kalmalı. Eğer 400 aşılırsa BLOCKED — başka extract gerekli.

- [ ] **Step 7: Commit**

```bash
git -c user.email=dev@local -c user.name=dev add src/orchestration/agent.py tests/unit/orchestration/test_agent_scale_out_log.py
git -c user.email=dev@local -c user.name=dev commit -m "feat(agent): extract _execute_partial_exit + log scale-out to trade_history"
```

---

## Task 6: Startup _reconcile_realized_pnl

**Files:**
- Modify: `src/orchestration/startup.py`
- Test: `tests/unit/orchestration/test_startup_reconcile.py` (yeni)

### ARCH_GUARD self-check
> "ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY (recalculate_bankroll çağırır), ✓ <400 satır, ✓ domain I/O yok (orchestration disk okur), ✓ katman düzeni (orchestration → infrastructure), ✓ magic number yok (0.01 yorumlu), ✓ utils/helpers/misc yok, ✓ sessiz hata yok (warning log), ✓ P(YES) anchor."

- [ ] **Step 1: Failing testleri yaz**

Oluştur: `tests/unit/orchestration/test_startup_reconcile.py`

```python
"""Startup reconciliation — trade_history.jsonl vs portfolio snapshot uyumsuzluk düzeltimi."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.domain.portfolio.manager import PortfolioManager
from src.orchestration.startup import _reconcile_realized_pnl


def _make_logger_with_records(records: list[dict]) -> MagicMock:
    logger = MagicMock()
    logger.read_all.return_value = records
    return logger


def test_reconcile_no_change_when_snapshot_matches_log():
    """Snapshot ve log eşit ise dokunulmaz (delta < 0.01)."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -30.0
    pm.bankroll = 970.0
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.4, "exit_pnl_usdc": -30.0},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert pm.realized_pnl == -30.0
    assert pm.bankroll == 970.0


def test_reconcile_overrides_snapshot_when_log_differs():
    """Log -82, snapshot -46 → log kazanır, bankroll yeniden türetilir."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -46.0
    pm.bankroll = 954.0  # eski yanlış değer
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.27, "exit_pnl_usdc": -17.07, "partial_exits": []},
        {"exit_price": 0.27, "exit_pnl_usdc": -19.32, "partial_exits": []},
        {"exit_price": 0.34, "exit_pnl_usdc": -15.31, "partial_exits": []},
        {"exit_price": 0.29, "exit_pnl_usdc": -15.48, "partial_exits": []},
        {"exit_price": 0.41, "exit_pnl_usdc": -14.97, "partial_exits": []},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert abs(pm.realized_pnl - (-82.15)) < 0.01
    assert abs(pm.bankroll - (1000.0 - 82.15)) < 0.01  # invested=0


def test_reconcile_includes_partial_exits():
    """Partial exit'ler de toplama dahil."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = 0.0
    pm.bankroll = 1000.0
    trade_logger = _make_logger_with_records([
        {
            "exit_price": None,
            "exit_pnl_usdc": 0.0,
            "partial_exits": [
                {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0, "timestamp": "t1"},
                {"tier": 2, "sell_pct": 0.5, "realized_pnl_usdc": 8.0, "timestamp": "t2"},
            ],
        },
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert abs(pm.realized_pnl - 13.0) < 0.01


def test_reconcile_empty_log_leaves_zero():
    """Boş log + zero snapshot → noop."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    trade_logger = _make_logger_with_records([])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert pm.realized_pnl == 0.0
    assert pm.bankroll == 1000.0
```

- [ ] **Step 2: Test çalıştır, fail bekle**

Run: `pytest tests/unit/orchestration/test_startup_reconcile.py -v`
Expected: FAIL — `ImportError: cannot import name '_reconcile_realized_pnl'`

- [ ] **Step 3: Implementation — _reconcile_realized_pnl ekle**

`src/orchestration/startup.py` dosyasının `_restore_blacklist` fonksiyonundan SONRA (yaklaşık satır 124) ekle:

```python
def _reconcile_realized_pnl(portfolio: PortfolioManager, trade_logger,
                            initial_bankroll: float) -> None:
    """trade_history.jsonl'dan true realized hesapla, portfolio snapshot'ıyla
    uyumsuzsa düzelt + bankroll'u yeniden türet (crash recovery sonrası).

    True realized = sum(full_exit.exit_pnl_usdc) + sum(partial_exits.realized_pnl_usdc).
    """
    records = trade_logger.read_all()
    true_realized = 0.0
    for rec in records:
        for pe in rec.get("partial_exits") or []:
            true_realized += float(pe.get("realized_pnl_usdc", 0.0))
        if rec.get("exit_price") is not None:
            true_realized += float(rec.get("exit_pnl_usdc", 0.0))

    delta = true_realized - portfolio.realized_pnl
    if abs(delta) < 0.01:  # floating noise — eşit kabul
        return

    logger.warning(
        "Realized PnL reconciliation: snapshot=$%.2f, log=$%.2f, delta=$%+.2f — using log",
        portfolio.realized_pnl, true_realized, delta,
    )
    portfolio.realized_pnl = true_realized
    portfolio.recalculate_bankroll(initial_bankroll)
```

- [ ] **Step 4: Test çalıştır, pass bekle**

Run: `pytest tests/unit/orchestration/test_startup_reconcile.py -v`
Expected: 4 test PASS.

- [ ] **Step 5: Bootstrap'e çağrıyı ekle**

`src/orchestration/startup.py::bootstrap()` fonksiyonunda `_restore_blacklist` çağrısından SONRA (yaklaşık satır 65) trade_logger lazım. Mevcut bootstrap'in yapısına bak — `TradeHistoryLogger` import edilmemiş.

Önce dosyanın başına import ekle:

```python
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
```

`_TRADE_HISTORY_FILE` sabitini diğerleriyle yan yana ekle (yaklaşık satır 30):

```python
_TRADE_HISTORY_FILE = "logs/trade_history.jsonl"
```

`bootstrap` fonksiyonunda blacklist restore'dan SONRA, `logger.info("Bootstrap complete...")` çağrısından ÖNCE şu satırları ekle:

```python
    # Reconcile realized PnL — trade_history.jsonl ground truth
    trade_logger = TradeHistoryLogger(str(logs / "trade_history.jsonl"))
    _reconcile_realized_pnl(portfolio, trade_logger, config.initial_bankroll)
```

- [ ] **Step 6: Test çalıştır, pass bekle (regression)**

Run: `pytest tests/unit/orchestration/ -q`
Expected: Tüm testler PASS. Eğer mevcut bootstrap testleri (`test_startup.py` varsa) trade_history.jsonl yokluğunda kırılırsa: TradeHistoryLogger zaten var olmayan dosya için `read_all` = `[]` döner (`if not self.path.exists(): return []`), reconcile noop olur.

- [ ] **Step 7: Tüm regression**

Run: `pytest tests/unit/ -q`
Expected: 619+ testler PASS.

- [ ] **Step 8: Commit**

```bash
git -c user.email=dev@local -c user.name=dev add src/orchestration/startup.py tests/unit/orchestration/test_startup_reconcile.py
git -c user.email=dev@local -c user.name=dev commit -m "feat(startup): reconcile portfolio realized_pnl from trade_history on bootstrap"
```

---

## Task 7: Bot restart + manuel doğrulama

**Files:** (yok — runtime adımı)

- [ ] **Step 1: Mevcut bot/dashboard process'lerini durdur**

Run:
```bash
wmic process where "name='python.exe'" get ProcessId,CommandLine 2>&1 | grep -E "src.main|dashboard.app"
```
Çıkan PID'leri taşkill ile kapat:
```bash
taskkill //F //PID <PID1> //PID <PID2> ...
```

- [ ] **Step 2: Bot'u arka planda başlat**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m src.main
```
(run_in_background: true)

- [ ] **Step 3: Bot log'unda reconciliation warning'ini doğrula**

Run: `tail -10 logs/bot.log`
Beklenen satır (mevcut yanlış realized varsa): `WARNING ... Realized PnL reconciliation: snapshot=$-46.08, log=$-82.15, delta=$-36.07 — using log`

Eğer yoksa snapshot zaten doğruymuş demektir.

- [ ] **Step 4: positions.json'da realized_pnl güncellenmesini doğrula**

Bir sonraki `persist` çağrısı sonrası (~5sn light cycle):
```bash
python -c "import json; print(json.load(open('logs/positions.json'))['realized_pnl'])"
```
Beklenen: `-82.15` (veya gerçek log toplamı).

- [ ] **Step 5: Dashboard'u arka planda başlat**

```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -m src.presentation.dashboard.app
```
(run_in_background: true)

- [ ] **Step 6: Dashboard'da Realized P&L kartını doğrula**

Tarayıcıda dashboard'ı yenile. Realized P&L kartında artık `-$82.15` olmalı (eskiden `-$46.08`). Branches toplamıyla tutarlı.

---

## Self-Review

**1. Spec coverage:**
- TradeRecord.partial_exits field → Task 1 ✓
- TradeHistoryLogger.log_partial_exit → Task 3 ✓
- _rewrite_matching DRY helper → Task 2 ✓
- PortfolioManager.recalculate_bankroll DRY → Task 4 ✓
- Agent _execute_partial_exit extract + log → Task 5 ✓
- Startup _reconcile_realized_pnl + bootstrap çağrısı → Task 6 ✓
- E2E doğrulama → Task 7 ✓
- Hata toleransı (boş log, missing record) → testlerde kapsanıyor ✓
- Scope-out (VS flag, dashboard UI, dead code) → spec'te belirtildi, plana dahil edilmedi ✓

**2. Placeholder scan:** TBD/TODO yok; her step'te gerçek kod blokları var. "Similar to..." yok.

**3. Type/signature consistency:**
- `log_partial_exit(condition_id, tier, sell_pct, realized_pnl_usdc, timestamp)` — Task 3 imzası ile Task 5 çağrısı ve Task 6 reconcile parsing'i tutarlı.
- `recalculate_bankroll(initial_bankroll)` — Task 4 tanımı ile Task 6 çağrısı tutarlı.
- `_reconcile_realized_pnl(portfolio, trade_logger, initial_bankroll)` — Task 6 imzası ile bootstrap çağrısı tutarlı.
- TradeRecord.partial_exits item şeması: `{tier, sell_pct, realized_pnl_usdc, timestamp}` — Task 3 yazımı ile Task 6 okuması tutarlı.

**4. Risk noktaları:**
- Task 5 sonrası agent.py ~400 satıra yaklaşır. Refactor net düşürür ama yine de izlemek lazım.
- Task 6 bootstrap'e yeni I/O ekler — test mock'larında `read_all` MagicMock olduğundan etkilenmez.
- Mevcut `update_on_exit` davranışı korunmalı — Task 2 sadece refactor, Task 3 yeni ekleme; mevcut testler regression olarak yakalar.
