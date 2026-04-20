# Exit Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise exited-tab card density to match the active card: entry odds %, PnL %, partial sell price, remaining %, humanized `exit_reason` with tone. Spec: [docs/superpowers/specs/2026-04-20-exit-card-redesign-design.md](../specs/2026-04-20-exit-card-redesign-design.md).

**Architecture:** One infrastructure change (`trade_logger.log_partial_exit()` gains a required `price` parameter), one orchestration call-site update (`exit_processor.py` passes `pos.current_price`), one presentation-computation change (`computed.py::exit_events()` enriches partial event dicts with `anchor_probability`, `partial_price`, `remaining_pct`), two new presentation helpers in `fmt.js` (`exitReasonLabel`, `durationShort`), and a rewrite of `feed.js::_exitedCard()`. No new files, no new directories, no domain changes.

**Tech Stack:** Python 3.12 (pytest for backend tests), vanilla JS (no JS test framework in repo — manual dashboard verification for frontend).

---

## Resolved Open Questions (from spec)

1. **`ExitSignal.price`** — does not exist and will NOT be added. `pos.current_price` is already used by `_log_exit_to_archive()` for the partial branch at [src/orchestration/exit_processor.py:161](../../src/orchestration/exit_processor.py#L161), so the same value feeds `log_partial_exit()`. Keeps `ExitSignal` minimal.
2. **`price` parameter on `log_partial_exit()`** — required (no default). There is exactly one live call site ([src/orchestration/exit_processor.py:133-139](../../src/orchestration/exit_processor.py#L133-L139)); no transition period needed. Legacy rows on disk stay as-is (frontend handles missing `price` with `@ —` fallback).

---

## File Touch Map

| File | Change |
|------|--------|
| `src/infrastructure/persistence/trade_logger.py` | `log_partial_exit()` signature + entry dict gains `"price"` |
| `src/orchestration/exit_processor.py` | `_execute_partial_exit()` passes `price=pos.current_price` |
| `src/presentation/dashboard/computed.py` | `exit_events()` partial branch enriched; cumulative `remaining_pct` |
| `src/presentation/dashboard/static/js/fmt.js` | Add `FMT.exitReasonLabel()` + `FMT.durationShort()` |
| `src/presentation/dashboard/static/js/feed.js` | Rewrite `_exitedCard()` |
| `tests/unit/infrastructure/persistence/test_trade_logger.py` | Update 3 existing tests; add 1 new (price persisted) |
| `tests/unit/orchestration/test_exit_processor.py` | Update `mock_log_partial` signature |
| `tests/unit/orchestration/test_agent_scale_out_log.py` | Add `price` kwarg assertion |
| `tests/unit/presentation/dashboard/test_computed.py` | Add `exit_events` partial enrichment tests |

---

## Task 1: `log_partial_exit()` gains required `price` parameter

**Files:**
- Modify: `src/infrastructure/persistence/trade_logger.py:142-159`
- Test: `tests/unit/infrastructure/persistence/test_trade_logger.py:213-271`

- [ ] **Step 1.1: Update existing 3 tests to pass `price` + add 1 new test**

Open `tests/unit/infrastructure/persistence/test_trade_logger.py` and replace the existing three partial-exit tests plus add a fourth. Replace lines 213-271 with:

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
        price=0.62,
    )
    assert ok is True

    records = logger.read_all()
    assert len(records) == 1
    assert records[0]["partial_exits"] == [
        {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
         "timestamp": "2026-04-15T01:00:00Z", "price": 0.62}
    ]


def test_log_partial_exit_appends_to_open_trade(tmp_path):
    """Partial exit acik trade record'una append edilir."""
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
                            realized_pnl_usdc=5.0, timestamp="t1",
                            price=0.62)
    records = logger.read_all()
    assert len(records[0]["partial_exits"]) == 1
    assert records[0]["partial_exits"][0]["tier"] == 1
    assert records[0]["partial_exits"][0]["sell_pct"] == 0.4
    assert records[0]["partial_exits"][0]["price"] == 0.62


def test_log_partial_exit_returns_false_if_no_open_record(tmp_path):
    """Eşleşen açık kayıt yoksa False döner, dosya değişmez."""
    from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
    logger = TradeHistoryLogger(str(tmp_path / "trades.jsonl"))
    ok = logger.log_partial_exit(
        condition_id="missing", tier=1, sell_pct=0.4,
        realized_pnl_usdc=5.0, timestamp="t1", price=0.62,
    )
    assert ok is False


def test_log_partial_exit_persists_price_field(tmp_path):
    """Partial exit kaydında 'price' alanı tam olarak korunur (yuvarlama yok)."""
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
    logger.log_partial_exit(condition_id="cid", tier=2, sell_pct=0.3,
                            realized_pnl_usdc=9.0, timestamp="t2",
                            price=0.7345)
    records = logger.read_all()
    assert records[0]["partial_exits"][0]["price"] == 0.7345
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v -k partial_exit`

Expected: FAIL — `log_partial_exit() got an unexpected keyword argument 'price'` (or TypeError equivalent), because the current signature does not accept `price`.

- [ ] **Step 1.3: Update `log_partial_exit()` to accept and persist `price`**

In `src/infrastructure/persistence/trade_logger.py`, replace lines 142-159 with:

```python
    def log_partial_exit(self, condition_id: str, tier: int, sell_pct: float,
                         realized_pnl_usdc: float, timestamp: str,
                         price: float) -> bool:
        """En son açık trade kaydının partial_exits listesine bir partial ekle.
        Atomic rewrite. Return: kayıt bulundu mu.
        """
        entry: dict[str, Any] = {
            "tier": tier,
            "sell_pct": sell_pct,
            "realized_pnl_usdc": realized_pnl_usdc,
            "timestamp": timestamp,
            "price": price,
        }

        def append_partial(rec: dict[str, Any]) -> None:
            existing = rec.get("partial_exits") or []
            existing.append(entry)
            rec["partial_exits"] = existing

        return self._rewrite_matching(condition_id, append_partial)
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `pytest tests/unit/infrastructure/persistence/test_trade_logger.py -v -k partial_exit`

Expected: PASS — 4 tests pass.

- [ ] **Step 1.5: Commit**

```bash
git add src/infrastructure/persistence/trade_logger.py tests/unit/infrastructure/persistence/test_trade_logger.py
git commit -m "feat(trade_logger): persist price on partial exit log"
```

---

## Task 2: `exit_processor._execute_partial_exit()` passes `price`

**Files:**
- Modify: `src/orchestration/exit_processor.py:133-139`
- Test: `tests/unit/orchestration/test_exit_processor.py:77-80`
- Test: `tests/unit/orchestration/test_agent_scale_out_log.py:53-73`

- [ ] **Step 2.1: Update `mock_log_partial` signature in `test_exit_processor.py`**

In `tests/unit/orchestration/test_exit_processor.py`, replace line 77-80 (the `mock_log_partial` definition and assignment) with:

```python
    def mock_log_partial(condition_id, tier, sell_pct, realized_pnl_usdc,
                         timestamp, price):
        recorder.calls.append("trade_logger_partial")
        return True
    deps.trade_logger.log_partial_exit.side_effect = mock_log_partial
```

- [ ] **Step 2.2: Add `price` kwarg assertion in `test_agent_scale_out_log.py`**

In `tests/unit/orchestration/test_agent_scale_out_log.py`, in `test_execute_partial_exit_calls_trade_logger_with_tier_and_pnl` (lines 53-73), after the existing `assert "timestamp" in kwargs` line, append:

```python
    # pos.current_price = 0.6 (see _make_deps_with_position), must be passed through
    assert "price" in kwargs
    assert abs(kwargs["price"] - 0.6) < 1e-9
```

The final test body becomes:

```python
def test_execute_partial_exit_calls_trade_logger_with_tier_and_pnl():
    """Scale-out partial exit'te trade_logger.log_partial_exit doğru argümanlarla çağrılır."""
    deps, pos = _make_deps_with_position()
    agent = Agent(deps)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT,
        partial=True,
        sell_pct=0.4,
        tier=1,
    )
    agent._exit._execute_exit(pos, signal)

    assert deps.trade_logger.log_partial_exit.called
    kwargs = deps.trade_logger.log_partial_exit.call_args.kwargs
    assert kwargs["condition_id"] == "cid"
    assert kwargs["tier"] == 1
    assert kwargs["sell_pct"] == 0.4
    # pos.unrealized_pnl_usdc * 0.4 — pozisyon entry 0.5, current 0.6, shares 200
    # unrealized = 200 * 0.6 - 100 = 20; partial = 20 * 0.4 = 8.0
    assert abs(kwargs["realized_pnl_usdc"] - 8.0) < 0.01
    assert "timestamp" in kwargs
    # pos.current_price = 0.6 (see _make_deps_with_position), must be passed through
    assert "price" in kwargs
    assert abs(kwargs["price"] - 0.6) < 1e-9
```

- [ ] **Step 2.3: Run tests to verify they fail**

Run:
```bash
pytest tests/unit/orchestration/test_agent_scale_out_log.py::test_execute_partial_exit_calls_trade_logger_with_tier_and_pnl -v
pytest tests/unit/orchestration/test_exit_processor.py -v -k partial
```

Expected: `test_execute_partial_exit_calls_trade_logger_with_tier_and_pnl` FAILS with `KeyError: 'price'` (the call site does not pass it yet). `test_exit_processor.py` partial tests may now fail because the mock expects 6 args but the production call passes 5.

- [ ] **Step 2.4: Update `_execute_partial_exit()` to pass `price=pos.current_price`**

In `src/orchestration/exit_processor.py`, replace lines 133-139 with:

```python
        # 1. Disk — trade_logger ÖNCE (crash-safe sıralama)
        partial_written = self.deps.trade_logger.log_partial_exit(
            condition_id=pos.condition_id,
            tier=tier,
            sell_pct=signal.sell_pct,
            realized_pnl_usdc=realized,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price=pos.current_price,
        )
```

- [ ] **Step 2.5: Run tests to verify they pass**

Run:
```bash
pytest tests/unit/orchestration/test_agent_scale_out_log.py -v
pytest tests/unit/orchestration/test_exit_processor.py -v
```

Expected: PASS — all tests in both files.

- [ ] **Step 2.6: Commit**

```bash
git add src/orchestration/exit_processor.py tests/unit/orchestration/test_exit_processor.py tests/unit/orchestration/test_agent_scale_out_log.py
git commit -m "feat(exit_processor): forward pos.current_price to partial exit log"
```

---

## Task 3: `computed.py::exit_events()` enrichment

**Files:**
- Modify: `src/presentation/dashboard/computed.py:131-159`
- Test: `tests/unit/presentation/dashboard/test_computed.py` (append at end of file)

- [ ] **Step 3.1: Write failing tests**

Append to `tests/unit/presentation/dashboard/test_computed.py`:

```python
# ── exit_events enrichment (2026-04-21 exit card redesign) ──

def test_exit_events_partial_carries_anchor_probability_and_price() -> None:
    trades = [{
        "slug": "x", "condition_id": "cid", "sport_tag": "mlb",
        "direction": "BUY_YES", "entry_price": 0.5,
        "entry_timestamp": "2026-04-15T00:00:00Z", "question": "Q?",
        "anchor_probability": 0.58,
        "partial_exits": [
            {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
             "timestamp": "2026-04-15T01:00:00Z", "price": 0.62},
        ],
        "exit_price": None,
    }]
    events = computed.exit_events(trades)
    assert len(events) == 1
    ev = events[0]
    assert ev["partial"] is True
    assert ev["anchor_probability"] == 0.58
    assert ev["partial_price"] == 0.62
    assert abs(ev["remaining_pct"] - 0.6) < 1e-9


def test_exit_events_partial_remaining_pct_is_cumulative() -> None:
    """İki partial — remaining ikinci event'te 1 − (0.40 + 0.30) = 0.30."""
    trades = [{
        "slug": "x", "condition_id": "cid", "sport_tag": "mlb",
        "direction": "BUY_YES", "entry_price": 0.5,
        "entry_timestamp": "2026-04-15T00:00:00Z", "question": "Q?",
        "anchor_probability": 0.58,
        "partial_exits": [
            {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
             "timestamp": "2026-04-15T01:00:00Z", "price": 0.62},
            {"tier": 2, "sell_pct": 0.3, "realized_pnl_usdc": 4.0,
             "timestamp": "2026-04-15T02:00:00Z", "price": 0.74},
        ],
        "exit_price": None,
    }]
    events = computed.exit_events(trades)
    # Sort order is descending by exit_timestamp — tier 2 (later) first
    assert events[0]["partial_price"] == 0.74
    assert abs(events[0]["remaining_pct"] - 0.3) < 1e-9
    assert events[1]["partial_price"] == 0.62
    assert abs(events[1]["remaining_pct"] - 0.6) < 1e-9


def test_exit_events_legacy_partial_without_price_is_none() -> None:
    """Legacy kayıtlarda 'price' yok — event partial_price = None taşır."""
    trades = [{
        "slug": "x", "condition_id": "cid", "sport_tag": "mlb",
        "direction": "BUY_YES", "entry_price": 0.5,
        "entry_timestamp": "2026-04-15T00:00:00Z", "question": "Q?",
        "anchor_probability": 0.58,
        "partial_exits": [
            {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
             "timestamp": "2026-04-15T01:00:00Z"},  # NO price
        ],
        "exit_price": None,
    }]
    events = computed.exit_events(trades)
    assert events[0]["partial_price"] is None
    assert abs(events[0]["remaining_pct"] - 0.6) < 1e-9


def test_exit_events_full_exit_has_remaining_pct_zero() -> None:
    trades = [{
        "slug": "x", "condition_id": "cid", "sport_tag": "mlb",
        "direction": "BUY_YES", "entry_price": 0.5,
        "entry_timestamp": "2026-04-15T00:00:00Z", "question": "Q?",
        "anchor_probability": 0.58,
        "partial_exits": [],
        "exit_price": 0.7, "exit_reason": "near_resolve",
        "exit_pnl_usdc": 20.0, "exit_timestamp": "2026-04-15T03:00:00Z",
    }]
    events = computed.exit_events(trades)
    assert len(events) == 1
    assert events[0]["partial"] is False
    assert events[0]["remaining_pct"] == 0.0
    assert events[0]["anchor_probability"] == 0.58
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `pytest tests/unit/presentation/dashboard/test_computed.py -v -k exit_events`

Expected: FAIL — `KeyError: 'anchor_probability'` / `'partial_price'` / `'remaining_pct'` on the partial branch; `'remaining_pct'` also missing on full branch.

- [ ] **Step 3.3: Enrich `exit_events()`**

In `src/presentation/dashboard/computed.py`, replace lines 131-159 with:

```python
def exit_events(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Full exit'ler + partial scale-out'ları tek liste olarak döner.

    Her full-close TradeRecord bir event, her partial_exit ayrı bir event.
    Partial event'lerde `remaining_pct` kümülatif — o event'e kadar satılan
    toplam oranın tümleyeni. Full event için `remaining_pct = 0.0`.
    Exited tab ve treemap aggregation source.
    """
    events: list[dict[str, Any]] = []
    for t in trades:
        cumulative_sell_pct = 0.0
        for pe in (t.get("partial_exits") or []):
            cumulative_sell_pct += float(pe.get("sell_pct") or 0.0)
            remaining = max(0.0, 1.0 - cumulative_sell_pct)
            events.append({
                "slug": t.get("slug", ""),
                "sport_tag": t.get("sport_tag", ""),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price"),
                "entry_timestamp": t.get("entry_timestamp", ""),
                "question": t.get("question", ""),
                "anchor_probability": t.get("anchor_probability"),
                "exit_price": None,
                "exit_pnl_usdc": pe.get("realized_pnl_usdc", 0.0),
                "exit_reason": f"scale_out_tier_{pe.get('tier', '?')}",
                "exit_timestamp": pe.get("timestamp", ""),
                "partial": True,
                "sell_pct": pe.get("sell_pct", 0.0),
                "partial_price": pe.get("price"),
                "remaining_pct": remaining,
            })
        if t.get("exit_price") is not None:
            ev = dict(t)
            ev["partial"] = False
            ev["remaining_pct"] = 0.0
            events.append(ev)
    events.sort(key=lambda e: e.get("exit_timestamp", ""), reverse=True)
    return events
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `pytest tests/unit/presentation/dashboard/test_computed.py -v`

Expected: PASS — all tests in file, including the 4 new exit_events tests.

- [ ] **Step 3.5: Commit**

```bash
git add src/presentation/dashboard/computed.py tests/unit/presentation/dashboard/test_computed.py
git commit -m "feat(computed): enrich exit_events with anchor/partial_price/remaining_pct"
```

---

## Task 4: `fmt.js` adds `exitReasonLabel` and `durationShort`

**Files:**
- Modify: `src/presentation/dashboard/static/js/fmt.js` (append helpers before `sideCode`)

No JS test framework in repo. Verification is manual via browser DevTools console.

- [ ] **Step 4.1: Add `FMT.exitReasonLabel()` helper**

In `src/presentation/dashboard/static/js/fmt.js`, inside the `FMT` object literal, immediately before the `sideCode(direction, slug)` method (line 203), insert:

```javascript
    // Raw exit_reason → { text, emoji, tone }. Tek kaynak — map burada yaşar.
    // tone ∈ { "pos", "neg", "neutral" } → CSS class seçimi.
    exitReasonLabel(raw) {
      const r = String(raw || "");
      if (!r) return { text: "", emoji: "", tone: "neutral" };
      // Scale-out: scale_out_tier_N → TP{N}
      const tp = r.match(/^scale_out_tier_(\d+)$/);
      if (tp) return { text: "TP" + tp[1], emoji: "🎯", tone: "pos" };
      // Stop loss: stop_loss_lN → SL L{N}
      const sl = r.match(/^stop_loss_l(\d+)$/);
      if (sl) return { text: "SL L" + sl[1], emoji: "🛑", tone: "neg" };
      // Score exit (sport-agnostic + home/away suffixes)
      if (r.startsWith("score_exit")) {
        if (r.endsWith("_home_goal")) return { text: "Score against (home)", emoji: "⚠️", tone: "neg" };
        if (r.endsWith("_away_goal")) return { text: "Score against (away)", emoji: "⚠️", tone: "neg" };
        return { text: "Score against", emoji: "⚠️", tone: "neg" };
      }
      if (r === "market_flip") return { text: "Market flipped", emoji: "🔄", tone: "neg" };
      if (r === "time_exit") return { text: "Time exit", emoji: "⏱", tone: "neutral" };
      if (r === "directional_reversal") return { text: "Direction reversed", emoji: "↩️", tone: "neg" };
      if (r === "manual_override") return { text: "Manual", emoji: "👤", tone: "neutral" };
      // Fallback — raw string, neutral
      return { text: r, emoji: "", tone: "neutral" };
    },
    // ms → "Xh Ym" / "Xm" / "Xs" (truncate, do not round up).
    durationShort(ms) {
      if (ms === null || ms === undefined || isNaN(ms) || ms < 0) return "";
      const totalSec = Math.floor(ms / 1000);
      if (totalSec < 60) return totalSec + "s";
      const totalMin = Math.floor(totalSec / 60);
      if (totalMin < 60) return totalMin + "m";
      const h = Math.floor(totalMin / 60);
      const m = totalMin % 60;
      return h + "h " + m + "m";
    },
```

- [ ] **Step 4.2: Manual verification in browser DevTools**

Start the dashboard (user runs bot + dashboard as usual — the plan does not prescribe the startup command) and open the dashboard page. In the browser DevTools console, run:

```javascript
FMT.exitReasonLabel("scale_out_tier_2")
// Expected: { text: "TP2", emoji: "🎯", tone: "pos" }

FMT.exitReasonLabel("stop_loss_l5")
// Expected: { text: "SL L5", emoji: "🛑", tone: "neg" }

FMT.exitReasonLabel("score_exit_home_goal")
// Expected: { text: "Score against (home)", emoji: "⚠️", tone: "neg" }

FMT.exitReasonLabel("score_exit_period_flip")
// Expected: { text: "Score against", emoji: "⚠️", tone: "neg" }

FMT.exitReasonLabel("market_flip")
// Expected: { text: "Market flipped", emoji: "🔄", tone: "neg" }

FMT.exitReasonLabel("unknown_reason_xyz")
// Expected: { text: "unknown_reason_xyz", emoji: "", tone: "neutral" }

FMT.durationShort(135 * 60 * 1000)  // Expected: "2h 15m"
FMT.durationShort(45 * 60 * 1000)   // Expected: "45m"
FMT.durationShort(30 * 1000)        // Expected: "30s"
FMT.durationShort(0)                // Expected: "0s"
FMT.durationShort(null)             // Expected: ""
```

All outputs must match. If any mismatch, fix in `fmt.js` and re-verify.

- [ ] **Step 4.3: Commit**

```bash
git add src/presentation/dashboard/static/js/fmt.js
git commit -m "feat(fmt.js): add exitReasonLabel and durationShort helpers"
```

---

## Task 5: Rewrite `feed.js::_exitedCard()`

**Files:**
- Modify: `src/presentation/dashboard/static/js/feed.js:168-199`

- [ ] **Step 5.1: Rewrite `_exitedCard(t)`**

In `src/presentation/dashboard/static/js/feed.js`, replace lines 168-199 (the entire `_exitedCard(t)` method including the trailing comma) with:

```javascript
    _exitedCard(t) {
      const icon = ICONS.getSportEmoji(t.sport_tag, t.slug);
      const dir = FMT.sideCode(t.direction, t.slug);
      const dirCls = t.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      const pnl = Number(t.exit_pnl_usdc || 0);
      const isPartial = !!t.partial;

      // Invested notional: partial'da orijinal tutarın payı, full'de tam size.
      // (t.size_usdc = pozisyonun entry'deki tutarı — TradeRecord'dan gelir.)
      const invested = isPartial
        ? Number(t.size_usdc || 0) * Number(t.sell_pct || 0)
        : Number(t.size_usdc || 0);
      const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;

      // Odds %: direction-adjusted render. anchor_probability = P(YES).
      const anchor = t.anchor_probability;
      const oddsStr = (anchor === null || anchor === undefined)
        ? ""
        : `Odds ${((t.direction === "BUY_NO" ? (1 - anchor) : anchor) * 100).toFixed(1)}%`;

      // Exit fiyat hücresi:
      //   Full:     "Entry XX¢ → Exit YY¢"
      //   Partial+price: "Entry XX¢ → @ YY¢"
      //   Partial legacy (price yok): "Entry XX¢ → @ —"
      const exitPriceStr = isPartial
        ? (t.partial_price !== null && t.partial_price !== undefined
            ? `@ ${FMT.cents(t.partial_price)}`
            : "@ —")
        : `Exit ${FMT.cents(t.exit_price || 0)}`;

      // Remaining — partial'da gösterilir. "Remaining 60%" gibi.
      const remainingStr = isPartial
        ? `· Remaining ${Math.round((t.remaining_pct || 0) * 100)}%`
        : "";

      // Held — full exit'te gösterilir (pozisyon hâlâ açık değil).
      let heldPrefix = "";
      if (!isPartial && t.entry_timestamp && t.exit_timestamp) {
        const heldMs = new Date(t.exit_timestamp).getTime()
          - new Date(t.entry_timestamp).getTime();
        const held = FMT.durationShort(heldMs);
        if (held) heldPrefix = `Held ${held} · `;
      }

      // Humanized reason + tone class.
      const label = FMT.exitReasonLabel(t.exit_reason);
      const toneCls = label.tone === "pos"
        ? "feed-pnl-pos"
        : label.tone === "neg" ? "feed-pnl-neg" : "";
      const reasonText = label.emoji
        ? `${label.emoji} ${FMT.escapeHtml(label.text)}`
        : FMT.escapeHtml(label.text);

      const partialBadge = isPartial
        ? `<span class="feed-badge badge-partial">PARTIAL</span>`
        : "";

      return `${this._cardOpen(t.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            ${this._marketTitle(t.question, t.slug)}</div>
          ${partialBadge}<span class="feed-badge ${dirCls}">${dir}</span>
        </div>
        <div class="feed-details">
          <span>Entry ${FMT.cents(t.entry_price)} &nbsp;→&nbsp; ${exitPriceStr}</span>
          <span>${oddsStr}</span>
        </div>
        <div class="feed-impact">
          <span class="${FMT.pnlClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
          <span class="feed-pnl-pct ${FMT.pnlClass(pnl)}">(${FMT.pctSigned(pnlPct, 0)})</span>
          ${remainingStr ? `<span class="feed-remaining">${remainingStr}</span>` : ""}
        </div>
        <div class="feed-exit-reason-row ${toneCls}">${reasonText}</div>
        <div class="feed-time">
          <span>${heldPrefix}${FMT.relTime(t.exit_timestamp)}</span>
          <span>${t.final_outcome || ""}</span>
        </div>
      </a>`;
    },
```

- [ ] **Step 5.2: Manual verification — full-win scenario**

Start the dashboard. Open the "Exited" tab. Find a full-exit trade with positive PnL (or wait for one / reboot to a known log with one).

Expected card layout:
```
[icon] [teams]                            [dir]
Entry XX¢  →  Exit YY¢              Odds ZZ.Z%
+$A.BC  (+N%)
🎯 TP{n}   or   ⚠️ Score against   (tone colour applied)
Held {dur} · {relTime}                       W
```

Verify:
- `Odds` column is present and matches `anchor_probability` (direction-adjusted for BUY_NO).
- PnL % is rendered in parentheses next to `$` amount.
- Reason row shows humanized text with emoji; colour matches tone (green for TP, red for score / SL / flip).
- `Held` prefix present on full exits.

- [ ] **Step 5.3: Manual verification — partial scenario (new partial, with price)**

Trigger or wait for a new scale-out (or inject one via the test harness the owner usually uses). Find it in the Exited tab.

Expected:
- `@ {price}¢` in the exit cell.
- `· Remaining {pct}%` rendered in the impact row.
- `Held` prefix **absent** (position still open).
- `PARTIAL` badge rendered.

- [ ] **Step 5.4: Manual verification — legacy partial (price missing)**

Locate an old partial-exit event in `logs/trade_history.jsonl` that does not carry `price` (any pre-this-feature partial). Dashboard card for it must render `@ —` in the exit cell, no crash, remaining % still computed.

If no legacy partial exists locally, simulate one by editing a fresh row in `logs/trade_history.jsonl`: delete the `"price"` key from one `partial_exits[]` entry, refresh the dashboard, verify `@ —` renders.

**If simulating, restore the file afterwards** (or accept the edit — the owner's call; ask if unsure).

- [ ] **Step 5.5: Manual verification — negative exit (tone colour)**

Find or simulate a full exit with negative PnL AND a negative-tone reason (`score_exit_*`, `stop_loss_*`, `market_flip`). Card must render:
- `$` and `%` both in the negative colour (existing `.feed-pnl-neg`).
- Reason row also in the negative colour (`feed-pnl-neg` applied via `toneCls`).

- [ ] **Step 5.6: Commit**

```bash
git add src/presentation/dashboard/static/js/feed.js
git commit -m "feat(feed.js): redesign exit card — odds, pnl %, partial price, remaining, humanized reason"
```

---

## Task 6: Full regression pass

- [ ] **Step 6.1: Full backend test suite**

Run: `pytest -q`

Expected: All tests pass. If any test unrelated to this feature fails, stop and report — do not proceed with the rest.

- [ ] **Step 6.2: Dashboard smoke test — all tabs still work**

Open dashboard. Click each tab: Active, Exited, Skipped, Stock. Each renders cards without JS errors in the console.

- [ ] **Step 6.3: No layer violations**

Run: `pytest tests/unit/presentation/dashboard/test_computed.py::test_computed_module_has_no_layer_imports -v`

Expected: PASS. (Validates the `computed.py` changes did not introduce a forbidden import.)

- [ ] **Step 6.4: Commit marker (optional — only if a follow-up fix was needed)**

If Steps 6.1–6.3 all pass on the first try, no commit is needed — the feature is complete with the Task 1–5 commits. If a fix was required, commit it now:

```bash
git add <fixed files>
git commit -m "fix(exit-card): <specific follow-up>"
```

---

## Out of Scope (explicit)

- Confidence pill / entry-reason tag on exit card (owner rejected during brainstorming).
- Peak unrealized PnL, match-state-at-exit (deferred — no persisted state).
- CSS palette changes. The plan reuses `.feed-pnl-pos` / `.feed-pnl-neg` for tone. If the owner later wants distinct reason-row colours, that is a new spec.
- Migration / backfill of legacy `partial_exits[]` entries without `price`.
- JS unit testing infrastructure (repo has none; adding one is a separate initiative).
