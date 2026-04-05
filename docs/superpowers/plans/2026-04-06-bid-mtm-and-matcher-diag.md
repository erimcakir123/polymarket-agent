# Bid-Side MTM Display + Matcher Diagnostic Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Display realized close value (best-bid) on dashboard so PnL shown matches what user would receive if closing now; (2) Produce a written diagnostic report on why only ~25% of scout-queue entries in the 2h window match Polymarket markets.

**Architecture:**
- Part 1 adds a new `Position.bid_price` field populated by the WS feed; `current_price` (stored as ask) stays untouched so stop-loss/trailing-TP/match-exit logic is unchanged. Dashboard reads `bid_price` for display and falls back to `current_price` on old snapshots.
- Part 2 is a read-only analysis. Loads `logs/scout_queue.json`, fetches Polymarket markets in the 2h window, runs the existing matcher, and writes a report enumerating every unmatched pair with a failure classification.

**Tech Stack:** Python 3.11, Pydantic v2, Flask dashboard (vanilla JS), pytest, requests.

**Scope boundary:** Any matcher *patch* that comes out of the Part 2 diagnostic is a separate plan. This plan produces only the report.

---

## File Structure

**Part 1 — Bid-side MTM**

| File | Change type | Responsibility |
|---|---|---|
| `src/models.py` | modify (line 105 area) | Add `bid_price: float = 0.0` to Position |
| `src/websocket_feed.py` | modify (3 handlers + callback type) | Pass bid alongside ask to callback |
| `src/exit_monitor.py` | modify (`_on_ws_price_update` + `process_ws_ticks`) | Accept bid, store on Position |
| `templates/dashboard.html` | modify (`renderActivePositions`) | Prefer `bid_price` when computing card PnL |
| `tests/test_bid_mtm.py` | create | Unit tests for new field and dashboard PnL computation |

**Part 2 — Matcher diagnostic**

| File | Change type | Responsibility |
|---|---|---|
| `scripts/diagnose_matcher.py` | create | Standalone script that loads scout queue + fetches current Polymarket markets + reports failures |
| `docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md` | create (written by the script run) | Output report with numbered failure cases |

No other files change. No config changes. No schema migrations.

---

## Invariants preserved

- `pos.current_price` continues to be the ASK-side fill price (what we paid). All exit logic (`stop_loss_helper.compute_stop_loss_pct`, `trailing_tp.calculate_trailing_tp`, `match_exit.check_match_exit`, `a_conf_hold`, `catastrophic_floor`, `consensus_thesis`) reads this field unchanged.
- `Position.unrealized_pnl_usdc` / `unrealized_pnl_pct` computed properties are UNTOUCHED. They continue to mark-to-market on `current_price`.
- Exit logs, trade log PnL, portfolio.realized_pnl all unchanged.
- Dashboard is the only consumer that reads `bid_price` for display.
- Backward compatible: a Position loaded from an old `positions.json` without `bid_price` defaults to `0.0`, and the dashboard falls back to `current_price`.

---

## Part 1: Bid-Side MTM

### Task 1: Add `bid_price` field to `Position` model

**Files:**
- Modify: `src/models.py` (line 105 area, inside Position class scale-out fields block)
- Test: `tests/test_bid_mtm.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bid_mtm.py`:

```python
"""Tests for bid-side mark-to-market display fix.

Ensures:
  1. Position exposes a new `bid_price` field that defaults to 0.0.
  2. Legacy positions.json (missing the field) round-trip correctly.
  3. The existing unrealized_pnl_* properties keep using current_price.
"""
from __future__ import annotations

from src.models import Position


def _make_pos(**overrides) -> Position:
    defaults = dict(
        condition_id="0xabc",
        token_id="1",
        direction="BUY_YES",
        entry_price=0.50,
        size_usdc=100.0,
        shares=200.0,
        current_price=0.50,
        ai_probability=0.55,
    )
    defaults.update(overrides)
    return Position(**defaults)


def test_bid_price_defaults_to_zero():
    pos = _make_pos()
    assert hasattr(pos, "bid_price")
    assert pos.bid_price == 0.0


def test_legacy_position_roundtrip_missing_bid():
    """A dict saved before this field existed must still load cleanly."""
    legacy = {
        "condition_id": "0xabc",
        "token_id": "1",
        "direction": "BUY_YES",
        "entry_price": 0.50,
        "size_usdc": 100.0,
        "shares": 200.0,
        "current_price": 0.50,
        "ai_probability": 0.55,
    }
    pos = Position.model_validate(legacy)
    assert pos.bid_price == 0.0


def test_unrealized_pnl_uses_current_price_not_bid():
    """bid_price must NOT leak into exit-facing unrealized_pnl_usdc."""
    pos = _make_pos(current_price=0.60, bid_price=0.40)
    # current_price=0.60 → current_value = 200 * 0.60 = 120 → PnL = +20
    assert round(pos.unrealized_pnl_usdc, 4) == 20.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_bid_mtm.py -v`
Expected: `test_bid_price_defaults_to_zero` and `test_legacy_position_roundtrip_missing_bid` FAIL with `AttributeError: 'Position' object has no attribute 'bid_price'` or `ValidationError`. `test_unrealized_pnl_uses_current_price_not_bid` will also fail for the same reason.

- [ ] **Step 3: Add the field to Position**

In `src/models.py`, locate the scale-out fields block near line 105:

```python
    # Scale Out fields (v2)
    original_shares: float | None = None
    original_size_usdc: float | None = None
    partial_exits: list[dict] = []
    scale_out_tier: int = 0
    scale_out_realized_usdc: float = 0.0  # Cumulative realized PnL from scale-outs (for dashboard net display)
```

Add a new dashboard-display field immediately after `scale_out_realized_usdc`:

```python
    # Scale Out fields (v2)
    original_shares: float | None = None
    original_size_usdc: float | None = None
    partial_exits: list[dict] = []
    scale_out_tier: int = 0
    scale_out_realized_usdc: float = 0.0  # Cumulative realized PnL from scale-outs (for dashboard net display)
    # Dashboard-only: live best-bid for mark-to-market display. DO NOT read in exit
    # logic — always use current_price (which is ask-side) for SL/TP/match exits.
    # 0.0 means "no WS tick received yet" (falls back to current_price in the UI).
    bid_price: float = 0.0
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest tests/test_bid_mtm.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Run the existing suite to verify no regression**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py -q`
Expected: 154 passed (151 existing + 3 new).

- [ ] **Step 6: Commit**

```bash
git add src/models.py tests/test_bid_mtm.py
git commit -m "feat(models): add Position.bid_price for dashboard MTM display"
```

---

### Task 2: Extend WebSocketFeed callback to pass bid

**Files:**
- Modify: `src/websocket_feed.py` (lines 48, 257, `_handle_book_event`, `_handle_price_change_event`, `_handle_best_bid_ask_event`, `_fire_callback`)
- Test: `tests/test_bid_mtm.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bid_mtm.py`:

```python
def test_ws_feed_fires_callback_with_bid():
    """_handle_book_event must pass best_bid to the registered callback."""
    from src.websocket_feed import WebSocketFeed

    captured: list[tuple] = []
    def cb(asset_id: str, yes_price: float, bid_price: float, ts: float) -> None:
        captured.append((asset_id, yes_price, bid_price, ts))

    feed = WebSocketFeed(on_price_update=cb)
    feed._subscriptions = {"asset-123"}  # Seed subscription so handler accepts

    feed._handle_book_event({
        "asset_id": "asset-123",
        "bids": [{"price": "0.01", "size": "100"}, {"price": "0.74", "size": "50"}],
        "asks": [{"price": "0.99", "size": "100"}, {"price": "0.75", "size": "50"}],
    })

    assert len(captured) == 1
    asset_id, yes_price, bid_price, _ts = captured[0]
    assert asset_id == "asset-123"
    assert yes_price == 0.75   # best_ask (asks[-1])
    assert bid_price == 0.74   # best_bid (bids[-1])


def test_ws_feed_price_change_callback_bid():
    """_handle_price_change_event must forward best_bid from price_changes[]."""
    from src.websocket_feed import WebSocketFeed

    captured: list[tuple] = []
    def cb(asset_id: str, yes_price: float, bid_price: float, ts: float) -> None:
        captured.append((asset_id, yes_price, bid_price, ts))

    feed = WebSocketFeed(on_price_update=cb)
    feed._subscriptions = {"asset-xyz"}

    feed._handle_price_change_event({
        "price_changes": [
            {"asset_id": "asset-xyz", "best_bid": "0.41", "best_ask": "0.42"},
        ],
    })

    assert len(captured) == 1
    assert captured[0][1] == 0.42  # yes_price = best_ask
    assert captured[0][2] == 0.41  # bid_price
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bid_mtm.py::test_ws_feed_fires_callback_with_bid tests/test_bid_mtm.py::test_ws_feed_price_change_callback_bid -v`
Expected: both FAIL with `TypeError: cb() takes 3 positional arguments but 4 were given` (current callback signature is `(token_id, yes_price, ts)`).

- [ ] **Step 3: Update callback type alias**

In `src/websocket_feed.py` line 48, change:

```python
PriceCallback = Callable[[str, float, float], None]  # token_id, yes_price, timestamp
```

to:

```python
PriceCallback = Callable[[str, float, float, float], None]  # token_id, yes_price, bid_price, timestamp
```

- [ ] **Step 4: Update `_fire_callback` to accept and forward bid**

Locate `_fire_callback` (around line 425 — search for `def _fire_callback`):

```python
    def _fire_callback(self, asset_id: str, yes_price: float, ts: float) -> None:
        """Invoke the registered price callback outside any lock."""
        if self._callback:
            try:
                self._callback(asset_id, yes_price, ts)
            except Exception as e:
                logger.debug("Price callback error: %s", e)
```

Replace with:

```python
    def _fire_callback(self, asset_id: str, yes_price: float, bid_price: float, ts: float) -> None:
        """Invoke the registered price callback outside any lock.

        Passes best-bid alongside best-ask so callers can distinguish the
        fill price (ask, used by exit logic) from the realizable close value
        (bid, used by dashboard MTM).
        """
        if self._callback:
            try:
                self._callback(asset_id, yes_price, bid_price, ts)
            except Exception as e:
                logger.debug("Price callback error: %s", e)
```

- [ ] **Step 5: Update three `_fire_callback` call sites**

Search the file for `self._fire_callback(` — there should be exactly three call sites inside the three event handlers. Each currently passes `(asset_id, yes_price, now)`. Change each to `(asset_id, yes_price, best_bid, now)`:

**In `_handle_book_event`** (around line 333):
```python
        self._fire_callback(asset_id, yes_price, best_bid, now)
```

**In `_handle_price_change_event`** (around line 366):
```python
            self._fire_callback(asset_id, yes_price, best_bid, now)
```

**In `_handle_best_bid_ask_event`** (around line 389):
```python
        self._fire_callback(asset_id, yes_price, best_bid, now)
```

(Each of these functions already has `best_bid` in local scope — no new variables.)

- [ ] **Step 6: Run the new tests and verify they pass**

Run: `python -m pytest tests/test_bid_mtm.py -v`
Expected: all 5 tests (3 from Task 1 + 2 new) PASS.

- [ ] **Step 7: Run the existing suite**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py -q`
Expected: 156 passed (151 existing + 5 new).

- [ ] **Step 8: Commit**

```bash
git add src/websocket_feed.py tests/test_bid_mtm.py
git commit -m "feat(ws): pass best_bid to price callback (dashboard MTM support)"
```

---

### Task 3: ExitMonitor propagates bid to Position

**Files:**
- Modify: `src/exit_monitor.py` (lines 70-72 `_on_ws_price_update`, line 49 `_ws_tick_queue`, lines 80-115 `process_ws_ticks`)
- Test: `tests/test_bid_mtm.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bid_mtm.py`:

```python
def test_exit_monitor_stores_bid_on_position():
    """Ticks arriving via _on_ws_price_update must populate pos.bid_price
    when process_ws_ticks drains the queue."""
    from unittest.mock import MagicMock
    from src.exit_monitor import ExitMonitor
    from src.models import Position
    from src.websocket_feed import WebSocketFeed

    pos = _make_pos(token_id="TOK-1", direction="BUY_YES")
    portfolio = MagicMock()
    portfolio.positions = {"0xabc": pos}

    config = MagicMock()
    config.risk.stop_loss_pct = 0.30
    config.trailing_tp.enabled = False
    config.trailing_tp.activation_pct = 0.20
    config.trailing_tp.trail_distance = 0.15

    ws = WebSocketFeed()
    em = ExitMonitor(portfolio, ws, config)

    # Simulate a WS tick: yes_price=0.60 (ask), bid=0.58
    em._on_ws_price_update("TOK-1", 0.60, 0.58, 1_700_000_000.0)
    em.process_ws_ticks()

    assert pos.current_price == 0.60   # ask-side, exit logic sees this
    assert pos.bid_price == 0.58       # bid-side, dashboard sees this


def test_exit_monitor_bid_inverted_for_buy_no():
    """For BUY_NO positions we store YES-side prices. A NO-token tick
    arriving with (ask=0.70, bid=0.69) means the YES token's implied
    ask=0.31, bid=0.30. Position must store YES-side values so dashboard
    displays the NO-side correctly via effective_price()."""
    from unittest.mock import MagicMock
    from src.exit_monitor import ExitMonitor
    from src.models import Position
    from src.websocket_feed import WebSocketFeed

    pos = _make_pos(token_id="TOK-NO", direction="BUY_NO",
                    entry_price=0.30, current_price=0.30)
    portfolio = MagicMock()
    portfolio.positions = {"0xabc": pos}
    config = MagicMock()
    config.risk.stop_loss_pct = 0.30
    config.trailing_tp.enabled = False
    config.trailing_tp.activation_pct = 0.20
    config.trailing_tp.trail_distance = 0.15

    ws = WebSocketFeed()
    em = ExitMonitor(portfolio, ws, config)

    # NO token: ask=0.70, bid=0.69 (market in our favour)
    em._on_ws_price_update("TOK-NO", 0.70, 0.69, 1_700_000_000.0)
    em.process_ws_ticks()

    # Stored YES-side: current_price=1-0.70=0.30, bid_price=1-0.69=0.31
    assert round(pos.current_price, 4) == 0.30
    assert round(pos.bid_price, 4) == 0.31
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bid_mtm.py::test_exit_monitor_stores_bid_on_position tests/test_bid_mtm.py::test_exit_monitor_bid_inverted_for_buy_no -v`
Expected: both FAIL with `TypeError: _on_ws_price_update() takes 4 positional arguments but 5 were given` (current signature is `(self, token_id, price, ts)`).

- [ ] **Step 3: Widen the tick queue type and update `_on_ws_price_update`**

In `src/exit_monitor.py` around line 49, change:

```python
        self._ws_tick_queue: queue.SimpleQueue[tuple[str, float, float]] = queue.SimpleQueue()
```

to:

```python
        # (token_id, yes_price_ask, bid_price, timestamp)
        self._ws_tick_queue: queue.SimpleQueue[tuple[str, float, float, float]] = queue.SimpleQueue()
```

Then around line 70 change `_on_ws_price_update`:

```python
    def _on_ws_price_update(self, token_id: str, price: float, ts: float) -> None:
        """Called from WS thread -- only enqueues, never mutates shared state."""
        self._ws_tick_queue.put_nowait((token_id, price, ts))
```

to:

```python
    def _on_ws_price_update(self, token_id: str, price: float, bid_price: float, ts: float) -> None:
        """Called from WS thread -- only enqueues, never mutates shared state.

        `price` is the token-side best-ask (fill price); `bid_price` is the
        token-side best-bid (realizable close value). Both are enqueued so
        the main thread can store them on the Position atomically.
        """
        self._ws_tick_queue.put_nowait((token_id, price, bid_price, ts))
```

- [ ] **Step 4: Update `process_ws_ticks` to unpack bid and store it on Position**

Locate the drain loop inside `process_ws_ticks` (around line 83-102):

```python
            while not self._ws_tick_queue.empty():
                try:
                    token_id, price, ts = self._ws_tick_queue.get_nowait()
                except queue.Empty:
                    break

                # Find matching position by token_id
                # Snapshot positions to avoid RuntimeError if the main thread
                # adds/removes a position concurrently during entry/exit.
                cid_found: str | None = None
                pos_found = None
                for cid, pos in list(self.portfolio.positions.items()):
                    if pos.token_id == token_id:
                        # WS sends token-side price; convert BUY_NO to YES-side
                        # so all downstream code (PnL, SL, TP) sees consistent prices
                        pos.current_price = (1.0 - price) if pos.direction == "BUY_NO" else price
                        cid_found = cid
                        pos_found = pos
                        _ticks_processed += 1
                        break
```

Replace with:

```python
            while not self._ws_tick_queue.empty():
                try:
                    token_id, price, bid_price, ts = self._ws_tick_queue.get_nowait()
                except queue.Empty:
                    break

                # Find matching position by token_id
                # Snapshot positions to avoid RuntimeError if the main thread
                # adds/removes a position concurrently during entry/exit.
                cid_found: str | None = None
                pos_found = None
                for cid, pos in list(self.portfolio.positions.items()):
                    if pos.token_id == token_id:
                        # WS sends token-side prices; convert BUY_NO to YES-side
                        # so all downstream code (PnL, SL, TP) sees consistent prices.
                        # current_price stays ASK-side (drives exit logic);
                        # bid_price is stored so the dashboard can display the
                        # realizable close value without spread-wide false losses.
                        if pos.direction == "BUY_NO":
                            pos.current_price = 1.0 - price
                            # For BUY_NO the NO-token's bid maps to (1 - bid) on the
                            # YES-side. Dashboard re-applies effective_price(),
                            # so we store YES-side consistently with current_price.
                            pos.bid_price = 1.0 - bid_price if bid_price > 0 else 0.0
                        else:
                            pos.current_price = price
                            pos.bid_price = bid_price
                        cid_found = cid
                        pos_found = pos
                        _ticks_processed += 1
                        break
```

- [ ] **Step 5: Run the new tests and verify they pass**

Run: `python -m pytest tests/test_bid_mtm.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 6: Run the existing suite to verify no regression**

Run: `python -m pytest tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py tests/test_bid_mtm.py -q`
Expected: 158 passed (151 existing + 7 new).

- [ ] **Step 7: Import smoke test**

Run: `python -c "from src.agent import Agent; from src.exit_monitor import ExitMonitor; from src.websocket_feed import WebSocketFeed; print('ok')"`
Expected: `ok`.

- [ ] **Step 8: Commit**

```bash
git add src/exit_monitor.py tests/test_bid_mtm.py
git commit -m "feat(exit_monitor): store bid_price on Position from WS ticks"
```

---

### Task 4: Dashboard displays bid-side PnL

**Files:**
- Modify: `templates/dashboard.html` (`renderActivePositions` — the computation of `pnlUsdc`/`pnlPct` per active card)

- [ ] **Step 1: Locate the active-card PnL computation**

Open `templates/dashboard.html` and search for `renderActivePositions` (around line 1918). Inside the `.map(p => { ... })` that builds each active card, find the two lines near line 1954:

```javascript
                const pnlUsdc = p.unrealized_pnl_usdc || 0;
                const pnlPct = p.unrealized_pnl_pct || 0;
```

These read the Pydantic computed fields which are marked-to-ask.

- [ ] **Step 2: Replace with bid-aware computation**

Replace those two lines with:

```javascript
                // Mark-to-market using the realizable close price (best-bid)
                // so the card shows what the user would actually receive if
                // closing the position now. Falls back to current_price for
                // legacy snapshots that predate bid_price (value 0 = no WS
                // tick yet). Exit logic is unaffected — it reads
                // unrealized_pnl_usdc which uses current_price (ask-side).
                const _hasBid = (p.bid_price || 0) > 0;
                const _markPrice = _hasBid ? p.bid_price : (p.current_price || 0);
                const _effMark = (p.direction === 'BUY_NO')
                    ? (1 - _markPrice)
                    : _markPrice;
                const _currentValue = (p.shares || 0) * _effMark;
                const _sizeUsdc = p.size_usdc || 0;
                const pnlUsdc = _currentValue - _sizeUsdc;
                const pnlPct = _sizeUsdc > 0 ? (pnlUsdc / _sizeUsdc) : 0;
```

(Everything downstream that reads `pnlUsdc` and `pnlPct` continues to work — `pnlNeutral`, `pnlColor`, the impact bar, the scale-out badge, the display string — all untouched.)

- [ ] **Step 3: Update the Entry/Now price display on the card to show the bid**

Slightly above the PnL block, around line 1996-1998, find:

```javascript
                const priceInfo = currentPrice > 0
                    ? `<span>Entry: ${(entryPrice*100).toFixed(0)}%</span><span style="opacity:0.6">→</span><span>Now: ${(currentPrice*100).toFixed(0)}%</span>`
                    : `<span>Entry: ${(entryPrice*100).toFixed(0)}%</span><span style="opacity:0.5">Awaiting price</span>`;
```

`currentPrice` here is already a direction-effective YES/NO-side value. We want "Now" to reflect the realizable close price so it stays consistent with the PnL above. Add a derived value above this block:

```javascript
                // Prefer bid-side for "Now" display so it matches the bid-MTM PnL below.
                const _nowRaw = _hasBid ? p.bid_price : (p.current_price || 0);
                const nowPrice = (p.direction === 'BUY_NO' || p.direction === 'SELL_YES')
                    ? (1 - _nowRaw)
                    : _nowRaw;
                const priceInfo = nowPrice > 0
                    ? `<span>Entry: ${(entryPrice*100).toFixed(0)}%</span><span style="opacity:0.6">→</span><span>Now: ${(nowPrice*100).toFixed(0)}%</span>`
                    : `<span>Entry: ${(entryPrice*100).toFixed(0)}%</span><span style="opacity:0.5">Awaiting price</span>`;
```

Also find the second `<span>Now: ...</span>` inside the feed-details block (around line 2025):

```javascript
                        <span>Now: ${currentPrice > 0 ? (currentPrice*100).toFixed(0)+'%' : '—'}</span>
```

Replace with:

```javascript
                        <span>Now: ${nowPrice > 0 ? (nowPrice*100).toFixed(0)+'%' : '—'}</span>
```

- [ ] **Step 4: Reload the dashboard manually**

Without restarting the bot, hard-reload the dashboard in the browser (Ctrl+F5). Confirm the active card for any position that has a `bid_price > 0` now shows a small positive or zero PnL (not the previous -0.5% to -2.5% spread-driven fake loss).

Note: if no WS ticks have arrived yet for a position (brand-new entry), `bid_price == 0.0` and the fallback path uses `current_price` — so behaviour is identical to before for those positions.

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat(dashboard): show bid-side MTM on active cards (realizable close)"
```

---

### Task 5: Part 1 audit + push

- [ ] **Step 1: Dispatch single audit agent**

Per CLAUDE.md rule: 1 agent per audit round, 2 consecutive clean rounds required. Dispatch one general-purpose agent with the prompt:

> "Audit `src/models.py`, `src/exit_monitor.py`, `src/websocket_feed.py`, `templates/dashboard.html` for the bid-MTM fix. Verify: (1) Position.bid_price defaults to 0, legacy positions.json loads clean, `unrealized_pnl_*` properties still read `current_price`. (2) WebSocketFeed callback signature is `(asset_id, yes_price, bid_price, ts)` and all three `_fire_callback` call sites pass `best_bid`. (3) ExitMonitor `_on_ws_price_update` accepts 4 positional args, `process_ws_ticks` unpacks 4-tuple and writes `pos.bid_price` with BUY_NO inversion. (4) Dashboard `renderActivePositions` uses `bid_price` with fallback, Entry→Now display matches the bid-side. (5) No exit-logic file was touched (grep for `bid_price` in stop_loss_helper/match_exit/trailing_tp/exit_executor — should be empty). (6) Zero dead code, zero spaghetti. (7) `pytest tests/test_bid_mtm.py tests/test_match_exit.py tests/test_odds_api_bugs.py tests/test_reentry.py -q` reports 158 passed. Report 0 bugs or a numbered list."

- [ ] **Step 2: Fix any bugs found, re-dispatch until one round is clean**

- [ ] **Step 3: Dispatch second fresh audit agent**

Same prompt. Must also return 0 bugs.

- [ ] **Step 4: Push**

```bash
git push origin master
```

---

## Part 2: Matcher Diagnostic (read-only, produces report)

### Task 6: Diagnostic script

**Files:**
- Create: `scripts/diagnose_matcher.py`
- Create: `docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md` (written by the script at run time)

- [ ] **Step 1: Create the diagnostic script**

Create `scripts/diagnose_matcher.py`:

```python
"""Matcher diagnostic: why are scout-queue entries not finding Polymarket markets?

Reads the current scout queue and live Polymarket markets (filtered to the 2h
window used by entry_gate), runs the real matcher, and writes a report
enumerating every scout entry that failed to match with a classification of
the likely reason.

Usage:
    python scripts/diagnose_matcher.py

Output: docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.matching import match_markets  # noqa: E402
from src.market_scanner import MarketScanner  # noqa: E402
from src.config import load_config  # noqa: E402

SCOUT_QUEUE = PROJECT_ROOT / "logs" / "scout_queue.json"
REPORT = PROJECT_ROOT / "docs" / "superpowers" / "analysis" / "2026-04-06-matcher-diagnostic.md"

# Window used by entry_gate._analyze_batch scout chrono selection
WINDOW_START_HOURS = -2.0
WINDOW_END_HOURS = 2.0


def load_scout_in_window(now: datetime) -> dict:
    raw = json.loads(SCOUT_QUEUE.read_text(encoding="utf-8"))
    in_window: dict = {}
    for key, entry in raw.items():
        mt = entry.get("match_time", "")
        if not mt:
            continue
        try:
            dt = datetime.fromisoformat(mt.replace("Z", "+00:00"))
        except ValueError:
            continue
        hours = (dt - now).total_seconds() / 3600
        if WINDOW_START_HOURS <= hours <= WINDOW_END_HOURS:
            in_window[key] = entry
    return in_window


def load_polymarket_in_window(now: datetime):
    cfg = load_config()
    scanner = MarketScanner(cfg.scanner)
    all_markets = scanner.fetch()
    in_window = []
    for m in all_markets:
        mt = getattr(m, "match_start_iso", "") or ""
        if not mt:
            continue
        try:
            dt = datetime.fromisoformat(mt.replace("Z", "+00:00"))
        except ValueError:
            continue
        hours = (dt - now).total_seconds() / 3600
        if WINDOW_START_HOURS <= hours <= WINDOW_END_HOURS:
            in_window.append(m)
    return in_window


def classify_failure(market, scout_queue: dict) -> str:
    """Return a short label explaining why this market likely did not match."""
    slug = (getattr(market, "slug", "") or "").lower()
    question = (getattr(market, "question", "") or "").lower()

    # Prop markets: first-set, exact-score, player props — no head-to-head scout entry
    prop_tokens = ("first-set", "exact-score", "total-", "-over-", "-under-",
                   "to-score", "anytime", "margin", "handicap")
    if any(tok in slug for tok in prop_tokens):
        return "prop_market_no_h2h_scout"

    # Outright / long-term (year-level, playoff, season)
    if any(tok in slug or tok in question for tok in
           ("season", "playoff", "champion", "finish", "top-scorer", "mvp")):
        return "outright_not_h2h"

    # Sport not in scout coverage
    if slug.startswith(("f1-", "ufc-", "mma-", "boxing-")):
        return "sport_not_scouted"

    # Default: likely fuzzy-name failure (both teams should exist but matcher missed)
    return "fuzzy_name_mismatch_candidate"


def main() -> int:
    now = datetime.now(timezone.utc)
    print(f"Running matcher diagnostic at {now.isoformat()}")

    scout = load_scout_in_window(now)
    markets = load_polymarket_in_window(now)
    print(f"Scout entries in 2h window:     {len(scout)}")
    print(f"Polymarket markets in 2h window: {len(markets)}")

    matched = match_markets(markets, scout)
    matched_cids = {mm["market"].condition_id for mm in matched}
    unmatched = [m for m in markets if m.condition_id not in matched_cids]
    print(f"Matched:   {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")

    # Classify unmatched
    from collections import Counter
    classes: Counter = Counter()
    per_class_samples: dict[str, list] = {}
    for m in unmatched:
        label = classify_failure(m, scout)
        classes[label] += 1
        per_class_samples.setdefault(label, [])
        if len(per_class_samples[label]) < 5:
            per_class_samples[label].append(
                f"{(m.slug or '')[:50]:50} | {(getattr(m, 'question', '') or '')[:60]}"
            )

    # Write report
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"# Matcher Diagnostic — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Scout entries in 2h window: **{len(scout)}**")
    lines.append(f"- Polymarket markets in 2h window: **{len(markets)}**")
    lines.append(f"- Matched: **{len(matched)}**")
    lines.append(f"- Unmatched: **{len(unmatched)}**")
    lines.append(f"- Match rate: **{len(matched) / max(len(markets), 1) * 100:.1f}%**")
    lines.append("")
    lines.append("## Unmatched by category")
    lines.append("")
    lines.append("| Category | Count | Description |")
    lines.append("|---|---|---|")
    descriptions = {
        "prop_market_no_h2h_scout":
            "Prop market (first-set, exact-score, totals, player props). "
            "Scout only stores head-to-head matches, so these will never match. "
            "Expected — not a matcher bug.",
        "outright_not_h2h":
            "Outright / season-long (champion, top scorer, finish 2nd). "
            "Not a head-to-head match. Expected.",
        "sport_not_scouted":
            "F1, UFC, boxing — not covered by the scout sources. Expected.",
        "fuzzy_name_mismatch_candidate":
            "Both teams exist as a head-to-head market; matcher *should* have "
            "found a scout entry but didn't. **Likely fuzzy-matching gap.**",
    }
    for cat, count in classes.most_common():
        lines.append(f"| `{cat}` | {count} | {descriptions.get(cat, '—')} |")
    lines.append("")
    lines.append("## Samples per category")
    lines.append("")
    for cat, count in classes.most_common():
        lines.append(f"### `{cat}` ({count} cases)")
        lines.append("")
        for s in per_class_samples.get(cat, []):
            lines.append(f"- `{s}`")
        lines.append("")

    # Reverse angle: scout entries that had no Polymarket market at all
    matched_scout_keys = {mm["scout_key"] for mm in matched}
    scout_unused = [k for k in scout if k not in matched_scout_keys]
    lines.append("## Scout entries without a Polymarket market")
    lines.append("")
    lines.append(f"Out of {len(scout)} scout entries in the 2h window, "
                 f"**{len(scout_unused)}** have no Polymarket counterpart. "
                 "These are either niche leagues Polymarket doesn't list, or "
                 "matcher-side fuzzy failures (if Polymarket DID list the match).")
    lines.append("")
    for k in scout_unused[:20]:
        e = scout[k]
        ta = e.get("team_a", "?")
        tb = e.get("team_b", "?")
        sport = e.get("sport") or "?"
        mt = e.get("match_time", "")[:16]
        lines.append(f"- `[{sport}]` {ta} vs {tb} @ {mt}")
    if len(scout_unused) > 20:
        lines.append(f"- ... and {len(scout_unused) - 20} more")
    lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    fuzzy_count = classes.get("fuzzy_name_mismatch_candidate", 0)
    if fuzzy_count == 0:
        lines.append(
            "No fuzzy-match gaps detected. All unmatched markets fall into "
            "categories the matcher is **not expected** to handle (props, "
            "outrights, non-scouted sports). Match rate is limited by "
            "Polymarket's non-H2H inventory, not matcher quality."
        )
    else:
        lines.append(
            f"**{fuzzy_count}** markets are candidates for a matcher patch. "
            "These are head-to-head markets where Polymarket and the scout "
            "both *should* know the teams but fuzzy matching failed. Review "
            "the `fuzzy_name_mismatch_candidate` samples above and open a "
            "follow-up matcher patch plan."
        )
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the diagnostic**

Run: `python scripts/diagnose_matcher.py`
Expected output: prints counts and writes `docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md`. Exit code 0.

- [ ] **Step 3: Read the report and decide next step**

Open `docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md`. Look at the `fuzzy_name_mismatch_candidate` count:

- **If 0:** No matcher bug — the low match rate is inventory-driven. Part 2 is done.
- **If > 0:** Open a follow-up plan for a matcher patch. That is a separate spec; do not write code in this plan.

- [ ] **Step 4: Commit the script and report**

```bash
git add scripts/diagnose_matcher.py docs/superpowers/analysis/2026-04-06-matcher-diagnostic.md
git commit -m "docs(matcher): diagnostic script + initial 2h-window report"
git push origin master
```

---

## Execution notes

- **Bot state during Part 1:** The bot can continue running while Part 1 tasks 1-3 are edited (they don't ship until Task 5). The dashboard will not show bid-side PnL until Task 4 is deployed, but existing behaviour is preserved.
- **Deploy trigger:** After Task 5 commits, the bot must be restarted (`taskkill` → `python -m src.main`) for the new WebSocketFeed callback signature to take effect. No log wipe — this is a deploy, not a reset.
- **Part 2:** Runs while bot is up. No restart needed.
