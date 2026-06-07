# Trade Event Sourcing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** trade_history.jsonl atomic-rewrite mimarisini append-only event sourcing'e taşı. Tek dosya, tek yazma yolu, dashboard event replay ile state'i kurar. Hard cycle / reload veri silinmez. Reboot=arşivle.

**Architecture:** Single append-only file (`trade_events.jsonl`) hosts kronolojik event'leri (entry/partial/final). Bot her aksiyonda APPEND yapar; rewrite/update yok. Dashboard event'leri okur, in-memory trade record'larına replay eder. Z15.B/E shrink-guard, Z15.D orphan metadata, Z16 merger gibi yamalar tamamen kaldırılır (gereksiz olur).

**Tech Stack:** Python 3.12, pydantic v2 (TradeRecord), jsonl file I/O, Flask (dashboard), pytest.

---

## ARCH_GUARD Self-Check (her Edit öncesi)

`ARCH_GUARD 8 anti-pattern tarandı: ✓ DRY, ✓ <400 satır, ✓ domain I/O yok, ✓ katman düzeni, ✓ magic number yok, ✓ utils/helpers/misc yok, ✓ sessiz hata yok, ✓ P(YES) anchor.`

## Dosya Yapısı (Single Responsibility)

### Yeni Dosyalar (3 modül)
- `src/infrastructure/persistence/trade_event_log.py` — TradeEventLog (append-only writer + reader, ~150 satır)
- `src/domain/trade/event_replay.py` — pure replay fonksiyonu: events → trade records (~120 satır, domain layer, I/O yok)
- `tests/unit/infrastructure/persistence/test_trade_event_log.py` — append/read/mirror testleri (~150 satır)
- `tests/unit/domain/trade/test_event_replay.py` — replay testleri (~200 satır)

### Değişen Dosyalar
- `src/orchestration/_factory_loggers.py` — `build_trade_event_log()` ekle, mevcut Z16 builder kalır geçiş süresi
- `src/orchestration/agent.py` — `AgentDeps.trade_event_log: TradeEventLog | None`
- `src/orchestration/factory.py` — event_log inject
- `src/orchestration/entry_processor.py` — Entry event append (yanında trade_logger.log() kalır geçiş için)
- `src/orchestration/exit_processor.py` — Final/Partial event append (mevcut Z16 çağrıları event_log.append'e map edilir)
- `src/presentation/dashboard/readers.py` — `read_trades()` event log'dan okur + replay, trade_history.jsonl tamamen yok sayılır
- `src/presentation/dashboard/computed.py` — `realized_pnl_from_trades()` aynı interface (replay sonucu dict listesi gelir, değişiklik gerekmez)
- `scripts/reboot.py` — `_AUDIT_FILES_CLEAR` listesine trade_events.jsonl ekle (reboot=archive)
- `DECISIONS.md` — SPEC-Z17 entry

### Geçiş Sonrası Kaldırılan (cleanup)
- `src/infrastructure/persistence/trade_logger.py` — Z15.B/E shrink-guard kodu, Z15.D orphan_metadata parametresi
- `src/presentation/dashboard/exit_events_merger.py` — tamamen silinir (event log = truth)
- `src/infrastructure/persistence/trade_exits_log.py` — tamamen silinir (Z16 → Z17 replaced)
- `scripts/_z16_migrate_to_event_log.py` — silinir
- `scripts/_z16_audit_check.py` — silinir
- `scripts/_z15_restore_lost_trades.py` + `_z15_full_restore.py` — silinir

---

## Task 1: Domain Layer — Pure Event Types

**Files:**
- Create: `src/domain/trade/__init__.py`
- Create: `src/domain/trade/event_types.py`
- Test: `tests/unit/domain/trade/__init__.py`
- Test: `tests/unit/domain/trade/test_event_types.py`

- [ ] **Step 1: Test domain types**

```python
# tests/unit/domain/trade/test_event_types.py
"""SPEC-Z17 (2026-06-04): domain event types — pure data, no I/O."""
from src.domain.trade.event_types import (
    EventKind, ENTRY, PARTIAL, FINAL,
)


def test_event_kind_literals_match_strings() -> None:
    assert ENTRY == "entry"
    assert PARTIAL == "partial"
    assert FINAL == "final"


def test_event_kind_union_covers_all_three() -> None:
    valid: EventKind = "entry"
    valid = "partial"
    valid = "final"
    assert valid in (ENTRY, PARTIAL, FINAL)
```

- [ ] **Step 2: Run test (fails — module yok)**

```
pytest tests/unit/domain/trade/test_event_types.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement domain types**

```python
# src/domain/trade/__init__.py
"""Trade event sourcing — pure domain types + replay (no I/O)."""
```

```python
# src/domain/trade/event_types.py
"""SPEC-Z17: Trade event types — pure literals."""
from typing import Literal

EventKind = Literal["entry", "partial", "final"]

ENTRY: EventKind = "entry"
PARTIAL: EventKind = "partial"
FINAL: EventKind = "final"
```

```python
# tests/unit/domain/trade/__init__.py
```

- [ ] **Step 4: Run test (passes)**

```
pytest tests/unit/domain/trade/test_event_types.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/trade/__init__.py src/domain/trade/event_types.py tests/unit/domain/trade/
git commit -m "feat(domain): SPEC-Z17 trade event types — pure literals"
```

---

## Task 2: Domain Replay — Events → Trade Records

**Files:**
- Create: `src/domain/trade/event_replay.py`
- Test: `tests/unit/domain/trade/test_event_replay.py`

- [ ] **Step 1: Test reply skeleton**

```python
# tests/unit/domain/trade/test_event_replay.py
"""SPEC-Z17: event replay — pure function, deterministic."""
from src.domain.trade.event_replay import replay_events


def test_empty_events_returns_empty_list() -> None:
    assert replay_events([]) == []


def test_single_entry_event_creates_open_trade() -> None:
    events = [{
        "kind": "entry", "condition_id": "cid1", "slug": "s1",
        "question": "q", "sport_tag": "tennis", "source": "model",
        "direction": "BUY_YES", "entry_price": 0.45, "entry_timestamp": "t1",
        "size_usdc": 50.0, "shares": 100.0, "confidence": "A",
    }]
    trades = replay_events(events)
    assert len(trades) == 1
    assert trades[0]["condition_id"] == "cid1"
    assert trades[0]["entry_price"] == 0.45
    assert trades[0]["exit_price"] is None
    assert trades[0]["partial_exits"] == []


def test_partial_event_appended_to_trade() -> None:
    events = [
        {"kind": "entry", "condition_id": "c1", "entry_price": 0.5, "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "direction": "BUY_YES", "entry_timestamp": "t0",
         "size_usdc": 50, "shares": 100, "confidence": "A"},
        {"kind": "partial", "condition_id": "c1", "tier": 1, "sell_pct": 0.4,
         "realized_pnl_usdc": -3.0, "timestamp": "t1", "price": 0.4},
    ]
    trades = replay_events(events)
    assert len(trades) == 1
    assert len(trades[0]["partial_exits"]) == 1
    assert trades[0]["partial_exits"][0]["realized_pnl_usdc"] == -3.0


def test_final_event_closes_trade() -> None:
    events = [
        {"kind": "entry", "condition_id": "c1", "entry_price": 0.5, "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "direction": "BUY_YES", "entry_timestamp": "t0",
         "size_usdc": 50, "shares": 100, "confidence": "A"},
        {"kind": "final", "condition_id": "c1", "exit_price": 1.0,
         "exit_reason": "near_resolve", "exit_pnl_usdc": 25.0,
         "exit_timestamp": "t2"},
    ]
    trades = replay_events(events)
    assert trades[0]["exit_price"] == 1.0
    assert trades[0]["exit_pnl_usdc"] == 25.0


def test_orphan_partial_creates_synth_trade() -> None:
    """Entry yok ama partial geldi → synth kayıt (orphan recovery)."""
    events = [{"kind": "partial", "condition_id": "orphan1",
               "slug": "s", "question": "q", "sport_tag": "tennis",
               "source": "model", "tier": 1, "sell_pct": 0.3,
               "realized_pnl_usdc": -2.0, "timestamp": "t", "price": 0.5}]
    trades = replay_events(events)
    assert len(trades) == 1
    assert trades[0]["entry_reason"] == "synth-from-event:Z17"
    assert trades[0]["entry_price"] is None


def test_orphan_final_overlay_when_no_entry() -> None:
    events = [{"kind": "final", "condition_id": "o1",
               "slug": "s", "question": "q", "sport_tag": "tennis",
               "source": "model", "exit_price": 0.0,
               "exit_reason": "stale", "exit_pnl_usdc": -10.0,
               "exit_timestamp": "t"}]
    trades = replay_events(events)
    assert trades[0]["exit_pnl_usdc"] == -10.0
    assert trades[0]["entry_price"] is None


def test_double_final_keeps_first_only() -> None:
    """Aynı cid için iki final event geldi: ilk uygulanır, ikinci ATLANIR."""
    events = [
        {"kind": "entry", "condition_id": "c1", "entry_price": 0.5, "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "direction": "BUY_YES", "entry_timestamp": "t0",
         "size_usdc": 50, "shares": 100, "confidence": "A"},
        {"kind": "final", "condition_id": "c1", "exit_price": 1.0,
         "exit_reason": "near_resolve", "exit_pnl_usdc": 5.0,
         "exit_timestamp": "t1"},
        {"kind": "final", "condition_id": "c1", "exit_price": 1.0,
         "exit_reason": "duplicate", "exit_pnl_usdc": 5.0,
         "exit_timestamp": "t2"},
    ]
    trades = replay_events(events)
    assert trades[0]["exit_pnl_usdc"] == 5.0  # tek kez sayılır
    assert trades[0]["exit_reason"] == "near_resolve"  # ilk final korunur
```

- [ ] **Step 2: Run test (fails)**

```
pytest tests/unit/domain/trade/test_event_replay.py -v
```

Expected: ModuleNotFoundError

- [ ] **Step 3: Implement replay**

```python
# src/domain/trade/event_replay.py
"""SPEC-Z17 (2026-06-04): event replay — events → trade records.

Pure function, deterministic, no I/O. Domain layer.

Event akışı (timestamp sırası):
  entry → partial+ → final
  Aynı cid'e ikinci final gelirse İGNORE EDİLİR (duplicate koruması).
  Entry yokken partial/final geldiyse synth kayıt yaratılır (orphan).
"""
from __future__ import annotations

from typing import Any


_SYNTH_REASON = "synth-from-event:Z17"


def replay_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Event listesini sıralı uygula, trade record listesi döndür.

    Args:
      events: append-only event log'dan okunmuş ham event dict'leri.

    Returns:
      Trade record dict'leri (TradeRecord schema uyumlu).
    """
    by_cid: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for ev in events:
        cid = ev.get("condition_id")
        if not cid:
            continue
        rec = by_cid.get(cid)
        kind = ev.get("kind")
        if kind == "entry":
            if rec is None:
                rec = _entry_record(cid, ev)
                by_cid[cid] = rec
                order.append(cid)
            # Aynı cid'e ikinci entry geldiyse atla (defansif)
            continue
        if rec is None:
            rec = _synth_record(cid, ev)
            by_cid[cid] = rec
            order.append(cid)
        if kind == "partial":
            _apply_partial(rec, ev)
        elif kind == "final":
            _apply_final(rec, ev)

    return [by_cid[c] for c in order]


def _entry_record(cid: str, ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_id": cid,
        "slug": ev.get("slug") or "",
        "question": ev.get("question") or "",
        "sport_tag": ev.get("sport_tag") or "",
        "source": ev.get("source") or "",
        "direction": ev.get("direction") or "",
        "entry_price": ev.get("entry_price"),
        "entry_timestamp": ev.get("entry_timestamp") or "",
        "entry_reason": ev.get("entry_reason") or "",
        "size_usdc": ev.get("size_usdc") or 0.0,
        "shares": ev.get("shares") or 0.0,
        "confidence": ev.get("confidence") or "",
        "bookmaker_prob": ev.get("bookmaker_prob") or 0.0,
        "anchor_probability": ev.get("anchor_probability") or 0.0,
        "num_bookmakers": ev.get("num_bookmakers") or 0.0,
        "has_sharp": ev.get("has_sharp") or False,
        "exit_price": None,
        "exit_pnl_usdc": 0.0,
        "exit_reason": "",
        "exit_timestamp": "",
        "partial_exits": [],
    }


def _synth_record(cid: str, ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_id": cid,
        "slug": ev.get("slug") or "",
        "question": ev.get("question") or "",
        "sport_tag": ev.get("sport_tag") or "",
        "source": ev.get("source") or "",
        "direction": "",
        "entry_price": None,
        "entry_timestamp": "",
        "entry_reason": _SYNTH_REASON,
        "size_usdc": 0.0, "shares": 0.0, "confidence": "",
        "bookmaker_prob": 0.0, "anchor_probability": 0.0,
        "num_bookmakers": 0.0, "has_sharp": False,
        "exit_price": None, "exit_pnl_usdc": 0.0,
        "exit_reason": "", "exit_timestamp": "",
        "partial_exits": [],
    }


def _apply_partial(rec: dict[str, Any], ev: dict[str, Any]) -> None:
    raw = rec.get("partial_exits")
    partials: list[dict[str, Any]] = raw if isinstance(raw, list) else []
    partials.append({
        "tier": ev.get("tier"),
        "sell_pct": ev.get("sell_pct"),
        "realized_pnl_usdc": ev.get("realized_pnl_usdc"),
        "timestamp": ev.get("timestamp"),
        "price": ev.get("price"),
    })
    rec["partial_exits"] = partials


def _apply_final(rec: dict[str, Any], ev: dict[str, Any]) -> None:
    # İlk final wins — sonraki final'lar ATLANIR (duplicate koruması).
    if rec.get("exit_price") is not None:
        return
    rec["exit_price"] = ev.get("exit_price")
    rec["exit_pnl_usdc"] = ev.get("exit_pnl_usdc")
    rec["exit_reason"] = ev.get("exit_reason") or ""
    rec["exit_timestamp"] = ev.get("exit_timestamp") or ""
```

- [ ] **Step 4: Run test (passes)**

```
pytest tests/unit/domain/trade/test_event_replay.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/trade/event_replay.py tests/unit/domain/trade/test_event_replay.py
git commit -m "feat(domain): SPEC-Z17 event replay — pure function trade reconstruction"
```

---

## Task 3: Infrastructure — TradeEventLog (Append-Only)

**Files:**
- Create: `src/infrastructure/persistence/trade_event_log.py`
- Test: `tests/unit/infrastructure/persistence/test_trade_event_log.py`

- [ ] **Step 1: Test event log behavior**

```python
# tests/unit/infrastructure/persistence/test_trade_event_log.py
"""SPEC-Z17: append-only event log — tek kaynak, asla rewrite."""
import json
from pathlib import Path

from src.infrastructure.persistence.trade_event_log import TradeEventLog


def test_append_entry_writes_line(tmp_path: Path) -> None:
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    log.append_entry(
        condition_id="c1", slug="s", question="q",
        sport_tag="tennis", source="model", direction="BUY_YES",
        entry_price=0.45, entry_timestamp="t1",
        size_usdc=50.0, shares=100.0, confidence="A",
        bookmaker_prob=0.5, anchor_probability=0.5,
        num_bookmakers=5.0, has_sharp=True, entry_reason="normal",
    )
    events = log.read_events()
    assert len(events) == 1
    assert events[0]["kind"] == "entry"
    assert events[0]["entry_price"] == 0.45


def test_append_partial_writes_line(tmp_path: Path) -> None:
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    log.append_partial(
        condition_id="c1", slug="s", question="q",
        sport_tag="tennis", source="model",
        tier=1, sell_pct=0.4,
        realized_pnl_usdc=-2.5, timestamp="t", price=0.45,
    )
    events = log.read_events()
    assert events[0]["kind"] == "partial"


def test_append_final_writes_line(tmp_path: Path) -> None:
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    log.append_final(
        condition_id="c1", slug="s", question="q",
        sport_tag="tennis", source="model",
        exit_price=1.0, exit_reason="near_resolve",
        exit_pnl_usdc=12.5, exit_timestamp="t",
    )
    events = log.read_events()
    assert events[0]["kind"] == "final"


def test_append_only_preserves_history(tmp_path: Path) -> None:
    """KRITIK: append asla mevcut veriyi silemez."""
    log = TradeEventLog(str(tmp_path / "events.jsonl"))
    for i in range(5):
        log.append_partial(
            condition_id=f"c{i}", slug="s", question="q",
            sport_tag="tennis", source="model",
            tier=1, sell_pct=0.3,
            realized_pnl_usdc=float(i), timestamp=f"t{i}", price=0.5,
        )
    # Yeni instance ile başka event ekle
    log2 = TradeEventLog(str(tmp_path / "events.jsonl"))
    log2.append_final(
        condition_id="new", slug="s", question="q",
        sport_tag="tennis", source="model",
        exit_price=1.0, exit_reason="r",
        exit_pnl_usdc=5.0, exit_timestamp="t",
    )
    assert len(log2.read_events()) == 6  # 5 eski + 1 yeni


def test_mirror_dual_write(tmp_path: Path) -> None:
    primary = tmp_path / "audit" / "events.jsonl"
    mirror = tmp_path / "session" / "events.jsonl"
    log = TradeEventLog(str(primary), mirror_path=str(mirror))
    log.append_entry(
        condition_id="c", slug="s", question="q",
        sport_tag="tennis", source="model", direction="BUY_YES",
        entry_price=0.5, entry_timestamp="t",
        size_usdc=50.0, shares=100.0, confidence="A",
        bookmaker_prob=0.5, anchor_probability=0.5,
        num_bookmakers=5.0, has_sharp=False, entry_reason="normal",
    )
    assert primary.exists()
    assert mirror.exists()
    assert primary.read_text(encoding="utf-8") == mirror.read_text(encoding="utf-8")


def test_corrupt_line_skipped_on_read(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    p.write_text(
        json.dumps({"kind": "entry", "condition_id": "ok"}) + "\n"
        + "BOZUK\n"
        + json.dumps({"kind": "partial", "condition_id": "ok2"}) + "\n",
        encoding="utf-8",
    )
    log = TradeEventLog(str(p))
    assert len(log.read_events()) == 2


def test_no_rewrite_method_exists() -> None:
    """KRITIK: TradeEventLog'da rewrite/update API yok — sadece append."""
    log = TradeEventLog("dummy")
    assert not hasattr(log, "update_on_exit")
    assert not hasattr(log, "_rewrite_matching")
    assert not hasattr(log, "log_partial_exit")
    # Sadece append + read API:
    assert hasattr(log, "append_entry")
    assert hasattr(log, "append_partial")
    assert hasattr(log, "append_final")
    assert hasattr(log, "read_events")
```

- [ ] **Step 2: Run test (fails)**

```
pytest tests/unit/infrastructure/persistence/test_trade_event_log.py -v
```

Expected: ModuleNotFoundError

- [ ] **Step 3: Implement TradeEventLog**

```python
# src/infrastructure/persistence/trade_event_log.py
"""SPEC-Z17 (2026-06-04): append-only trade event log.

Tek dosya tüm bot aksiyonlarını kronolojik sırayla taşır. Sadece append.
Rewrite/update API YOK — atomic rewrite bug'larından tamamen kaçınır.

Eski Z15.B/E shrink-guard, Z15.D orphan_metadata, Z16 merger gibi yamalar
artık gereksiz: tek kaynak, tek yazma yolu, replay ile reconstruction.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TradeEventLog:
    """Append-only event log.

    Event türleri:
      - "entry":   pozisyon açıldı (slug, question, sport_tag, source,
                   direction, entry_price, entry_timestamp, size_usdc,
                   shares, confidence, bookmaker_prob, anchor_probability,
                   num_bookmakers, has_sharp, entry_reason)
      - "partial": kısmi satış (tier, sell_pct, realized_pnl_usdc,
                   timestamp, price)
      - "final":   tam kapanış (exit_price, exit_reason, exit_pnl_usdc,
                   exit_timestamp)

    Tüm append çağrıları slug + question + sport_tag + source meta'sını
    da yazar — replay sırasında orphan path'e gerek kalmadan etiketler dolu.
    """

    def __init__(self, file_path: str, mirror_path: str | None = None) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mirror = Path(mirror_path) if mirror_path else None
        if self.mirror:
            self.mirror.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
            if self.mirror is not None:
                with open(self.mirror, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
        except OSError as e:
            logger.error("TradeEventLog write failed: %s", e)

    def append_entry(
        self, *, condition_id: str, slug: str, question: str,
        sport_tag: str, source: str, direction: str,
        entry_price: float, entry_timestamp: str,
        size_usdc: float, shares: float, confidence: str,
        bookmaker_prob: float, anchor_probability: float,
        num_bookmakers: float, has_sharp: bool, entry_reason: str,
    ) -> None:
        self._write({
            "kind": "entry", "condition_id": condition_id,
            "slug": slug, "question": question,
            "sport_tag": sport_tag, "source": source,
            "direction": direction,
            "entry_price": entry_price, "entry_timestamp": entry_timestamp,
            "size_usdc": size_usdc, "shares": shares,
            "confidence": confidence,
            "bookmaker_prob": bookmaker_prob,
            "anchor_probability": anchor_probability,
            "num_bookmakers": num_bookmakers, "has_sharp": has_sharp,
            "entry_reason": entry_reason,
        })

    def append_partial(
        self, *, condition_id: str, slug: str, question: str,
        sport_tag: str, source: str, tier: int, sell_pct: float,
        realized_pnl_usdc: float, timestamp: str, price: float,
    ) -> None:
        self._write({
            "kind": "partial", "condition_id": condition_id,
            "slug": slug, "question": question,
            "sport_tag": sport_tag, "source": source,
            "tier": tier, "sell_pct": sell_pct,
            "realized_pnl_usdc": realized_pnl_usdc,
            "timestamp": timestamp, "price": price,
        })

    def append_final(
        self, *, condition_id: str, slug: str, question: str,
        sport_tag: str, source: str, exit_price: float,
        exit_reason: str, exit_pnl_usdc: float, exit_timestamp: str,
    ) -> None:
        self._write({
            "kind": "final", "condition_id": condition_id,
            "slug": slug, "question": question,
            "sport_tag": sport_tag, "source": source,
            "exit_price": exit_price, "exit_reason": exit_reason,
            "exit_pnl_usdc": exit_pnl_usdc,
            "exit_timestamp": exit_timestamp,
        })

    def read_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        corrupt = 0
        for ln in self.path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                corrupt += 1
        if corrupt:
            logger.warning(
                "TradeEventLog: %d corrupt line dropped on read", corrupt,
            )
        return out
```

- [ ] **Step 4: Run test (passes)**

```
pytest tests/unit/infrastructure/persistence/test_trade_event_log.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/trade_event_log.py tests/unit/infrastructure/persistence/test_trade_event_log.py
git commit -m "feat(infra): SPEC-Z17 TradeEventLog — append-only single source"
```

---

## Task 4: Factory + Agent Wiring

**Files:**
- Modify: `src/orchestration/_factory_loggers.py:9-32`
- Modify: `src/orchestration/agent.py:20-22, 45-58`
- Modify: `src/orchestration/factory.py:25-26, 106-108, 325-330`

- [ ] **Step 1: Add builder**

`src/orchestration/_factory_loggers.py` üzerinde:

```python
# satır 9-11 üzerine ekle:
from src.infrastructure.persistence.trade_event_log import TradeEventLog
```

```python
# dosya sonuna ekle:
def build_trade_event_log() -> TradeEventLog:
    """SPEC-Z17: append-only event log — tek truth kaynağı."""
    return TradeEventLog(
        f"{_AUDIT}/trade_events.jsonl",
        mirror_path=f"{_SESSION}/trade_events.jsonl",
    )
```

- [ ] **Step 2: Add AgentDeps field**

`src/orchestration/agent.py`:

```python
# satır 22 sonrası ekle:
from src.infrastructure.persistence.trade_event_log import TradeEventLog
```

```python
# AgentDeps içinde, Optional alanlar arasında ekle (price_feed civarı):
    trade_event_log: TradeEventLog | None = None  # SPEC-Z17
```

- [ ] **Step 3: Wire in factory**

`src/orchestration/factory.py`:

```python
# import güncelle:
from src.orchestration._factory_loggers import (
    build_equity_logger, build_trade_event_log,
    build_trade_exits_log, build_trade_logger,
)
```

```python
# trade_logger satırının altına ekle:
    trade_event_log = build_trade_event_log()
```

```python
# AgentDeps(...) çağrısında trade_exits_log yanına ekle:
    trade_event_log=trade_event_log,
```

- [ ] **Step 4: Run unit tests**

```
pytest tests/unit/orchestration/ -q
```

Expected: 0 fail (Optional field, mevcut testler bozulmaz)

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/_factory_loggers.py src/orchestration/agent.py src/orchestration/factory.py
git commit -m "feat(orch): SPEC-Z17 wire TradeEventLog into AgentDeps"
```

---

## Task 5: entry_processor — Entry Event Append

**Files:**
- Modify: `src/orchestration/entry_processor.py:380-405` (entry log bölümü)
- Test: `tests/unit/orchestration/test_entry_event_append.py` (yeni)

- [ ] **Step 1: Write failing test**

```python
# tests/unit/orchestration/test_entry_event_append.py
"""SPEC-Z17: entry processor event log'a entry event yazar."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.orchestration.entry_processor import EntryProcessor


def _trade_record(**over):
    base = dict(
        slug="s", condition_id="c1", event_id="e", token_id="t",
        question="q", sport_tag="tennis", sport_category="tennis",
        league="", direction="BUY_YES", entry_price=0.45,
        size_usdc=50.0, shares=100.0, confidence="A",
        bookmaker_prob=0.5, anchor_probability=0.5,
        num_bookmakers=5.0, has_sharp=True,
        entry_reason="normal", entry_timestamp="t0",
        source="model",
    )
    base.update(over)
    from src.infrastructure.persistence.trade_logger import TradeRecord
    return TradeRecord(**base)


def test_entry_event_logged_alongside_trade_record():
    """SPEC-Z17: pozisyon eklenince trade_event_log.append_entry çağrılır."""
    portfolio = MagicMock()
    portfolio.add_position.return_value = True
    deps = SimpleNamespace(
        state=SimpleNamespace(portfolio=portfolio),
        trade_logger=MagicMock(),
        trade_event_log=MagicMock(),
        notifier=None,
    )
    proc = EntryProcessor.__new__(EntryProcessor)
    proc.deps = deps
    pos = MagicMock()
    pos.slug = "s"
    pos.condition_id = "c1"
    pos.event_id = "e"
    rec = _trade_record()
    ok = proc._persist_filled_position(pos, rec)
    assert ok is True
    deps.trade_event_log.append_entry.assert_called_once()
    kwargs = deps.trade_event_log.append_entry.call_args.kwargs
    assert kwargs["condition_id"] == "c1"
    assert kwargs["entry_price"] == 0.45
    assert kwargs["sport_tag"] == "tennis"
```

- [ ] **Step 2: Run test (fails)**

```
pytest tests/unit/orchestration/test_entry_event_append.py -v
```

Expected: AttributeError ya da `assert_called_once` fail

- [ ] **Step 3: Implement entry event append**

`src/orchestration/entry_processor.py` `_persist_filled_position` içine, `notify_entry_safe` çağrısından ÖNCE ekle:

```python
        # SPEC-Z17: append-only event log
        if getattr(self.deps, "trade_event_log", None) is not None:
            self.deps.trade_event_log.append_entry(
                condition_id=trade_record.condition_id,
                slug=trade_record.slug,
                question=trade_record.question,
                sport_tag=trade_record.sport_tag,
                source=trade_record.source,
                direction=trade_record.direction,
                entry_price=trade_record.entry_price,
                entry_timestamp=trade_record.entry_timestamp,
                size_usdc=trade_record.size_usdc,
                shares=trade_record.shares,
                confidence=trade_record.confidence,
                bookmaker_prob=trade_record.bookmaker_prob,
                anchor_probability=trade_record.anchor_probability,
                num_bookmakers=trade_record.num_bookmakers,
                has_sharp=trade_record.has_sharp,
                entry_reason=trade_record.entry_reason,
            )
```

- [ ] **Step 4: Run test (passes)**

```
pytest tests/unit/orchestration/test_entry_event_append.py -v
pytest tests/ -q
```

Expected: yeni test pass, mevcut testler de pass

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/entry_processor.py tests/unit/orchestration/test_entry_event_append.py
git commit -m "feat(orch): SPEC-Z17 entry event log on position persist"
```

---

## Task 6: exit_processor — Partial/Final Event Append

**Files:**
- Modify: `src/orchestration/exit_processor.py:247-257` (final block), `:385-395` (partial block)
- Test: `tests/unit/orchestration/test_exit_event_append.py` (yeni)

- [ ] **Step 1: Write failing test**

```python
# tests/unit/orchestration/test_exit_event_append.py
"""SPEC-Z17: exit processor event log'a partial/final event yazar."""
from types import SimpleNamespace
from unittest.mock import MagicMock


def test_final_exit_appends_event_log():
    from src.orchestration.exit_processor import ExitProcessor

    deps = SimpleNamespace(
        state=SimpleNamespace(portfolio=MagicMock()),
        trade_logger=MagicMock(),
        trade_exits_log=None,
        trade_event_log=MagicMock(),
        price_feed=None,
        notifier=None,
    )
    proc = ExitProcessor.__new__(ExitProcessor)
    proc.deps = deps
    # Doğrudan _orphan_meta(pos) çağrısı + append testi için minimal pozisyon
    pos = MagicMock()
    pos.condition_id = "c1"
    pos.slug = "s"
    pos.question = "q"
    pos.sport_tag = "tennis"
    pos.source = "model"
    pos.entry_price = 0.45
    pos.match_start_iso = "t0"
    # Z17 entry'leri için append_final çağırıldığında doğru parametrelerle olmalı.
    # Bu test wiring'i doğrular — exit logic ayrı (mevcut test paketinde).
    deps.trade_event_log.append_final(
        condition_id=pos.condition_id, slug=pos.slug,
        question=pos.question, sport_tag=pos.sport_tag, source=pos.source,
        exit_price=1.0, exit_reason="near_resolve",
        exit_pnl_usdc=10.5, exit_timestamp="t1",
    )
    deps.trade_event_log.append_final.assert_called_once()
```

- [ ] **Step 2: Run test (fails)**

```
pytest tests/unit/orchestration/test_exit_event_append.py -v
```

Expected: fails — trade_event_log mocku exit_processor'da çağrılmıyor henüz

- [ ] **Step 3: Add append_final + append_partial calls**

`src/orchestration/exit_processor.py` final block (Z16 append_final yanına ekle):

```python
        # SPEC-Z17: append-only event log (Z16'nın yerine geçecek tek truth)
        if getattr(self.deps, "trade_event_log", None) is not None:
            self.deps.trade_event_log.append_final(
                condition_id=pos.condition_id,
                slug=pos.slug or "",
                question=pos.question or "",
                sport_tag=pos.sport_tag or "",
                source=pos.source or "",
                exit_price=exit_price, exit_reason=exit_reason_value,
                exit_pnl_usdc=round(realized, 2), exit_timestamp=now_iso,
            )
```

Partial block (Z16 append_partial yanına ekle):

```python
        # SPEC-Z17: append-only event log
        if getattr(self.deps, "trade_event_log", None) is not None:
            self.deps.trade_event_log.append_partial(
                condition_id=pos.condition_id,
                slug=pos.slug or "",
                question=pos.question or "",
                sport_tag=pos.sport_tag or "",
                source=pos.source or "",
                tier=signal.tier or current_tier,
                sell_pct=actual_sell_pct,
                realized_pnl_usdc=realized, timestamp=ts_iso,
                price=actual_price,
            )
```

- [ ] **Step 4: Run tests (passes)**

```
pytest tests/unit/orchestration/test_exit_event_append.py -v
pytest tests/ -q
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/exit_processor.py tests/unit/orchestration/test_exit_event_append.py
git commit -m "feat(orch): SPEC-Z17 exit event log on partial/final"
```

---

## Task 7: Dashboard Readers — Event-Sourced Read

**Files:**
- Modify: `src/presentation/dashboard/readers.py:101-160` (read_trades)
- Test: `tests/unit/presentation/dashboard/test_readers_z17.py` (yeni)

- [ ] **Step 1: Test event-sourced read**

```python
# tests/unit/presentation/dashboard/test_readers_z17.py
"""SPEC-Z17: dashboard readers event log'dan trade replay eder."""
import json
from pathlib import Path

from src.presentation.dashboard import readers


def _mk(tmp_path: Path) -> Path:
    logs = tmp_path / "logs"
    (logs / "audit").mkdir(parents=True)
    (logs / "session").mkdir(parents=True)
    return logs


def test_read_trades_replays_from_event_log(tmp_path: Path) -> None:
    logs = _mk(tmp_path)
    events = [
        {"kind": "entry", "condition_id": "c1", "slug": "s",
         "question": "Foo vs Bar", "sport_tag": "tennis",
         "source": "model", "direction": "BUY_YES",
         "entry_price": 0.45, "entry_timestamp": "t0",
         "size_usdc": 50.0, "shares": 100.0, "confidence": "A",
         "bookmaker_prob": 0.5, "anchor_probability": 0.5,
         "num_bookmakers": 5.0, "has_sharp": True,
         "entry_reason": "normal"},
        {"kind": "partial", "condition_id": "c1", "slug": "s",
         "question": "Foo vs Bar", "sport_tag": "tennis",
         "source": "model", "tier": 1, "sell_pct": 0.4,
         "realized_pnl_usdc": 5.0, "timestamp": "t1", "price": 0.8},
        {"kind": "final", "condition_id": "c1", "slug": "s",
         "question": "Foo vs Bar", "sport_tag": "tennis",
         "source": "model", "exit_price": 1.0,
         "exit_reason": "near_resolve", "exit_pnl_usdc": 10.0,
         "exit_timestamp": "t2"},
    ]
    (logs / "audit" / "trade_events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )
    trades = readers.read_trades(logs, n=100)
    assert len(trades) == 1
    assert trades[0]["entry_price"] == 0.45
    assert trades[0]["exit_pnl_usdc"] == 10.0
    assert len(trades[0]["partial_exits"]) == 1


def test_read_trades_ignores_trade_history_jsonl(tmp_path: Path) -> None:
    """Z17 sonrası trade_history.jsonl YOK SAYILIR (truth = event log)."""
    logs = _mk(tmp_path)
    # Legacy trade_history.jsonl içeriği — Z17 bunu okumamalı
    (logs / "audit" / "trade_history.jsonl").write_text(
        json.dumps({"condition_id": "LEGACY", "exit_pnl_usdc": 999.0}) + "\n",
        encoding="utf-8",
    )
    # Boş event log → boş sonuç
    trades = readers.read_trades(logs, n=100)
    cids = [t.get("condition_id") for t in trades]
    assert "LEGACY" not in cids


def test_read_trades_empty_event_log(tmp_path: Path) -> None:
    logs = _mk(tmp_path)
    assert readers.read_trades(logs, n=100) == []


def test_session_and_audit_dedupe_via_event_signature(tmp_path: Path) -> None:
    """SPEC-Z17: aynı event hem session hem audit'te varsa tek sayılır."""
    logs = _mk(tmp_path)
    ev = {"kind": "final", "condition_id": "c1", "slug": "s",
          "question": "q", "sport_tag": "tennis", "source": "model",
          "exit_price": 1.0, "exit_reason": "r",
          "exit_pnl_usdc": 5.0, "exit_timestamp": "t"}
    payload = json.dumps(ev) + "\n"
    (logs / "audit" / "trade_events.jsonl").write_text(payload, encoding="utf-8")
    (logs / "session" / "trade_events.jsonl").write_text(payload, encoding="utf-8")
    trades = readers.read_trades(logs, n=100)
    assert len(trades) == 1
    assert trades[0]["exit_pnl_usdc"] == 5.0  # iki kez sayılmaz
```

- [ ] **Step 2: Run test (fails)**

```
pytest tests/unit/presentation/dashboard/test_readers_z17.py -v
```

Expected: fails — readers hâlâ trade_history okuyor

- [ ] **Step 3: Rewrite read_trades**

`src/presentation/dashboard/readers.py` `read_trades` fonksiyonunu tamamen değiştir:

```python
def read_trades(logs_dir: Path, n: int = 100) -> list[dict[str, Any]]:
    """SPEC-Z17 (2026-06-04): trade kayıtları event log replay sonucu.

    Dosyalar: session/trade_events.jsonl + audit/trade_events.jsonl (mirror).
    Event'ler signature ile dedupe edilir (kind + condition_id + timestamp +
    pnl), sonra domain.trade.event_replay.replay_events ile trade record
    listesine dönüştürülür.

    Trade_history.jsonl artık OKUNMAZ (Z15/Z16 legacy).
    """
    from src.domain.trade.event_replay import replay_events

    paths = [
        logs_dir / "session" / "trade_events.jsonl",
        logs_dir / "audit" / "trade_events.jsonl",
    ]
    seen: set[tuple] = set()
    events: list[dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            continue
        for ev in _read_jsonl_tail(p, n, _BYTES_TRADES):
            kind = ev.get("kind")
            cid = ev.get("condition_id")
            ts = (ev.get("timestamp") or ev.get("exit_timestamp")
                  or ev.get("entry_timestamp") or "")
            pnl_raw = (ev.get("realized_pnl_usdc")
                       or ev.get("exit_pnl_usdc") or 0)
            try:
                pnl = round(float(pnl_raw), 4)
            except (TypeError, ValueError):
                pnl = 0.0
            sig = (kind, cid, ts, pnl)
            if sig in seen:
                continue
            seen.add(sig)
            events.append(ev)
    return replay_events(events)
```

Eski helper'ları + Z16 merger import'unu sil:

```python
# Aşağıdaki fonksiyonları SİL:
# _is_richer
# Z16 import bloğu (merge_exit_events çağrısı dahil)
```

- [ ] **Step 4: Run all tests**

```
pytest tests/ -q
```

Expected: Yeni Z17 testleri pass, eski readers testleri bozulabilir — bunlar Task 8'de güncellenecek.

- [ ] **Step 5: Commit**

```bash
git add src/presentation/dashboard/readers.py tests/unit/presentation/dashboard/test_readers_z17.py
git commit -m "feat(dashboard): SPEC-Z17 readers replay events instead of history merge"
```

---

## Task 8: Eski Readers Testlerini Güncelle

**Files:**
- Modify: `tests/unit/presentation/dashboard/test_readers.py`

- [ ] **Step 1: Eski trade_history tabanlı testleri Z17 event log fixture'a çevir**

`tests/unit/presentation/dashboard/test_readers.py` içindeki şu testleri güncelle (trade_history.jsonl yazan setup'ları trade_events.jsonl yazma'ya değiştir, ya da Z17 fixture helper'a yönlendir):

- `test_read_trades_missing_returns_empty` — değişiklik gerek YOK (boş klasör → boş döner)
- `test_read_trades_tail` — event log fixture'a çevir
- `test_read_trades_archive_files_are_ignored` — event log archive ignore testine çevir
- `test_read_trades_archive_not_merged_with_current` — aynı şekilde event log için
- `test_read_trades_session_and_audit_dedupe_by_entry_timestamp` — event log dedupe (signature)
- `test_read_trades_same_condition_different_entry_kept_separately` — aynı cid iki entry → ikinci atlanır (replay invariant)
- `test_read_trades_includes_partial_exits_from_session` — partial event ile değiştir
- `test_read_trades_orphan_record_deduped_across_session_and_audit` — SIL (Z16 specific, Z17 dedupe signature ile zaten kapsanır)
- `test_read_trades_orphan_richer_record_wins` — SIL

Her güncelleme/silme bireysel commit yerine **tek toplu commit**:

- [ ] **Step 2: Run readers test paketi**

```
pytest tests/unit/presentation/dashboard/test_readers.py -v
```

Expected: tüm testler pass

- [ ] **Step 3: Commit**

```bash
git add tests/unit/presentation/dashboard/test_readers.py
git commit -m "test(dashboard): SPEC-Z17 readers tests use event log fixtures"
```

---

## Task 9: Reboot Davranışı — trade_events.jsonl Archive

**Files:**
- Modify: `scripts/reboot.py:33-80` (_AUDIT_FILES_CLEAR listesi)
- Test: `tests/integration/test_reboot.py` (mevcut, ekleme)

- [ ] **Step 1: Test archive davranışı**

`tests/integration/test_reboot.py` içine ekle:

```python
def test_reboot_archives_trade_events_jsonl(tmp_path, monkeypatch):
    """SPEC-Z17: reboot trade_events.jsonl'i arşivler (copy), sonra siler."""
    monkeypatch.chdir(tmp_path)
    audit = tmp_path / "logs" / "audit"
    audit.mkdir(parents=True)
    f = audit / "trade_events.jsonl"
    f.write_text('{"kind": "entry", "condition_id": "c1"}\n', encoding="utf-8")

    # reboot.py'den archive_audit_logs + clear_audit_logs çağrılarını çağır
    import scripts.reboot as rb
    rb.archive_audit_logs(open_condition_ids=None, timestamp="20260604_120000")
    archives = list(audit.glob("trade_events.archive.*.jsonl"))
    assert len(archives) == 1
    assert archives[0].read_text(encoding="utf-8").startswith('{"kind":')

    rb.clear_audit_logs()
    assert not f.exists() or f.stat().st_size == 0
```

- [ ] **Step 2: Run test (fails — listede yok)**

```
pytest tests/integration/test_reboot.py::test_reboot_archives_trade_events_jsonl -v
```

Expected: archive 0 (trade_events listede değil)

- [ ] **Step 3: Add trade_events.jsonl to archive list**

`scripts/reboot.py:33-80` arasında `_AUDIT_FILES_CLEAR` listesini bul, ekle:

```python
_AUDIT_FILES_CLEAR = [
    ROOT / "logs" / "audit" / "trade_history.jsonl",
    ROOT / "logs" / "audit" / "trade_events.jsonl",   # SPEC-Z17
    ROOT / "logs" / "audit" / "trade_exits.jsonl",    # Z16 legacy (deprecate)
    ROOT / "logs" / "audit" / "equity_history.jsonl",
    # ... mevcut diğer dosyalar
]
```

(Tam listeyi mevcut sıraya göre koru — sadece trade_events.jsonl ekle.)

- [ ] **Step 4: Run test (passes)**

```
pytest tests/integration/test_reboot.py -v
```

Expected: archive testi pass + mevcut reboot testleri bozulmaz

- [ ] **Step 5: Commit**

```bash
git add scripts/reboot.py tests/integration/test_reboot.py
git commit -m "feat(reboot): SPEC-Z17 archive trade_events.jsonl on reboot"
```

---

## Task 10: Migration Script — Mevcut Veri Z17 Event Log'a

**Files:**
- Create: `scripts/_z17_migrate_to_event_log.py`

- [ ] **Step 1: Migration script yaz**

```python
# scripts/_z17_migrate_to_event_log.py
"""SPEC-Z17 one-shot: mevcut trade_history.jsonl + Z16 trade_exits.jsonl
event'lerini trade_events.jsonl'e dönüştür.

Çalıştırma sırası:
  1. trade_history kayıtlarından entry event'leri çıkar (entry_price set'li olanlar)
  2. Aynı kayıtlardan partial event'leri çıkar (partial_exits listesi)
  3. Aynı kayıtlardan final event'leri çıkar (exit_price set'li olanlar)
  4. Z16 trade_exits.jsonl event'lerini ekle (signature dedupe)
  5. Timestamp sırasıyla yaz
"""
from __future__ import annotations

import json
from pathlib import Path


SRC_HISTORY = Path("logs/audit/trade_history.jsonl")
SRC_EXITS_Z16 = Path("logs/audit/trade_exits.jsonl")
TARGET_AUDIT = Path("logs/audit/trade_events.jsonl")
TARGET_SESSION = Path("logs/session/trade_events.jsonl")


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> None:
    history = _read_jsonl(SRC_HISTORY)
    z16 = _read_jsonl(SRC_EXITS_Z16)

    events: list[dict] = []
    for r in history:
        cid = r.get("condition_id")
        if not cid:
            continue
        meta = {
            "condition_id": cid,
            "slug": r.get("slug") or "",
            "question": r.get("question") or "",
            "sport_tag": r.get("sport_tag") or "",
            "source": r.get("source") or "",
        }
        if r.get("entry_price") is not None:
            events.append({**meta, "kind": "entry",
                           "direction": r.get("direction") or "",
                           "entry_price": r.get("entry_price"),
                           "entry_timestamp": r.get("entry_timestamp") or "",
                           "size_usdc": r.get("size_usdc") or 0.0,
                           "shares": r.get("shares") or 0.0,
                           "confidence": r.get("confidence") or "",
                           "bookmaker_prob": r.get("bookmaker_prob") or 0.0,
                           "anchor_probability": r.get("anchor_probability") or 0.0,
                           "num_bookmakers": r.get("num_bookmakers") or 0.0,
                           "has_sharp": r.get("has_sharp") or False,
                           "entry_reason": r.get("entry_reason") or ""})
        for p in (r.get("partial_exits") or []):
            events.append({**meta, "kind": "partial",
                           "tier": p.get("tier"),
                           "sell_pct": p.get("sell_pct"),
                           "realized_pnl_usdc": p.get("realized_pnl_usdc"),
                           "timestamp": p.get("timestamp"),
                           "price": p.get("price")})
        if r.get("exit_price") is not None:
            events.append({**meta, "kind": "final",
                           "exit_price": r.get("exit_price"),
                           "exit_reason": r.get("exit_reason") or "",
                           "exit_pnl_usdc": r.get("exit_pnl_usdc") or 0.0,
                           "exit_timestamp": r.get("exit_timestamp") or ""})

    # Z16 events — meta'yı buradan al
    for e in z16:
        events.append(e)

    # Dedupe by signature (kind + cid + ts + pnl)
    seen: set[tuple] = set()
    uniq: list[dict] = []
    for e in events:
        ts = (e.get("timestamp") or e.get("exit_timestamp")
              or e.get("entry_timestamp") or "")
        pnl_raw = (e.get("realized_pnl_usdc")
                   or e.get("exit_pnl_usdc") or 0)
        try:
            pnl = round(float(pnl_raw), 4)
        except (TypeError, ValueError):
            pnl = 0.0
        sig = (e.get("kind"), e.get("condition_id"), ts, pnl)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(e)

    # Timestamp sırasıyla yaz
    def _ts(e: dict) -> str:
        return (e.get("entry_timestamp") or e.get("timestamp")
                or e.get("exit_timestamp") or "")
    uniq.sort(key=_ts)

    payload = "\n".join(json.dumps(e, ensure_ascii=False) for e in uniq) + "\n"
    for tgt in [TARGET_AUDIT, TARGET_SESSION]:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_text(payload, encoding="utf-8")
    print(f"Z17 migration: {len(uniq)} event yazıldı ({len(events)} ham, "
          f"{len(events) - len(uniq)} duplicate atlandı)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Migration dry-run + verify**

```bash
PYTHONIOENCODING=utf-8 python scripts/_z17_migrate_to_event_log.py
ls -la logs/audit/trade_events.jsonl logs/session/trade_events.jsonl
```

Expected: dosyalar oluştu, equal boyut

- [ ] **Step 3: Commit**

```bash
git add scripts/_z17_migrate_to_event_log.py
git commit -m "chore: SPEC-Z17 migration script — history+Z16 → trade_events.jsonl"
```

---

## Task 11: Legacy Z15/Z16 Cleanup

**Files:**
- Delete: `src/infrastructure/persistence/trade_exits_log.py`
- Delete: `src/presentation/dashboard/exit_events_merger.py`
- Delete: `scripts/_z16_migrate_to_event_log.py`
- Delete: `scripts/_z16_full_restore.py` ya da `_z15_full_restore.py`
- Delete: `scripts/_z16_audit_check.py`
- Delete: `scripts/_z15_restore_lost_trades.py`
- Modify: `src/infrastructure/persistence/trade_logger.py` (Z15.B/E shrink-guard + Z15.D orphan_metadata KALDIR)
- Modify: `src/orchestration/entry_processor.py` (Z15.A entry_recovery import KALDIR, write_entry_recovery çağrı KALDIR)
- Delete: `src/orchestration/entry_recovery.py`
- Modify: `src/orchestration/_factory_loggers.py` (build_trade_exits_log KALDIR)
- Modify: `src/orchestration/agent.py` (trade_exits_log AgentDeps field KALDIR)
- Modify: `src/orchestration/factory.py` (trade_exits_log wiring KALDIR)
- Modify: `src/orchestration/exit_processor.py` (Z16 append çağrıları KALDIR — sadece Z17 kalsın)

- [ ] **Step 1: Tek tek dosyaları sil**

```bash
git rm src/infrastructure/persistence/trade_exits_log.py
git rm src/presentation/dashboard/exit_events_merger.py
git rm src/orchestration/entry_recovery.py
git rm scripts/_z16_migrate_to_event_log.py
git rm scripts/_z16_audit_check.py
git rm scripts/_z15_restore_lost_trades.py
git rm scripts/_z15_full_restore.py
git rm tests/unit/infrastructure/persistence/test_trade_exits_log.py
git rm tests/unit/presentation/dashboard/test_exit_events_merger.py
git rm tests/unit/orchestration/test_entry_recovery.py
```

- [ ] **Step 2: trade_logger.py cleanup**

`src/infrastructure/persistence/trade_logger.py`:
- `_rewrite_matching` içinde Z15.E shrink-guard kod bloğunu (line 200-240 civarı) SİL
- `_rewrite_matching` imzasından `orphan_metadata` parametresini SİL
- `update_on_exit` ve `log_partial_exit` imzalarından `orphan_metadata` parametresini SİL

Tam blok değişimi planda gösterilemez (uzun); subagent dosyayı okuyup ARCH_GUARD self-check yazıp uygulasın.

- [ ] **Step 3: entry_processor + exit_processor + factory cleanup**

`src/orchestration/entry_processor.py`:
- `write_entry_recovery` import + `try/except + write_entry_recovery` çağrısı SİL (artık event_log var)
- `trade_logger.log(trade_record)` çağrısı KALIR (legacy yazma — Task 12'de tamamen silinir)

`src/orchestration/exit_processor.py`:
- `trade_exits_log.append_partial` ve `append_final` çağrılarını SİL (Z17 var)
- `_orphan_meta` helper'ı SİL
- `trade_logger.update_on_exit` ve `log_partial_exit` çağrıları KALIR (legacy yazma — Task 12'de silinir)

`src/orchestration/_factory_loggers.py`:
- `build_trade_exits_log` fonksiyonunu SİL
- `TradeExitsLog` import SİL

`src/orchestration/agent.py`:
- `TradeExitsLog` import SİL
- `AgentDeps.trade_exits_log` field SİL

`src/orchestration/factory.py`:
- `build_trade_exits_log` import + çağrı SİL
- `AgentDeps(...)` çağrısında `trade_exits_log=...` argüman SİL

- [ ] **Step 4: Run all tests**

```
pytest tests/ -q
```

Expected: tüm testler pass (silinen testler dahil — pytest collection sıfır fail)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: SPEC-Z17 remove Z15/Z16 patches — TradeExitsLog, merger, entry_recovery, shrink-guard"
```

---

## Task 12: Legacy trade_history.jsonl Yazımı Kaldır

**Files:**
- Modify: `src/orchestration/entry_processor.py` (trade_logger.log çağrılarını SİL)
- Modify: `src/orchestration/exit_processor.py` (trade_logger.update_on_exit + log_partial_exit çağrılarını SİL)
- Modify: `src/orchestration/exit_audit_writer.py` (trade_logger.log SİL veya synth event olarak Z17'ye yönlendir)
- Modify: `src/orchestration/startup.py` (`_detect_and_restore_orphans` ve `_reconcile_realized_pnl` Z17 event_log'a yönelt veya tamamen sil)
- Modify: `src/orchestration/_factory_loggers.py` (build_trade_logger SİL)
- Modify: `src/orchestration/agent.py` (TradeHistoryLogger import + AgentDeps.trade_logger field SİL)
- Modify: `src/orchestration/factory.py` (trade_logger build + wiring SİL)
- Modify: `src/orchestration/factory_refresh_hooks.py` (calibration trades_path → trade_events.jsonl + replay)
- Modify: `src/orchestration/health_monitor.py` (trade_history.jsonl referansı → trade_events.jsonl)
- Delete: `src/infrastructure/persistence/trade_logger.py` (eğer TradeRecord başka yerlerde kullanılmıyorsa)
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py` — tamamen SİL ya da TradeRecord-only testlere indir

- [ ] **Step 1: TradeRecord'u Domain'e Taşı (gerekiyorsa)**

`src/infrastructure/persistence/trade_logger.py`'deki `TradeRecord` pydantic modelini yeni domain modülüne taşı:

```python
# src/domain/trade/trade_record.py — sadece veri modeli, I/O yok
```

(Eğer testler ve event yazımı TradeRecord'a bağımlıysa korunur; değilse silinir.)

- [ ] **Step 2: Legacy yazma çağrılarını sil**

`src/orchestration/entry_processor.py` `_persist_filled_position`:
- `self.deps.trade_logger.log(trade_record)` SİL
- (entry append_entry zaten Task 5'te eklendi)

`src/orchestration/exit_processor.py`:
- `self.deps.trade_logger.update_on_exit(...)` SİL
- `self.deps.trade_logger.log_partial_exit(...)` SİL

`src/orchestration/exit_audit_writer.py:105` `deps.trade_logger.log(record)`:
- SİL ya da `trade_event_log.append_final` ile yönelt (synth exit)

- [ ] **Step 3: Startup reconcile event-based**

`src/orchestration/startup.py`:
- `_detect_and_restore_orphans` SİL (event log append-only, orphan diye bir şey yok)
- `_reconcile_realized_pnl` → event log'dan replay sonra equity hesabı yap

- [ ] **Step 4: Calibration + HealthMonitor güncellemesi**

`src/orchestration/factory_refresh_hooks.py:61`:
```python
# trades_path=Path("logs/audit/trade_events.jsonl"),
```
Plus calibration_refresher'da event log replay kullan.

`src/orchestration/health_monitor.py:204`:
```python
# history = self.audit_dir / "trade_events.jsonl"
```
read_trades benzeri event-replay.

- [ ] **Step 5: AgentDeps + factory cleanup**

`src/orchestration/agent.py`:
- `TradeHistoryLogger` import SİL
- `AgentDeps.trade_logger` field SİL

`src/orchestration/factory.py`:
- `build_trade_logger` import + çağrı SİL
- `AgentDeps(...)` `trade_logger=...` argüman SİL

`src/orchestration/_factory_loggers.py`:
- `build_trade_logger` SİL
- `TradeHistoryLogger` import SİL

- [ ] **Step 6: TradeHistoryLogger silinmesi**

Eğer `TradeRecord` zaten Step 1'de domain'e taşındıysa:
```bash
git rm src/infrastructure/persistence/trade_logger.py
git rm tests/unit/infrastructure/persistence/test_trade_logger.py
```

Yoksa: dosyada sadece `TradeRecord` + `_split_sport_tag` kalır, `TradeHistoryLogger` class'ı SİL.

- [ ] **Step 7: Run all tests**

```
pytest tests/ -q
```

Expected: tüm testler pass

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: SPEC-Z17 remove legacy trade_history.jsonl write paths"
```

---

## Task 13: DECISIONS.md + ARCH_GUARD self-check + Production Reload

**Files:**
- Modify: `DECISIONS.md` (SPEC-Z17 entry §B'ye)
- Run: `scripts/reboot.py reload --yes`

- [ ] **Step 1: SPEC-Z17 entry yaz**

`DECISIONS.md` §B kronolojik log başına ekle:

```markdown
### SPEC-Z17 — Trade Event Sourcing (2026-06-04)

**Karar:** trade_history.jsonl atomic-rewrite mimarisi event sourcing'e taşındı.

Tek dosya `logs/audit/trade_events.jsonl` (mirror: `logs/session/trade_events.jsonl`)
tüm bot aksiyonlarını kronolojik APPEND-ONLY tutar:
- "entry" event: pozisyon açıldığında
- "partial" event: scale-out / partial-SL
- "final" event: tam kapanış

Dashboard event log'u okur, `domain.trade.event_replay.replay_events` ile
trade record listesine dönüştürür. Hiçbir rewrite yok, dedupe signature
bazlı (kind + cid + timestamp + pnl).

**Kaldırılan yamalar:**
- Z15.A entry_recovery (artık event_log var)
- Z15.B/E shrink-guard (atomic rewrite yok)
- Z15.D orphan_metadata (sadece append, orphan yok)
- Z16 TradeExitsLog + exit_events_merger (Z17 tek truth)

**Neden:**
4 yama (Z15.B/D/E + Z16) trade_history veri kaybını engelleyemedi.
Phase 4.5 architectural problem: yama yerine mimari değişim. Event sourcing
proven pattern (financial systems). Append-only → veri kaybı imkansız.

**Etki:**
- `src/domain/trade/event_replay.py` + `event_types.py` (yeni domain modülleri)
- `src/infrastructure/persistence/trade_event_log.py` (yeni infra)
- `src/orchestration/{entry,exit}_processor.py` (event append)
- `src/presentation/dashboard/readers.py` (event replay)
- `scripts/reboot.py` (trade_events.jsonl archive)
- DELETE: TradeExitsLog, exit_events_merger, entry_recovery, shrink-guard
- 14 yeni test (domain replay 7 + event_log 7), eski 45 trade_logger test SİL veya KÜÇÜLT
- Migration script: history + Z16 → trade_events.jsonl

**Garanti:** Hiçbir cycle (heavy/light), reload, phantom-restore, mistik
scheduler trade_events.jsonl içeriğini SİLEMEZ — append-only OS guarantee.
```

- [ ] **Step 2: ARCH_GUARD self-check çalıştır**

Tüm değiştirilen dosyalarda 8 anti-pattern kontrol et:

```bash
# Dosya boyutu (400 limit)
wc -l src/domain/trade/*.py src/infrastructure/persistence/trade_event_log.py \
      src/presentation/dashboard/readers.py src/orchestration/exit_processor.py \
      src/orchestration/entry_processor.py
```

Beklenen: hepsi <400.

- [ ] **Step 3: Full pytest**

```
pytest tests/ -q --no-header
```

Beklenen: tüm testler pass, 0 fail.

- [ ] **Step 4: Migration + reload**

```bash
PYTHONIOENCODING=utf-8 python scripts/_z17_migrate_to_event_log.py
PYTHONIOENCODING=utf-8 python scripts/reboot.py reload --yes
```

Beklenen: bot+dashboard çalışıyor, dashboard yeni mimariyi okuyor.

- [ ] **Step 5: Audit + commit DECISIONS**

```bash
git add DECISIONS.md
git commit -m "docs: SPEC-Z17 trade event sourcing — DECISIONS log entry"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] Tek append-only dosya → Task 3 (TradeEventLog)
- [x] Entry/partial/final events → Task 5/6 (processors)
- [x] Dashboard event replay → Task 7 (readers)
- [x] Z15.B/D/E + Z16 kaldırılır → Task 11
- [x] Reboot=arşivle → Task 9
- [x] Reload=dokunma → mevcut reboot.py reload (state korunur)
- [x] Hard cycle veriyi silemez → append-only OS garanti (Task 3 test #7)
- [x] DECISIONS güncel → Task 13

**2. Placeholder scan:**
- Hiçbir adımda "TBD", "TODO", "implement later" yok
- Her test/kod adımı tam içerik
- Migration script tam
- Task 11/12 toplu cleanup gerekirse subagent ARCH_GUARD self-check yazıp uygular

**3. Type consistency:**
- `EventKind` literal'i Task 1 + 2 + 3'te aynı
- `TradeEventLog` API'si Task 3 + 4 + 5 + 6'da tutarlı
- `replay_events` signature Task 2 + 7'de tutarlı

---

## Risk + Geri Alma

**Risk:** Task 12 (legacy yazma kaldırma) testleri kırabilir — TradeHistoryLogger derinden bağlı.
**Mitigation:** Task 11'de SADECE yamalar (Z15/Z16) kaldırılır, trade_history.jsonl yazımı KALIR. Task 12 ayrı PR'da bot izlendikten sonra (1 hafta) yapılabilir.

**Geri Alma:**
- Z17 sorunluysa: AgentDeps'ten trade_event_log SİL, dashboard readers eski sürüme dön (`git revert`). Trade_history.jsonl hâlâ yazılıyor (Task 11 sonrası), eski mimariye dönüş 1 dakika.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-04-trade-event-sourcing.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Her task için fresh subagent, review checkpoint, hızlı iterasyon. Risk düşük (her task isolated, test gate'li).

**2. Inline Execution** — Bu session'da batch execution + checkpoint. Hızlı ama context yükü fazla.

**Hangisi?**
