# Tekrar-giriş yasağı + test verisi temizliği — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** (A) Bir markete girip zararla kapanınca o markete bu session tekrar girişi engellemek; (B) bu session'daki 5 kural-dışı işlemi dashboard'dan tamamen temizlemek.

**Architecture:** (A) Saf domain fonksiyonu zararla kapanan condition_id'leri defterden türetir; `run_heavy` başında portfolio'ya yazılır; yeni bir pre-execution guard girişi bloklar. (B) Saf dönüşüm fonksiyonları hedef işlemleri çıkarır + equity eğrisini yeniden hesaplar; tek-seferlik script yedek alıp uygular ve doğrular.

**Tech Stack:** Python 3.12, pytest, dataclass, append-only JSONL (logs/audit/).

**Spec:** [docs/superpowers/specs/2026-06-07-reentry-loss-guard-and-cleanup-design.md](../specs/2026-06-07-reentry-loss-guard-and-cleanup-design.md)

> **Her kod Edit/Write öncesi:** ARCH_GUARD 8-madde self-check satırı yazılacak.

---

# PART A — Tekrar-giriş yasağı (production)

## Task A1: Saf domain fonksiyonu `closed_at_loss_cids`

**Files:**
- Create: `src/domain/trade/loss_tracking.py`
- Test: `tests/unit/domain/trade/test_loss_tracking.py`

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/trade/test_loss_tracking.py
from src.domain.trade.loss_tracking import closed_at_loss_cids


def test_closed_at_loss_cids_net_negative_final_marked():
    events = [
        {"kind": "entry", "condition_id": "A", "entry_price": 0.6},
        {"kind": "partial", "condition_id": "A", "realized_pnl_usdc": -3.0},
        {"kind": "final", "condition_id": "A", "exit_pnl_usdc": -10.0},
    ]
    assert closed_at_loss_cids(events) == {"A"}


def test_closed_at_loss_cids_net_positive_not_marked():
    events = [
        {"kind": "entry", "condition_id": "B"},
        {"kind": "final", "condition_id": "B", "exit_pnl_usdc": 5.0},
    ]
    assert closed_at_loss_cids(events) == set()


def test_closed_at_loss_cids_open_no_final_not_marked():
    events = [{"kind": "entry", "condition_id": "C"}]
    assert closed_at_loss_cids(events) == set()


def test_closed_at_loss_cids_ignores_missing_condition_id():
    events = [{"kind": "final", "exit_pnl_usdc": -1.0}]
    assert closed_at_loss_cids(events) == set()
```

- [ ] **Step 2: Run, verify fail**

Run: `python -m pytest tests/unit/domain/trade/test_loss_tracking.py -v`
Expected: FAIL (ModuleNotFoundError: loss_tracking)

- [ ] **Step 3: Implement**

```python
# src/domain/trade/loss_tracking.py
"""SPEC-Z24: zararla kapanan condition_id türetimi. Pure, I/O yok. Domain."""
from __future__ import annotations

from typing import Any


def closed_at_loss_cids(events: list[dict[str, Any]]) -> set[str]:
    """En az bir 'final' çıkışı olan VE net realized < 0 olan condition_id'ler.

    net realized = tüm 'partial' realized_pnl_usdc + tüm 'final' exit_pnl_usdc.
    Canlı akışta: episode-1 zararla kapanınca defterde net<0 görünür → bloklanır
    (gelecek kazanan episode henüz yok).
    """
    net: dict[str, float] = {}
    has_final: set[str] = set()
    for ev in events:
        cid = ev.get("condition_id")
        if not cid:
            continue
        kind = ev.get("kind")
        if kind == "partial":
            net[cid] = net.get(cid, 0.0) + float(ev.get("realized_pnl_usdc") or 0.0)
        elif kind == "final":
            net[cid] = net.get(cid, 0.0) + float(ev.get("exit_pnl_usdc") or 0.0)
            has_final.add(cid)
    return {cid for cid in has_final if net.get(cid, 0.0) < 0.0}
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/domain/trade/test_loss_tracking.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/trade/loss_tracking.py tests/unit/domain/trade/test_loss_tracking.py
git commit -m "feat(domain): SPEC-Z24 closed_at_loss_cids — zararla kapanan market türetimi"
```

---

## Task A2: PortfolioManager'a `closed_at_loss` state alanı

**Files:**
- Modify: `src/domain/portfolio/manager.py:25` (positions field'ının yanına)
- Test: `tests/unit/domain/portfolio/test_manager.py` (varsa ekle, yoksa oluştur)

- [ ] **Step 1: Failing test**

```python
# tests/unit/domain/portfolio/test_manager.py (yeni test ekle)
from src.domain.portfolio.manager import PortfolioManager


def test_portfolio_has_empty_closed_at_loss_by_default():
    pm = PortfolioManager(initial_bankroll=1000.0)
    assert pm.closed_at_loss == set()


def test_portfolio_closed_at_loss_is_assignable():
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.closed_at_loss = {"A", "B"}
    assert "A" in pm.closed_at_loss
```

- [ ] **Step 2: Run, verify fail**

Run: `python -m pytest tests/unit/domain/portfolio/test_manager.py -k closed_at_loss -v`
Expected: FAIL (AttributeError: closed_at_loss)

- [ ] **Step 3: Implement** — `manager.py` dataclass field ekle (line 25 `positions` altına):

```python
    positions: dict[str, Position] = field(default_factory=dict)
    closed_at_loss: set[str] = field(default_factory=set)  # SPEC-Z24: tekrar-giriş yasağı
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/domain/portfolio/test_manager.py -k closed_at_loss -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/domain/portfolio/manager.py tests/unit/domain/portfolio/test_manager.py
git commit -m "feat(domain): SPEC-Z24 PortfolioManager.closed_at_loss state alanı"
```

---

## Task A3: `check_loss_reentry` guard'ı

**Files:**
- Modify: `src/orchestration/entry_guards.py` (yeni fonksiyon, dosya sonuna `resolve_market_meta`'dan önce/sonra)
- Test: `tests/unit/orchestration/test_entry_guards.py` (yeni)

- [ ] **Step 1: Failing test**

```python
# tests/unit/orchestration/test_entry_guards.py
from types import SimpleNamespace

from src.orchestration.entry_guards import check_loss_reentry


def _market(cid="X"):
    return SimpleNamespace(condition_id=cid, slug="wnba-a-b-2026", sport_tag="wnba",
                           sports_market_type="moneyline", question="A vs B", event_id="1")


def _deps(closed):
    portfolio = SimpleNamespace(closed_at_loss=closed)
    state = SimpleNamespace(portfolio=portfolio)
    skip_log = []
    stock = SimpleNamespace(add=lambda m, r: skip_log.append(("stock", r)))
    skipped_logger = SimpleNamespace()
    return SimpleNamespace(state=state, stock=stock, skipped_logger=skipped_logger), skip_log


def test_check_loss_reentry_blocks_when_cid_closed_at_loss(monkeypatch):
    import src.orchestration.entry_guards as g
    monkeypatch.setattr(g.operational_writers, "log_skip", lambda *a, **k: None)
    deps, _ = _deps({"X"})
    assert check_loss_reentry(deps, _market("X")) is True


def test_check_loss_reentry_allows_when_not_closed(monkeypatch):
    import src.orchestration.entry_guards as g
    monkeypatch.setattr(g.operational_writers, "log_skip", lambda *a, **k: None)
    deps, _ = _deps({"Y"})
    assert check_loss_reentry(deps, _market("X")) is False


def test_check_loss_reentry_allows_when_set_missing(monkeypatch):
    import src.orchestration.entry_guards as g
    monkeypatch.setattr(g.operational_writers, "log_skip", lambda *a, **k: None)
    deps, _ = _deps(set())
    assert check_loss_reentry(deps, _market("X")) is False
```

- [ ] **Step 2: Run, verify fail**

Run: `python -m pytest tests/unit/orchestration/test_entry_guards.py -v`
Expected: FAIL (ImportError: check_loss_reentry)

- [ ] **Step 3: Implement** — `entry_guards.py`'a ekle (mevcut guard kalıbı birebir):

```python
def check_loss_reentry(deps, market: MarketData) -> bool:
    """SPEC-Z24: bu session'da zararla kapanan markete tekrar giriş yasağı.

    True → bloke. Kardeş guard'lar gibi her zaman açık (config flag yok).
    """
    closed = getattr(deps.state.portfolio, "closed_at_loss", None)
    if not closed or market.condition_id not in closed:
        return False
    detail = f"condition_id={market.condition_id[:20]}..."
    operational_writers.log_skip(
        deps.skipped_logger, market,
        "loss_reentry_blocked", detail=detail,
    )
    deps.stock.add(market, "loss_reentry_blocked")
    return True
```

Modül docstring'indeki guard listesine bir satır ekle: `- check_loss_reentry: zararla kapanan markete tekrar giriş (SPEC-Z24)`.

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/orchestration/test_entry_guards.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/orchestration/entry_guards.py tests/unit/orchestration/test_entry_guards.py
git commit -m "feat(orchestration): SPEC-Z24 check_loss_reentry guard"
```

---

## Task A4: Guard'ı `_execute_entry`'e bağla + `run_heavy`'de set'i doldur

**Files:**
- Modify: `src/orchestration/entry_processor.py` (import; run_heavy line ~43; _execute_entry line ~178)
- Test: `tests/unit/orchestration/test_entry_processor.py` (varsa entegrasyon testi ekle)

- [ ] **Step 1: Failing test** (guard'ın gerçekten girişi durdurduğunu doğrula)

```python
# tests/unit/orchestration/test_entry_processor.py (yeni test ekle)
def test_execute_entry_blocked_when_condition_closed_at_loss(monkeypatch):
    """closed_at_loss içinde olan cid için place_order ÇAĞRILMAZ."""
    from types import SimpleNamespace
    import src.orchestration.entry_processor as ep

    monkeypatch.setattr(ep, "check_duplicate_condition", lambda d, m: False)
    monkeypatch.setattr(ep, "check_exclude_combo", lambda d, m, s: False)
    monkeypatch.setattr(ep, "check_correlated_bet", lambda d, m, s: False)

    placed = []
    portfolio = SimpleNamespace(closed_at_loss={"LOST"}, positions={})
    state = SimpleNamespace(portfolio=portfolio,
                            config=SimpleNamespace(mode=SimpleNamespace(value="paper")))
    deps = SimpleNamespace(
        state=state,
        executor=SimpleNamespace(place_order=lambda **k: placed.append(k) or {"status": "simulated"}),
        skipped_logger=SimpleNamespace(),
        stock=SimpleNamespace(add=lambda m, r: None),
    )
    monkeypatch.setattr(ep.operational_writers, "log_skip", lambda *a, **k: None)

    market = SimpleNamespace(condition_id="LOST", slug="wnba-a-b", sport_tag="wnba",
                             sports_market_type="moneyline", question="A vs B",
                             event_id="1", yes_token_id="t", no_token_id="t",
                             yes_price=0.5, no_price=0.5)
    signal = SimpleNamespace(direction=SimpleNamespace(value="BUY_YES"), size_usdc=10.0)

    proc = ep.EntryProcessor(deps)
    proc._execute_entry(market, signal)
    assert placed == []  # bloke edildi, emir gitmedi
```

- [ ] **Step 2: Run, verify fail**

Run: `python -m pytest tests/unit/orchestration/test_entry_processor.py -k closed_at_loss -v`
Expected: FAIL (place_order çağrıldı, placed boş değil)

- [ ] **Step 3: Implement**

(a) Import'a ekle (`entry_processor.py` line 18-23 bloğu):

```python
from src.orchestration.entry_guards import (
    check_correlated_bet,
    check_duplicate_condition,
    check_exclude_combo,
    check_loss_reentry,
    resolve_market_meta,
)
from src.domain.trade.loss_tracking import closed_at_loss_cids
```

(b) `run_heavy` içinde, scan_by_cid satırından (line 42) sonra:

```python
        scan_by_cid = {m.condition_id: m for m in scan_fresh}

        # SPEC-Z24: zararla kapanan condition_id'leri defterden türet (tekrar-giriş yasağı).
        # Her heavy cycle yenilenir → reload sonrası kendiliğinden dolar.
        if self.deps.trade_event_log is not None:
            self.deps.state.portfolio.closed_at_loss = closed_at_loss_cids(
                self.deps.trade_event_log.read_events()
            )
```

(c) `_execute_entry` içinde, `check_correlated_bet` bloğundan (line 177-178) sonra:

```python
        if check_correlated_bet(self.deps, market, signal):
            return
        if check_loss_reentry(self.deps, market):
            return
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/orchestration/test_entry_processor.py -k closed_at_loss -v`
Expected: 1 passed

- [ ] **Step 5: Run full suite (regression)**

Run: `python -m pytest tests/unit/orchestration tests/unit/domain -q`
Expected: tümü pass

- [ ] **Step 6: Commit**

```bash
git add src/orchestration/entry_processor.py tests/unit/orchestration/test_entry_processor.py
git commit -m "feat(orchestration): SPEC-Z24 tekrar-giriş guard'ını entry akışına bağla"
```

---

# PART B — Veri temizliği (tek seferlik)

## Task B1: Saf temizlik fonksiyonları (event çıkarma + equity rebuild)

**Files:**
- Create: `scripts/cleanup_z24.py` (saf fonksiyonlar + main; bu task'ta sadece saf fonksiyonlar)
- Test: `tests/unit/scripts/test_cleanup_z24.py`

- [ ] **Step 1: Failing test**

```python
# tests/unit/scripts/test_cleanup_z24.py
from scripts.cleanup_z24 import remove_events, rebuild_equity


def test_remove_events_full_slug_drops_all_episodes():
    events = [
        {"kind": "entry", "slug": "S1", "condition_id": "c1", "entry_timestamp": "t0"},
        {"kind": "final", "slug": "S1", "condition_id": "c1", "exit_pnl_usdc": -1.0},
        {"kind": "entry", "slug": "KEEP", "condition_id": "c9", "entry_timestamp": "t0"},
    ]
    out = remove_events(events, full_slugs={"S1"}, episodes=[])
    assert [e["slug"] for e in out] == ["KEEP"]


def test_remove_events_episode_keeps_first_drops_targeted():
    events = [
        {"kind": "entry", "slug": "ML", "condition_id": "c", "entry_timestamp": "t1"},
        {"kind": "final", "slug": "ML", "condition_id": "c", "exit_pnl_usdc": -10.0,
         "exit_timestamp": "t1b"},
        {"kind": "entry", "slug": "ML", "condition_id": "c", "entry_timestamp": "t2"},
        {"kind": "final", "slug": "ML", "condition_id": "c", "exit_pnl_usdc": -24.0,
         "exit_timestamp": "t2b"},
    ]
    out = remove_events(events, full_slugs=set(), episodes=[("ML", "t2")])
    # 1. episode (t1) kalır, 2. episode (t2) gider
    entries = [e["entry_timestamp"] for e in out if e["kind"] == "entry"]
    assert entries == ["t1"]
    assert len(out) == 2


def test_rebuild_equity_subtracts_removed_realized():
    removed = [
        {"kind": "final", "exit_pnl_usdc": -24.0, "exit_timestamp": "2026-06-07T01:00:00+00:00",
         "entry_timestamp": "2026-06-07T00:00:00+00:00", "size_usdc": 50.0},
    ]
    snaps = [
        {"timestamp": "2026-06-07T02:00:00+00:00", "bankroll": 900.0, "realized_pnl": -24.0,
         "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0},
    ]
    out = rebuild_equity(snaps, removed, initial_bankroll=1000.0)
    assert out[0]["realized_pnl"] == 0.0      # -24 geri eklendi
    assert out[0]["bankroll"] == 924.0        # 900 - (-24) = 924
    assert out[0]["unrealized_pnl"] == 0.0    # titreme dokunulmaz
```

- [ ] **Step 2: Run, verify fail**

Run: `python -m pytest tests/unit/scripts/test_cleanup_z24.py -v`
Expected: FAIL (ModuleNotFoundError: scripts.cleanup_z24)

- [ ] **Step 3: Implement saf fonksiyonlar**

```python
# scripts/cleanup_z24.py
"""SPEC-Z24 tek-seferlik temizlik: kural-dışı 5 işlemi defterden çıkar +
equity eğrisini yeniden hesapla. Saf fonksiyonlar + I/O main().

KULLANIM: python scripts/cleanup_z24.py        (dry-run, sadece rapor)
          python scripts/cleanup_z24.py --apply (yedek al + uygula)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AUDIT = Path("logs/audit")
_TRADES = _AUDIT / "trade_events.jsonl"
_EQUITY = _AUDIT / "equity_history.jsonl"


def remove_events(
    events: list[dict[str, Any]],
    full_slugs: set[str],
    episodes: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """full_slugs: tüm event'leri silinecek slug'lar.
    episodes: (slug, entry_timestamp) — o slug'da SADECE o episode silinir
    (entry'den kendi final'ine kadar).
    """
    ep_targets = {(s, t) for s, t in episodes}
    ep_slugs = {s for s, _ in episodes}
    out: list[dict[str, Any]] = []
    # episode silme: slug bazında entry geldikçe aktif episode'u izle
    dropping: dict[str, bool] = {}  # slug -> şu an silinen episode'un içinde miyiz
    for ev in events:
        slug = ev.get("slug") or ""
        if slug in full_slugs:
            continue
        if slug in ep_slugs:
            kind = ev.get("kind")
            if kind == "entry":
                dropping[slug] = (slug, ev.get("entry_timestamp")) in ep_targets
            if dropping.get(slug):
                if kind == "final":
                    dropping[slug] = False  # episode bitti; final de silinir, sonrakiler reset
                continue  # bu event (entry/partial/final) silinen episode'a ait → at
        out.append(ev)
    return out


def removed_events(
    events: list[dict[str, Any]],
    full_slugs: set[str],
    episodes: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Silinen event'lerin listesi (equity rebuild için)."""
    kept = remove_events(events, full_slugs, episodes)
    # kept referans-eşitliğiyle değil, indeks farkıyla bulunur
    kept_ids = []
    ki = 0
    removed = []
    for ev in events:
        if ki < len(kept) and ev is kept[ki]:
            ki += 1
        else:
            removed.append(ev)
    return removed


def rebuild_equity(
    snapshots: list[dict[str, Any]],
    removed: list[dict[str, Any]],
    initial_bankroll: float,
) -> list[dict[str, Any]]:
    """Her snapshot'ta silinen işlemlerin realized + invested izini çıkar.
    unrealized (titreme) DOKUNULMAZ. bankroll = kayıt - removed_realized_by(T)
    + removed_invested_open_at(T).
    """
    def _ts(ev: dict[str, Any], key: str) -> str:
        return ev.get(key) or ""

    out: list[dict[str, Any]] = []
    for snap in snapshots:
        T = snap.get("timestamp") or ""
        removed_realized = 0.0
        removed_invested = 0.0
        removed_open = 0
        for ev in removed:
            kind = ev.get("kind")
            if kind == "partial" and _ts(ev, "timestamp") <= T:
                removed_realized += float(ev.get("realized_pnl_usdc") or 0.0)
            elif kind == "final":
                if _ts(ev, "exit_timestamp") <= T:
                    removed_realized += float(ev.get("exit_pnl_usdc") or 0.0)
                # final'i olan episode: entry<=T<final → açık → invested kilitli
                ent = _ts(ev, "entry_timestamp")
                fin = _ts(ev, "exit_timestamp")
                if ent and ent <= T < fin:
                    removed_invested += float(ev.get("size_usdc") or 0.0)
                    removed_open += 1
        new = dict(snap)
        new["realized_pnl"] = round(float(snap.get("realized_pnl", 0.0)) - removed_realized, 6)
        new["bankroll"] = round(
            float(snap.get("bankroll", 0.0)) - removed_realized + removed_invested, 6
        )
        new["invested"] = round(float(snap.get("invested", 0.0)) - removed_invested, 6)
        new["open_positions"] = max(0, int(snap.get("open_positions", 0)) - removed_open)
        out.append(new)
    return out
```

> NOT: `size_usdc` ve `entry_timestamp` `final` event'inde yok — bunları rebuild'e
> verebilmek için `removed_events` çıktısındaki `final` event'lerine, aynı episode'un
> `entry` event'inden `size_usdc` + `entry_timestamp` zenginleştirilir (Task B2 main()
> bunu yapar; saf test'te elle verildi).

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/scripts/test_cleanup_z24.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/cleanup_z24.py tests/unit/scripts/test_cleanup_z24.py
git commit -m "feat(scripts): SPEC-Z24 temizlik saf fonksiyonları (remove_events + rebuild_equity)"
```

---

## Task B2: Script main() — yedek + uygula + doğrula

**Files:**
- Modify: `scripts/cleanup_z24.py` (main + episode zenginleştirme + I/O)

- [ ] **Step 1: main() ekle** (saf fonksiyonların altına)

```python
# Hedefler (spec onaylı):
FULL_REMOVE_SLUGS = {
    "atp-poling-ilagan-2026-06-06",                       # 1. giriş 0.77 + tekrar
    "wta-vekic-monnet-2026-06-06-set-handicap-home-1pt5",  # 0.79
    "wnba-wsh-atl-2026-06-06",                            # moneyline 0.81 (totals DEĞİL)
}
EPISODE_REMOVE = [
    ("wnba-ind-nyl-2026-06-06", "2026-06-07T00:59:07.768854+00:00"),  # 2. giriş (tekrar)
]


def _enrich_removed_finals(removed: list[dict], events: list[dict]) -> list[dict]:
    """removed final'lerine, aynı episode entry'sinden size_usdc + entry_timestamp ekle."""
    # episode entry'lerini sırayla eşle: her removed final'den önceki en yakın removed entry
    last_entry: dict = {}
    by_slug_entry: dict = {}
    out = []
    for ev in removed:
        slug = ev.get("slug") or ""
        if ev.get("kind") == "entry":
            by_slug_entry[slug] = ev
        if ev.get("kind") == "final":
            ent = by_slug_entry.get(slug, {})
            ev = {**ev, "size_usdc": ent.get("size_usdc"),
                  "entry_timestamp": ent.get("entry_timestamp")}
        out.append(ev)
    return out


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def main(apply: bool) -> None:
    events = _read_jsonl(_TRADES)
    snaps = _read_jsonl(_EQUITY)
    kept = remove_events(events, FULL_REMOVE_SLUGS, EPISODE_REMOVE)
    removed = _enrich_removed_finals(
        removed_events(events, FULL_REMOVE_SLUGS, EPISODE_REMOVE), events
    )
    new_snaps = rebuild_equity(snaps, removed, initial_bankroll=1000.0)

    old_realized = sum(float(e.get("exit_pnl_usdc") or 0.0) for e in events if e.get("kind") == "final") \
        + sum(float(e.get("realized_pnl_usdc") or 0.0) for e in events if e.get("kind") == "partial")
    new_realized = sum(float(e.get("exit_pnl_usdc") or 0.0) for e in kept if e.get("kind") == "final") \
        + sum(float(e.get("realized_pnl_usdc") or 0.0) for e in kept if e.get("kind") == "partial")

    print(f"events: {len(events)} -> {len(kept)} (silinen {len(events) - len(kept)})")
    print(f"realized PnL: {old_realized:.2f} -> {new_realized:.2f}")
    print(f"equity snapshots: {len(snaps)} (rebuild)")

    if not apply:
        print("DRY-RUN — değişiklik yazılmadı. Uygulamak için --apply.")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    _TRADES.rename(_TRADES.with_suffix(f".jsonl.bak.{ts}"))
    _EQUITY.rename(_EQUITY.with_suffix(f".jsonl.bak.{ts}"))
    _write_jsonl(_TRADES, kept)
    _write_jsonl(_EQUITY, new_snaps)
    print(f"YEDEK alındı (.bak.{ts}) + yeni dosyalar yazıldı.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
```

- [ ] **Step 2: DRY-RUN çalıştır + raporu incele**

Run: `python scripts/cleanup_z24.py`
Expected: "silinen" event sayısı > 0; realized PnL eski→yeni doğru yönde; HİÇBİR dosya değişmedi.

⚠️ **DURAK:** Rapordaki silinen event sayısı ve yeni realized toplamı beklenenle uyuşmuyorsa DUR, kullanıcıya sor. Uygulama (--apply) yalnız rapor doğrulandıktan sonra.

- [ ] **Step 3: Uygula (rapor onaylanınca)**

Run: `python scripts/cleanup_z24.py --apply`
Expected: ".bak.<ts>" yedekleri oluştu + yeni dosyalar yazıldı.

- [ ] **Step 4: Doğrula** — silinen işlemler artık defterde yok:

Run: `python -c "import json; [print(json.loads(l)['slug']) for l in open('logs/audit/trade_events.jsonl',encoding='utf-8') if 'poling-ilagan' in l or 'vekic-monnet' in l]"`
Expected: çıktı BOŞ (poling-ilagan + vekic-monnet kalmadı).

- [ ] **Step 5: Commit**

```bash
git add scripts/cleanup_z24.py
git commit -m "feat(scripts): SPEC-Z24 temizlik main() — yedek + apply + doğrula"
```

---

## Task B3: Dashboard'da görsel doğrulama + DECISIONS.md güncelle

- [ ] **Step 1:** Kullanıcıdan dashboard reload onayı iste (memory: reload SORMADAN yapılmaz). Onay gelirse `python scripts/reboot.py reload`.

- [ ] **Step 2:** Dashboard'da kontrol: basketbol kartı, realized PnL, exited sekmesi — 5 işlemin izi yok.

- [ ] **Step 3:** DECISIONS.md güncelle:
  - §B'ye **SPEC-Z24** girişi (tekrar-giriş yasağı kuralı + neden: ind-nyl falling-knife −$35).
  - §A'ya kısa kural notu.
  - SPEC.md/spec draft'ı temizle (kod+test bitti).

- [ ] **Step 4: Commit**

```bash
git add DECISIONS.md
git commit -m "docs: SPEC-Z24 tekrar-giriş yasağı + temizlik kaydı (DECISIONS)"
```

---

## Self-Review notları
- **Spec coverage:** İŞ A (guard+state+hook+rebuild) → A1-A4 ✓. İŞ B (5 işlem sil + equity rebuild + yedek + doğrula) → B1-B3 ✓.
- **Bilinen sınır:** equity unrealized "titreme" düzeltilmez (kullanıcı onayı). realized + bankroll + invested düzeltilir.
- **Risk:** B2 dosya yazımı yıkıcı → DRY-RUN + yedek + doğrulama zorunlu duraklarla korundu.
