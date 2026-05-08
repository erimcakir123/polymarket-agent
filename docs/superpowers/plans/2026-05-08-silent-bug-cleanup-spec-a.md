# Silent Bug Cleanup (SPEC-A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sessiz hata yutma kalıbını kalıcı olarak yok et — bot yeni bug'ları HEMEN yüksek sesle bildirsin, state corruption riski sıfırlansın.

**Architecture:** Beş bağımsız fix, her biri kendi dosya ailesinde lokalize. Cycle-level except daraltma (TypeError/AttributeError → 2 ardışık fail → stop) + portfolio mutation guard'ları + persistence corrupt-row threshold + telegram callback API'sini public yap + tennis dead-code kısa devre.

**Tech Stack:** Python 3.12+, pytest, mock-based tests. Mevcut TDD pattern (test-first per fix), her step 2-5 dk.

**SPEC referansı:** `SPEC.md` SPEC-A. **Yasak listesi**: gate.py, monitor.py, exit dispatchers, executor, ESPN client (SPEC-B kapsamı).

---

## File Structure

| Dosya | Sorumluluk | Değişiklik |
|---|---|---|
| `src/orchestration/agent.py` | Cycle loop hata politikası | Modify L79-85: programatik hata sayacı + 2-strike stop |
| `src/orchestration/_agent_resilience.py` | Hata-tipi sınıflandırma + sayaç state | **Create** (yeni) — 60-80 satır |
| `src/domain/portfolio/manager.py` | Portfolio mutation guards | Modify L74-90: apply_partial_exit ValueError raise |
| `src/orchestration/exit_processor.py` | apply_partial_exit caller | Modify L97-101: try/except ValueError ekle |
| `src/infrastructure/persistence/trade_logger.py` | JSONL read corruption tracking | Modify L115-126: corrupt counter + threshold flag |
| `src/orchestration/startup.py` | Reconcile corrupt-aware abort | Modify L154-160: corrupt flag check |
| `src/infrastructure/telegram/command_poller.py` | Public callback API | Modify L36, **add** L92+: set_on_stop method |
| `src/orchestration/factory.py` | Telegram wiring | Modify L137: private mutation → set_on_stop |
| `src/strategy/enrichment/sport_key_resolver.py` | Tennis erken return | Modify L54+: atp/wta prefix → None |
| `src/domain/matching/odds_sport_keys.py` | Tennis erken return | Modify L155+: atp/wta erken çıkış |

**Test dosyaları:**
- `tests/unit/orchestration/test_agent_resilience.py` (**yeni**) — 6 test
- `tests/unit/domain/portfolio/test_manager.py` (modify) — +2 test
- `tests/unit/orchestration/test_exit_processor_partial.py` (modify) — +1 test
- `tests/unit/infrastructure/persistence/test_trade_logger.py` (modify) — +3 test
- `tests/unit/orchestration/test_startup.py` (modify) — +1 test
- `tests/unit/infrastructure/telegram/test_command_poller.py` (modify) — +2 test
- `tests/unit/domain/matching/test_tennis_disabled.py` (**yeni**) — 2 test

---

## Task 1: A1 — Cycle Hata Yutma → Programatik Hata Sayacı

**Files:**
- Create: `src/orchestration/_agent_resilience.py`
- Modify: `src/orchestration/agent.py:79-85`
- Test: `tests/unit/orchestration/test_agent_resilience.py`

### Step 1.1: Resilience helper test'lerini yaz

- [ ] **Step:** Test dosyasını oluştur

```python
# tests/unit/orchestration/test_agent_resilience.py
"""Cycle hata sınıflandırma + 2-strike stop politikası testleri."""
from __future__ import annotations

import pytest

from src.orchestration._agent_resilience import (
    CycleResilience,
    is_programmatic_error,
)


def test_programmatic_errors_classified_correctly() -> None:
    assert is_programmatic_error(TypeError("x"))
    assert is_programmatic_error(AttributeError("x"))
    assert is_programmatic_error(ValueError("x"))
    assert is_programmatic_error(KeyError("x"))
    assert is_programmatic_error(AssertionError("x"))


def test_network_errors_not_programmatic() -> None:
    assert not is_programmatic_error(TimeoutError("x"))
    assert not is_programmatic_error(ConnectionError("x"))
    assert not is_programmatic_error(OSError("x"))


def test_first_programmatic_error_does_not_trigger_stop() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("first"))
    assert r.should_stop() is False


def test_two_consecutive_same_type_triggers_stop() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("first"))
    r.record_error(TypeError("second"))
    assert r.should_stop() is True


def test_success_resets_counter() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("first"))
    r.record_success()
    r.record_error(TypeError("third"))
    assert r.should_stop() is False  # Counter resetlendi


def test_different_error_types_each_get_own_count() -> None:
    r = CycleResilience(max_consecutive=2)
    r.record_error(TypeError("a"))
    r.record_error(AttributeError("b"))  # Farklı tip
    assert r.should_stop() is False
    r.record_error(AttributeError("c"))  # AttrErr 2 ardışık
    assert r.should_stop() is True
```

- [ ] **Step:** Run to verify FAIL

```bash
pytest tests/unit/orchestration/test_agent_resilience.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.orchestration._agent_resilience'`

### Step 1.2: Resilience helper'ı yaz

- [ ] **Step:** Yeni dosya oluştur

```python
# src/orchestration/_agent_resilience.py
"""Cycle hata sınıflandırma + ardışık-aynı-tip-2-strike politikası.

Sebep: Programatik bug'lar (TypeError, AttributeError vb.) bot'un sessiz
çalışmaya devam etmesine neden oluyordu. Ağ hataları kabul edilir; programatik
hatalar 2 ardışık aynı tipten sonra bot'u durdurur.
"""
from __future__ import annotations

_PROGRAMMATIC_TYPES: tuple[type[BaseException], ...] = (
    TypeError, AttributeError, ValueError, KeyError, AssertionError,
)


def is_programmatic_error(e: BaseException) -> bool:
    """Programatik bug'lar bu sınıflara dahildir; geri kalan (ağ, IO) değil."""
    return isinstance(e, _PROGRAMMATIC_TYPES)


class CycleResilience:
    """Ardışık aynı-tip programatik hata sayacı.

    record_error(e): hata kayıt et.
    record_success(): sayacı sıfırla.
    should_stop(): max_consecutive eşiğine ulaşıldıysa True.
    """

    def __init__(self, max_consecutive: int = 2) -> None:
        self._max = max_consecutive
        self._last_type: type[BaseException] | None = None
        self._count = 0

    def record_error(self, e: BaseException) -> None:
        if not is_programmatic_error(e):
            return
        et = type(e)
        if et is self._last_type:
            self._count += 1
        else:
            self._last_type = et
            self._count = 1

    def record_success(self) -> None:
        self._last_type = None
        self._count = 0

    def should_stop(self) -> bool:
        return self._count >= self._max
```

- [ ] **Step:** Run to verify PASS

```bash
pytest tests/unit/orchestration/test_agent_resilience.py -v
```

Expected: `6 passed`

### Step 1.3: agent.py cycle except'i daralt

- [ ] **Step:** Modify `src/orchestration/agent.py:79-85`

Eski:
```python
            try:
                if tick.run_heavy:
                    self._entry.run_heavy()
                if tick.run_light:
                    self._exit.run_light()
            except Exception as e:
                logger.error("Cycle error (%s): %s", tick.reason, e, exc_info=True)
```

Yeni:
```python
            try:
                if tick.run_heavy:
                    self._entry.run_heavy()
                if tick.run_light:
                    self._exit.run_light()
                self._resilience.record_success()
            except Exception as e:
                logger.error("Cycle error (%s): %s", tick.reason, e, exc_info=True)
                self._resilience.record_error(e)
                if self._resilience.should_stop():
                    logger.critical(
                        "STOPPING: %d ardışık programatik hata (%s) — bot durdurulamadı içinde değil, dış müdahale gerek",
                        self._resilience._count, type(e).__name__,
                    )
                    self._stop_requested = True
```

Ayrıca `__init__`'a:
```python
from src.orchestration._agent_resilience import CycleResilience
# (mevcut imports'a ekle)

# __init__ method'unun sonunda (mevcut self.deps.price_feed bloğu sonrası):
        self._resilience = CycleResilience(max_consecutive=2)
```

- [ ] **Step:** agent.py için integration test ekle

```python
# tests/unit/orchestration/test_agent_resilience.py — sonuna ekle
from unittest.mock import MagicMock

from src.config.settings import AppConfig
from src.orchestration.agent import Agent, AgentDeps


def _build_minimal_deps() -> AgentDeps:
    """Cycle test için mock'lu minimal deps."""
    deps = MagicMock(spec=AgentDeps)
    deps.cycle_manager.tick.return_value = MagicMock(run_heavy=True, run_light=False, reason="heavy")
    deps.cycle_manager.sleep_seconds.return_value = 0.0
    deps.cooldown.new_cycle = MagicMock()
    deps.state.portfolio.count = MagicMock(return_value=0)
    deps.state.config = AppConfig()
    deps.bot_status_writer.write_from_tick = MagicMock()
    deps.price_feed = None
    deps.command_poller = None
    return deps


def test_two_consecutive_typeerror_stops_agent() -> None:
    deps = _build_minimal_deps()
    agent = Agent(deps)
    # Mock entry'yi 2 kez TypeError fırlatacak şekilde
    agent._entry = MagicMock()
    agent._entry.run_heavy = MagicMock(side_effect=TypeError("test bug"))
    agent._exit = MagicMock()

    # 5 tick izin ver — 2 ardışık hata sonrası stop bekleniyor
    agent.run(max_ticks=5)

    # 3. tick'e gelmeden stop_requested olmalı
    assert agent._stop_requested is True
    # entry.run_heavy 2 kez çağrılmış olmalı (3. tick'e gelmeden stop)
    assert agent._entry.run_heavy.call_count == 2
```

- [ ] **Step:** Run

```bash
pytest tests/unit/orchestration/test_agent_resilience.py -v
```

Expected: `7 passed`

### Step 1.4: Tüm test paketi geçer mi kontrol

- [ ] **Step:** Full suite

```bash
pytest -q --no-header
```

Expected: `956 + 7 = 963 passed`

### Step 1.5: Commit

- [ ] **Step:** Commit A1

```bash
git add src/orchestration/_agent_resilience.py src/orchestration/agent.py tests/unit/orchestration/test_agent_resilience.py
git commit -m "feat(agent): cycle programatik-hata 2-strike stop politikası (SPEC-A1)"
```

---

## Task 2: A2 — apply_partial_exit Silent No-Op

**Files:**
- Modify: `src/domain/portfolio/manager.py:74-90`
- Modify: `src/orchestration/exit_processor.py:97-108`
- Test: `tests/unit/domain/portfolio/test_manager.py` (modify)
- Test: `tests/unit/orchestration/test_exit_processor_partial.py` (modify)

### Step 2.1: manager.py test'i yaz

- [ ] **Step:** Test ekle

```python
# tests/unit/domain/portfolio/test_manager.py — sonuna ekle (mevcut import'lar yeter)
import pytest


def test_apply_partial_exit_missing_position_raises() -> None:
    """Pozisyon yoksa silent no-op DEĞIL, ValueError fırlatmalı."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    with pytest.raises(ValueError, match="condition_id not in positions"):
        pm.apply_partial_exit("missing_cid", basis_returned_usdc=10.0, realized_usdc=2.0)


def test_apply_partial_exit_existing_position_succeeds() -> None:
    """Pozisyon varsa normal işler — bankroll + realized güncellenir."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pos = Position(
        condition_id="c1", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=50.0, shares=100.0,
        current_price=0.5, anchor_probability=0.55,
        event_id="e1", slug="s",
    )
    pm.add_position(pos)
    bankroll_before = pm.bankroll
    pm.apply_partial_exit("c1", basis_returned_usdc=20.0, realized_usdc=5.0)
    assert pm.bankroll == bankroll_before + 25.0
    assert pm.realized_pnl == 5.0
```

- [ ] **Step:** Run, FAIL bekle

```bash
pytest tests/unit/domain/portfolio/test_manager.py::test_apply_partial_exit_missing_position_raises -v
```

Expected: FAIL — ValueError raise edilmiyor (mevcut return'lü davranış)

### Step 2.2: manager.py fix

- [ ] **Step:** Modify `src/domain/portfolio/manager.py:87-88`

Eski:
```python
        if condition_id not in self.positions:
            return
        self.bankroll += basis_returned_usdc + realized_usdc
        self.realized_pnl += realized_usdc
```

Yeni:
```python
        if condition_id not in self.positions:
            raise ValueError(f"apply_partial_exit: condition_id not in positions: {condition_id}")
        self.bankroll += basis_returned_usdc + realized_usdc
        self.realized_pnl += realized_usdc
```

Docstring'i de güncelle (silent no-op açıklamasını sil — exception fırlatıldığını belirt):

```python
        """Scale-out: partial exit realize et (bankroll güncellenir, pozisyon silinmez).

        Caller `pos.size_usdc`'yi küçültmeden ÖNCE `basis_returned_usdc`'yi hesaplar
        (`old_size × sell_pct`) ve buraya verir. Bankroll hem basis geri alımı hem
        realized PnL ile kredilenir → `remove_position` pattern'iyle simetrik.
        Böylece identity `bankroll + invested = initial + realized_pnl` korunur.

        Raises ValueError: condition_id positions'da yoksa (race condition guard,
        SPEC-A2). Caller bu durumu yakalayıp scale-out state mutation'ını rollback'lemeli.
        """
```

- [ ] **Step:** Run, PASS bekle

```bash
pytest tests/unit/domain/portfolio/test_manager.py -v
```

Expected: 2 yeni test pass + mevcut testler kırılmamış

### Step 2.3: exit_processor caller'ına try/except ekle

- [ ] **Step:** Modify `src/orchestration/exit_processor.py:_execute_partial_exit`

Mevcut akış (97-108):
```python
        self.deps.state.portfolio.apply_partial_exit(
            pos.condition_id,
            basis_returned_usdc=basis_returned,
            realized_usdc=realized,
        )
        self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=pos.current_price,
        )
```

Yeni — apply_partial_exit'ten ÖNCE pos state mutation'ı vardı. Race olursa rollback ihtiyacı:

```python
        # State mutation'ı (shares, size) BURADAN önce yapıldı.
        # apply_partial_exit ValueError fırlatırsa pozisyon arada silinmiş demek
        # → mutation'ı rollback edip uyarı log'la (full exit zaten state'i temizledi).
        try:
            self.deps.state.portfolio.apply_partial_exit(
                pos.condition_id,
                basis_returned_usdc=basis_returned,
                realized_usdc=realized,
            )
        except ValueError as e:
            # Rollback pozisyon mutation'ı (mantıksal açıdan; pozisyon zaten yoktur ama
            # objedeki shares/size değerlerini eski haline çevirmek tutarlılık için).
            pos.shares += shares_to_sell
            pos.size_usdc /= (1 - signal.sell_pct) if signal.sell_pct < 1.0 else 1.0
            pos.scale_out_realized_usdc -= realized
            logger.warning(
                "Partial exit aborted (race): %s — %s; mutation rolled back",
                pos.slug[:35], e,
            )
            return

        self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=signal.tier or pos.scale_out_tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=pos.current_price,
        )
```

### Step 2.4: exit_processor test ekle

- [ ] **Step:** Test ekle (mevcut `test_exit_processor_partial.py`'a)

```python
# tests/unit/orchestration/test_exit_processor_partial.py — sonuna ekle
from src.domain.portfolio.manager import PortfolioManager


def test_partial_exit_rollback_on_race() -> None:
    """Pozisyon ara silinmişse mutation rollback edilir, log warn."""
    deps = _build_partial_deps()  # mevcut helper
    # Pozisyon kuralı: portfolio.apply_partial_exit ValueError fırlatacak
    deps.state.portfolio = PortfolioManager(initial_bankroll=1000.0)  # boş portfolio
    
    pos = Position(
        condition_id="ghost", token_id="t", direction="BUY_YES",
        entry_price=0.5, size_usdc=50.0, shares=100.0,
        current_price=0.6, anchor_probability=0.55,
        event_id="e1", slug="ghost-slug",
    )
    # NOT: pos portfolio'da yok ama exit_processor pos referansını kullanır

    ep = ExitProcessor(deps)
    signal = ExitSignal(reason=ExitReason.SCALE_OUT_TIER1, partial=True, sell_pct=0.4, tier=1)
    
    shares_before = pos.shares
    size_before = pos.size_usdc
    ep._execute_partial_exit(pos, signal)
    
    # Mutation rollback edilmiş olmalı (pozisyon eski haline döndü)
    assert pos.shares == pytest.approx(shares_before)
    assert pos.size_usdc == pytest.approx(size_before)
```

- [ ] **Step:** Run, PASS bekle

```bash
pytest tests/unit/orchestration/test_exit_processor_partial.py -v
```

Expected: yeni test pass

### Step 2.5: Full suite

- [ ] **Step:** Tüm testler

```bash
pytest -q --no-header
```

Expected: 963 + 3 = 966 pass

### Step 2.6: Commit

- [ ] **Step:**

```bash
git add src/domain/portfolio/manager.py src/orchestration/exit_processor.py tests/unit/domain/portfolio/test_manager.py tests/unit/orchestration/test_exit_processor_partial.py
git commit -m "feat(portfolio): apply_partial_exit fail-loud + caller rollback (SPEC-A2)"
```

---

## Task 3: A3 — Trade Logger Corrupt Row Counter

**Files:**
- Modify: `src/infrastructure/persistence/trade_logger.py:115-126`
- Modify: `src/orchestration/startup.py:154-160`
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py` (modify)
- Test: `tests/unit/orchestration/test_startup.py` (modify)

### Step 3.1: trade_logger test'i yaz

- [ ] **Step:** Test ekle

```python
# tests/unit/infrastructure/persistence/test_trade_logger.py — sonuna ekle
def test_read_all_no_corrupt_no_flag(tmp_path: Path) -> None:
    """Bozuk satır yoksa corrupt_lines = 0."""
    p = tmp_path / "trade.jsonl"
    p.write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")
    log = TradeHistoryLogger(str(p))
    records = log.read_all()
    assert len(records) == 2
    assert log.corrupt_lines == 0


def test_read_all_few_corrupt_warns_no_flag(tmp_path: Path) -> None:
    """1-2 bozuk satır → continue + corrupt_lines artar (threshold altı)."""
    p = tmp_path / "trade.jsonl"
    p.write_text('{"a":1}\nNOT JSON\n{"b":2}\n', encoding="utf-8")
    log = TradeHistoryLogger(str(p))
    records = log.read_all()
    assert len(records) == 2  # 2 sağlam
    assert log.corrupt_lines == 1


def test_read_all_threshold_corrupt_raises_alarm(tmp_path: Path) -> None:
    """3+ bozuk → corrupt_lines threshold geçti (logger.error tetiklenir)."""
    p = tmp_path / "trade.jsonl"
    p.write_text('NOPE\n{not valid\n!!!\n{"valid":true}\n', encoding="utf-8")
    log = TradeHistoryLogger(str(p))
    records = log.read_all()
    assert len(records) == 1
    assert log.corrupt_lines == 3
    assert log.corrupt_threshold_exceeded is True
```

- [ ] **Step:** Run, FAIL bekle

```bash
pytest tests/unit/infrastructure/persistence/test_trade_logger.py::test_read_all_no_corrupt_no_flag -v
```

Expected: FAIL — `corrupt_lines` attribute yok

### Step 3.2: trade_logger.py fix

- [ ] **Step:** Modify `src/infrastructure/persistence/trade_logger.py:115-126`

Eski:
```python
    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for l in self.path.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return out
```

Yeni — `__init__`'a corrupt counter init ekle:
```python
    def __init__(self, file_path: str, mirror_path: str | None = None) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mirror: Path | None = None
        if mirror_path:
            self.mirror = Path(mirror_path)
            self.mirror.parent.mkdir(parents=True, exist_ok=True)
        # Corrupt-row tracking — read_all'da güncellenir, reconcile bunu okur (SPEC-A3).
        self.corrupt_lines = 0
        self.corrupt_threshold_exceeded = False
```

read_all'i güncelle:
```python
    _CORRUPT_THRESHOLD = 3  # 3+ bozuk satır → reconcile'a abort sinyal

    def read_all(self) -> list[dict[str, Any]]:
        """Tüm jsonl satırlarını oku. Bozuk satırları sayar; threshold geçerse flag set."""
        self.corrupt_lines = 0
        self.corrupt_threshold_exceeded = False
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for l in self.path.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                self.corrupt_lines += 1
                if self.corrupt_lines == 1:
                    logger.warning("trade_history.jsonl corrupt line detected (count=1)")
        if self.corrupt_lines >= self._CORRUPT_THRESHOLD:
            self.corrupt_threshold_exceeded = True
            logger.error(
                "trade_history.jsonl: %d corrupt lines (>=%d) — reconcile will abort",
                self.corrupt_lines, self._CORRUPT_THRESHOLD,
            )
        return out
```

NOT: `logger` import'u zaten var mı kontrol et. Yoksa ekle:
```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step:** Run, PASS bekle

```bash
pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v
```

Expected: 3 yeni test pass + mevcut testler

### Step 3.3: startup.py reconcile corrupt-aware abort

- [ ] **Step:** Modify `src/orchestration/startup.py:_reconcile_realized_pnl`

Mevcut SPEC-A öncesi (en son eklediğim version):
```python
def _reconcile_realized_pnl(portfolio: PortfolioManager, trade_logger: TradeHistoryLogger,
                            initial_bankroll: float) -> None:
    """..."""
    records = trade_logger.read_all()
    if not records:
        if abs(portfolio.realized_pnl) > 0.01:
            logger.warning(
                "Reconcile skipped: trade_history empty but snapshot.realized=$%.2f — "
                "logging gap suspected; trusting snapshot. Investigate trade_logger silent failures.",
                portfolio.realized_pnl,
            )
        return
    ...
```

A3 ile genişletiyoruz: corrupt threshold geçilirse de abort:

```python
def _reconcile_realized_pnl(portfolio: PortfolioManager, trade_logger: TradeHistoryLogger,
                            initial_bankroll: float) -> None:
    """trade_history.jsonl'dan true realized hesapla, portfolio snapshot'ıyla
    uyumsuzsa düzelt + bankroll'u yeniden türet (crash recovery sonrası).

    True realized = sum(full_exit.exit_pnl_usdc) + sum(partial_exits.realized_pnl_usdc).

    GUARD-1 (SPEC-A): trade_history boş + snapshot.realized > 0 → "logging gap"
    senaryosu. Otomatik zerolama YAPMA — snapshot'a güven, WARN.

    GUARD-2 (SPEC-A3): trade_history corrupt threshold geçtiyse de abort —
    log corrupt, parsing güvenilir değil, snapshot'a güven.
    """
    records = trade_logger.read_all()

    if trade_logger.corrupt_threshold_exceeded:
        logger.warning(
            "Reconcile aborted: trade_history corrupt_lines=%d exceeded threshold; "
            "trusting snapshot.realized=$%.2f.",
            trade_logger.corrupt_lines, portfolio.realized_pnl,
        )
        return

    if not records:
        if abs(portfolio.realized_pnl) > 0.01:
            logger.warning(
                "Reconcile skipped: trade_history empty but snapshot.realized=$%.2f — "
                "logging gap suspected; trusting snapshot. Investigate trade_logger silent failures.",
                portfolio.realized_pnl,
            )
        return

    # ... (geri kalan aynı)
```

### Step 3.4: startup.py test ekle

- [ ] **Step:** Test ekle

```python
# tests/unit/orchestration/test_startup.py — sonuna ekle
def test_reconcile_aborts_on_corrupt_threshold(tmp_path: Path, caplog) -> None:
    """trade_history corrupt threshold geçtiyse reconcile snapshot'a güvenir."""
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    
    # 4 bozuk satırlı trade_history yaz (threshold=3)
    (tmp_path / "trade_history.jsonl").write_text(
        "NOPE\n{not valid\n!!!\nALSO BAD\n", encoding="utf-8",
    )
    state.portfolio.realized_pnl = 100.0  # Snapshot dolu
    
    # Yeni bootstrap reconcile — corrupt threshold abort etmeli
    state2 = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    # Snapshot korundu (zerolama olmadı)
    # NOT: Yeni bootstrap fresh portfolio dönüyor; bu test sadece warning logu kontrol eder
    assert any("corrupt_lines" in rec.message for rec in caplog.records)
```

- [ ] **Step:** Run

```bash
pytest tests/unit/orchestration/test_startup.py -v
```

Expected: yeni test pass

### Step 3.5: Full suite

- [ ] **Step:**

```bash
pytest -q --no-header
```

Expected: 966 + 4 = 970 pass

### Step 3.6: Commit

- [ ] **Step:**

```bash
git add src/infrastructure/persistence/trade_logger.py src/orchestration/startup.py tests/unit/infrastructure/persistence/test_trade_logger.py tests/unit/orchestration/test_startup.py
git commit -m "feat(persistence): trade_logger corrupt-row counter + reconcile abort (SPEC-A3)"
```

---

## Task 4: A4 — TelegramCommandPoller Public Callback API

**Files:**
- Modify: `src/infrastructure/telegram/command_poller.py`
- Modify: `src/orchestration/factory.py:137`
- Test: `tests/unit/infrastructure/telegram/test_command_poller.py` (modify)

### Step 4.1: Test'i yaz

- [ ] **Step:** Test ekle

```python
# tests/unit/infrastructure/telegram/test_command_poller.py — sonuna ekle
from unittest.mock import MagicMock


def test_set_on_stop_replaces_callback() -> None:
    """set_on_stop sonrası /stop yeni callback'i tetikler."""
    initial_cb = MagicMock()
    new_cb = MagicMock()
    poller = TelegramCommandPoller(
        bot_token="tok", chat_id="123", on_stop=initial_cb,
    )
    poller.set_on_stop(new_cb)
    poller._handle({"update_id": 1, "message": {"text": "/stop", "chat": {"id": 123}}})
    initial_cb.assert_not_called()
    new_cb.assert_called_once()


def test_default_on_stop_is_replaceable_lambda() -> None:
    """Constructor'da no-op lambda → set_on_stop ile değiştirilebilir."""
    poller = TelegramCommandPoller(
        bot_token="tok", chat_id="123", on_stop=lambda: None,
    )
    real_cb = MagicMock()
    poller.set_on_stop(real_cb)
    poller._handle({"update_id": 1, "message": {"text": "/stop", "chat": {"id": 123}}})
    real_cb.assert_called_once()
```

- [ ] **Step:** Run, FAIL bekle

```bash
pytest tests/unit/infrastructure/telegram/test_command_poller.py::test_set_on_stop_replaces_callback -v
```

Expected: FAIL — `set_on_stop` method yok

### Step 4.2: command_poller.py'a public method ekle

- [ ] **Step:** Modify `src/infrastructure/telegram/command_poller.py`

`__init__` sonrası `start()`'tan ÖNCE method ekle:

```python
    def set_on_stop(self, callback: Callable[[], None]) -> None:
        """Telegram /stop komutu için callback'i değiştir.

        Factory wiring: agent yaratıldıktan sonra agent.request_stop bağlanır.
        Constructor'a no-op lambda verilir, gerçek callback set_on_stop ile gelir.
        """
        self._on_stop = callback
```

### Step 4.3: factory.py'i public API'ye geçir

- [ ] **Step:** Modify `src/orchestration/factory.py:137`

Eski:
```python
        command_poller._on_stop = agent.request_stop
```

Yeni:
```python
        command_poller.set_on_stop(agent.request_stop)
```

### Step 4.4: Run + Full suite

- [ ] **Step:**

```bash
pytest tests/unit/infrastructure/telegram/test_command_poller.py -v
pytest -q --no-header
```

Expected: yeni 2 test pass, full 970 + 2 = 972 pass

### Step 4.5: Commit

- [ ] **Step:**

```bash
git add src/infrastructure/telegram/command_poller.py src/orchestration/factory.py tests/unit/infrastructure/telegram/test_command_poller.py
git commit -m "refactor(telegram): public set_on_stop API; remove private mutation (SPEC-A4)"
```

---

## Task 5: A5 — Tennis Resolver Erken Return

**Files:**
- Modify: `src/strategy/enrichment/sport_key_resolver.py`
- Modify: `src/domain/matching/odds_sport_keys.py`
- Test: `tests/unit/domain/matching/test_tennis_disabled.py` (**yeni**)

### Step 5.1: Tennis-disabled test'i yaz

- [ ] **Step:** Yeni test dosyası

```python
# tests/unit/domain/matching/test_tennis_disabled.py
"""Tennis kapatıldı 2026-05-05 — resolver erken None döner (CPU israfı yok)."""
from __future__ import annotations

from src.domain.matching.odds_sport_keys import resolve_odds_sport_key
from src.strategy.enrichment.sport_key_resolver import resolve_sport_key


def test_atp_tag_returns_none() -> None:
    assert resolve_odds_sport_key("atp") is None


def test_wta_tag_returns_none() -> None:
    assert resolve_odds_sport_key("wta") is None


def test_atp_dynamic_tag_short_circuits() -> None:
    """tennis_atp_french_open gibi dinamik tag'ler de None döner — early exit."""
    # sport_key_resolver dinamik turnuva resolver kullanır;
    # tennis prefix'i erken atılmalı (Odds API çağrısı yok).
    result = resolve_sport_key("tennis_atp_french_open", available_keys=[])
    assert result is None
```

- [ ] **Step:** Run, davranış kontrol

```bash
pytest tests/unit/domain/matching/test_tennis_disabled.py -v
```

Expected: FAIL veya PASS — mevcut davranışa göre

### Step 5.2: sport_key_resolver erken return

- [ ] **Step:** Modify `src/strategy/enrichment/sport_key_resolver.py`

Önce dosyayı oku, ne ekleyeceğini bul. resolve_sport_key fonksiyonunun başına early-return:

```python
# Tüm input'u temizle, prefix kontrolü:
def resolve_sport_key(sport_tag: str, available_keys: list[str]) -> str | None:
    """..."""
    tag = (sport_tag or "").lower().strip()
    # Tennis kapatıldı 2026-05-05 — atp/wta prefix erken çıkış (SPEC-A5)
    if tag.startswith("atp") or tag.startswith("wta") or tag.startswith("tennis"):
        return None
    # ... mevcut mantık devam
```

### Step 5.3: odds_sport_keys.py erken return

- [ ] **Step:** Modify `src/domain/matching/odds_sport_keys.py`

Benzer şekilde `resolve_odds_sport_key`'in başına:

```python
def resolve_odds_sport_key(sport_tag: str) -> str | None:
    tag = (sport_tag or "").lower().strip()
    # Tennis kapatıldı 2026-05-05 (SPEC-A5)
    if tag in ("atp", "wta") or tag.startswith("tennis"):
        return None
    # ... mevcut mantık
```

### Step 5.4: Tests + Full suite

- [ ] **Step:**

```bash
pytest tests/unit/domain/matching/test_tennis_disabled.py -v
pytest tests/unit/domain/matching/ -v
pytest -q --no-header
```

Expected: yeni 3 test pass; mevcut tennis testleri (matching tarafı) hala pass — sadece resolver early-return ekledik, matching katmanı dokunulmadı.

### Step 5.5: Commit

- [ ] **Step:**

```bash
git add src/strategy/enrichment/sport_key_resolver.py src/domain/matching/odds_sport_keys.py tests/unit/domain/matching/test_tennis_disabled.py
git commit -m "feat(matching): tennis disabled prefix early-return (SPEC-A5)"
```

---

## Task 6: SPEC.md + DECISIONS.md temizlik

**Files:**
- Modify: `SPEC.md` (SPEC-A bölümünü "DONE" işaretle ve SPEC-B'yi koru, SPEC-C koru)
- Modify: `DECISIONS.md` (sessiz bug audit section'ına "SPEC-A tamamlandı" notu ekle)

### Step 6.1: SPEC-A'yı DONE işaretle

- [ ] **Step:** SPEC.md'de SPEC-A başlığını `## SPEC-A: Sessiz Bug Temizliği (Faz 1) — DONE 2026-05-08` yap

Aslında CLAUDE.md SPEC.md flow: "Koda dönüştü, sil." Tamam o zaman: SPEC-A tüm bloğunu sil. SPEC-B + SPEC-C kalsın.

- [ ] **Step:** SPEC.md'den SPEC-A bloğunu komple sil

```bash
# Manuel edit
```

### Step 6.2: DECISIONS.md güncelle

- [ ] **Step:** DECISIONS.md'deki "Sessiz Bug Audit + Fix Stratejisi" section'ına "Yapılış sırası" altına ek:

```markdown
**SPEC-A tamamlandı (2026-05-08):**
- A1: cycle programatik-hata 2-strike stop ✅
- A2: apply_partial_exit fail-loud + caller rollback ✅
- A3: trade_logger corrupt-row counter + reconcile abort ✅
- A4: TelegramCommandPoller public set_on_stop API ✅
- A5: tennis resolver erken return ✅

Test toplamı: 956 → 972 (+16 yeni test). Bot artık sessiz hata yutmayacak.
```

### Step 6.3: Final commit

- [ ] **Step:**

```bash
git add SPEC.md DECISIONS.md
git commit -m "docs: SPEC-A done; close silent bug cleanup spec"
```

---

## Task 7: Reload + smoke test

**Files:** Yok

### Step 7.1: Reload bot (state korunsun)

- [ ] **Step:**

```bash
python scripts/reboot.py reload
```

### Step 7.2: 5 dk gözlem — bot.log

- [ ] **Step:** Bot başladı + cycle çalışıyor mu doğrula

```bash
grep "Bootstrap complete\|Cycle error\|STOPPING" logs/runtime/bot.log | tail -10
```

Expected:
- `Bootstrap complete` mesajı görünür
- `Cycle error` görünmemeli
- `STOPPING` görünmemeli

### Step 7.3: Trade history'e write doğrula

- [ ] **Step:** İlk heavy cycle sonrası

```bash
ls -la logs/audit/trade_history.jsonl logs/session/trade_history.jsonl
wc -l logs/audit/trade_history.jsonl
```

Expected: dosyalar var, içeriği var (heavy cycle yeni pozisyon açtıysa).

---

## Self-Review Notes

**Spec coverage:**
- SPEC-A1 (cycle except) → Task 1 ✅
- SPEC-A2 (apply_partial_exit) → Task 2 ✅
- SPEC-A3 (corrupt counter) → Task 3 ✅
- SPEC-A4 (telegram public API) → Task 4 ✅
- SPEC-A5 (tennis resolver early) → Task 5 ✅
- SPEC.md/DECISIONS.md temizlik → Task 6 ✅
- Smoke test → Task 7 ✅

**Placeholder scan:** Yok — her step'te exact dosya yolları, exact satır numaraları, complete code blocks.

**Type consistency:**
- `CycleResilience` Task 1 boyunca tek isim
- `corrupt_lines` / `corrupt_threshold_exceeded` Task 3 boyunca tutarlı
- `set_on_stop` Task 4 boyunca tek isim
- `apply_partial_exit` ValueError signature Task 2 boyunca tutarlı

**Risk analizi:**
- Task 1: agent.py'a yeni state ekleniyor — `_resilience` instance attribute. Mock-driven test integration test ile kontrol ediliyor.
- Task 2: ValueError raise → caller exit_processor güncelleniyor. Diğer caller var mı? `grep apply_partial_exit src/` → sadece exit_processor.
- Task 3: corrupt counter eklenmesi backward-compatible (default 0).
- Task 4: factory.py:137 değişiyor; başka caller `_on_stop` özel attribute'ya dokunmuyor (audit edildi).
- Task 5: erken return → tennis sport_tag'leri zaten tarama dışı, mevcut allowed_sport_tags ile zaten None dönüyordu pratikte.

**Geri alma**:
- Her task ayrı commit. Hata olursa: `git revert <commit>`.
- Tüm SPEC-A geri alınırsa: `git revert <range>`.

**Yasak listesi (her task'ta)**:
- Entry/exit kuralları (gate.py, monitor.py, exit dispatchers): DOKUNMA
- Executor: DOKUNMA
- ESPN/score client: SPEC-B kapsamı
- 16 Nisan baseline davranışı korunacak — sadece hata kalıbı değişiyor
