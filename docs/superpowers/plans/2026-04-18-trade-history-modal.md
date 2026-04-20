# Trade History Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full-screen modal showing all trades with weekly pagination, hero metrics, hold time, and reason badges.

**Architecture:** Presentation-only. New backend endpoint (`/api/trades/history`) with weekly pagination reads from existing `trade_history.jsonl`. New JS module (`trade_history_modal.js`) renders modal with Chart.js bar chart + trade table. Also fixes dashboard.js 412-line ARCH_GUARD violation.

**Tech Stack:** Flask (backend), Chart.js 4.4 (chart), vanilla JS (modal), CSS custom properties (palette).

**Spec:** `docs/superpowers/specs/2026-04-18-trade-history-modal-design.md`

---

### Task 1: Fix dashboard.js ARCH_GUARD Violation (idle block → chart_tabs.js)

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js:400-412`
- Modify: `src/presentation/dashboard/static/js/chart_tabs.js:55-93`
- Modify: `src/presentation/dashboard/static/js/dashboard.js:384-397` (MAIN.init — pass new deps)

- [ ] **Step 1: Remove idle countdown block from dashboard.js**

Remove lines 400-412 from `dashboard.js`:

```javascript
// DELETE THIS ENTIRE BLOCK (lines 400-412):
// Idle countdown — /api/status cevabı cache'lenir, 1s'de bir label re-render edilir
let _lastStatusData = null;
const _origStatus = RENDER.status.bind(RENDER);
RENDER.status = function (data) {
  _lastStatusData = data;
  _origStatus(data);
};
setInterval(() => {
  if (_lastStatusData) _origStatus(_lastStatusData);
}, CONFIG.idleTickMs);
```

- [ ] **Step 2: Expose COLORS globally and pass idle deps to chart_tabs.bind()**

In `dashboard.js`, update `MAIN.init()` to expose COLORS and pass idle deps:

```javascript
init() {
  _initColors();
  global.COLORS = COLORS;  // modal JS needs palette access
  document.getElementById("slots-max").textContent = MAX_POSITIONS;
  CHARTS.initAll();
  global.CHART_TABS.bind({
    charts: CHARTS,
    state: CHART_STATE,
    cache: LAST,
    initialBankroll: INITIAL_BANKROLL,
    render: RENDER,              // NEW — idle countdown needs RENDER.status
    idleTickMs: CONFIG.idleTickMs, // NEW — idle interval constant
  });
  global.FEED.bindTabs();
  this.refresh();
  setInterval(() => this.refresh(), CONFIG.pollIntervalMs);
},
```

- [ ] **Step 3: Add idle countdown to chart_tabs.js bind()**

In `chart_tabs.js`, add idle countdown wiring at the end of `bind()`:

```javascript
function bind(deps) {
  const { charts, state, cache, initialBankroll, render, idleTickMs } = deps;
  const binding = {
    equity: {
      stateKey: "equityPeriod",
      render: () => charts.setEquity(cache.trades, initialBankroll),
    },
    pnl: {
      stateKey: "pnlPeriod",
      render: () => charts.setWaterfall(cache.trades),
    },
  };

  document.querySelectorAll(".chart-tabs").forEach((group) => {
    const chart = group.dataset.chart;
    const b = binding[chart];
    if (!b) return;
    group.addEventListener("click", (e) => {
      const btn = e.target.closest(".chart-tab");
      if (!btn) return;
      group.querySelectorAll(".chart-tab").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      state[b.stateKey] = btn.dataset.period;
      b.render();
    });
  });

  // Mouse wheel → yatay scroll (yalnızca yatay taşma varsa).
  document.querySelectorAll(".chart-scroll").forEach((el) => {
    el.addEventListener("wheel", (e) => {
      if (el.scrollWidth <= el.clientWidth) return;
      if (e.deltaY === 0) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    }, { passive: false });
  });

  // Idle countdown — status her 1s'de re-render (next heavy timer).
  // dashboard.js'ten taşındı (ARCH_GUARD Kural 3: 400 satır limiti).
  if (render && render.status && idleTickMs) {
    let _lastStatusData = null;
    const _origStatus = render.status.bind(render);
    render.status = function (data) {
      _lastStatusData = data;
      _origStatus(data);
    };
    setInterval(() => {
      if (_lastStatusData) _origStatus(_lastStatusData);
    }, idleTickMs);
  }
}
```

- [ ] **Step 4: Verify line counts**

Run:
```bash
wc -l src/presentation/dashboard/static/js/dashboard.js src/presentation/dashboard/static/js/chart_tabs.js
```

Expected: dashboard.js ≤ 400, chart_tabs.js ≤ 400.

- [ ] **Step 5: Verify dashboard still works**

Run:
```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE PROJELER/Polymarket Agent 2.0" && python -c "from src.presentation.dashboard.app import create_app; print('OK')"
```

Expected: `OK` (no import errors).

- [ ] **Step 6: Commit**

```bash
git add src/presentation/dashboard/static/js/dashboard.js src/presentation/dashboard/static/js/chart_tabs.js
git commit -m "refactor(dashboard): move idle countdown to chart_tabs.js (ARCH_GUARD fix)"
```

---

### Task 2: Backend — `read_trades_by_week()` + Tests

**Files:**
- Modify: `src/presentation/dashboard/readers.py`
- Create: `tests/unit/presentation/test_readers_week.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/presentation/test_readers_week.py`:

```python
"""Trade history weekly pagination reader tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.presentation.dashboard.readers import read_trades_by_week

_MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _make_trade(exit_iso: str) -> dict:
    return {
        "slug": "test-abc-xyz-2026-04-18",
        "sport_tag": "baseball_mlb",
        "exit_timestamp": exit_iso,
        "exit_pnl_usdc": 10.0,
        "exit_price": 0.55,
        "entry_timestamp": "2026-04-15T10:00:00Z",
    }


def _write_trades(tmp_path: Path, trades: list[dict]) -> Path:
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    with open(logs / "trade_history.jsonl", "w") as f:
        for t in trades:
            f.write(json.dumps(t) + "\n")
    return logs


def _monday_of_current_week() -> datetime:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


class TestReadTradesByWeek:
    def test_current_week_returns_this_weeks_trades(self, tmp_path: Path):
        monday = _monday_of_current_week()
        t1 = _make_trade((monday + timedelta(hours=10)).isoformat())
        t2 = _make_trade((monday + timedelta(days=2, hours=5)).isoformat())
        old = _make_trade((monday - timedelta(days=3)).isoformat())
        logs = _write_trades(tmp_path, [old, t1, t2])

        trades, label, has_older = read_trades_by_week(logs, week_offset=0)
        assert len(trades) == 2
        assert has_older is True

    def test_past_week_returns_correct_trades(self, tmp_path: Path):
        monday = _monday_of_current_week()
        this_week = _make_trade((monday + timedelta(hours=5)).isoformat())
        last_week = _make_trade((monday - timedelta(days=3)).isoformat())
        logs = _write_trades(tmp_path, [last_week, this_week])

        trades, label, has_older = read_trades_by_week(logs, week_offset=1)
        assert len(trades) == 1
        assert has_older is False

    def test_empty_week_returns_empty(self, tmp_path: Path):
        monday = _monday_of_current_week()
        t = _make_trade((monday + timedelta(hours=5)).isoformat())
        logs = _write_trades(tmp_path, [t])

        trades, label, has_older = read_trades_by_week(logs, week_offset=5)
        assert trades == []
        assert has_older is False

    def test_has_older_true_when_older_exists(self, tmp_path: Path):
        monday = _monday_of_current_week()
        old = _make_trade((monday - timedelta(days=14)).isoformat())
        last_week = _make_trade((monday - timedelta(days=3)).isoformat())
        logs = _write_trades(tmp_path, [old, last_week])

        trades, label, has_older = read_trades_by_week(logs, week_offset=1)
        assert len(trades) == 1
        assert has_older is True

    def test_label_format(self, tmp_path: Path):
        monday = _monday_of_current_week()
        t = _make_trade((monday + timedelta(hours=5)).isoformat())
        logs = _write_trades(tmp_path, [t])

        _, label, _ = read_trades_by_week(logs, week_offset=0)
        # Label should contain month abbreviation and year
        assert "2026" in label or "202" in label
        assert " - " in label

    def test_no_file_returns_empty(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir(exist_ok=True)
        trades, label, has_older = read_trades_by_week(logs, week_offset=0)
        assert trades == []
        assert has_older is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/presentation/test_readers_week.py -v`
Expected: FAIL — `ImportError: cannot import name 'read_trades_by_week'`

- [ ] **Step 3: Implement `read_trades_by_week` in readers.py**

Add to `src/presentation/dashboard/readers.py` (after `read_trades` function):

```python
def read_trades_by_week(
    logs_dir: Path, week_offset: int = 0,
) -> tuple[list[dict[str, Any]], str, bool]:
    """ISO-week-aligned trade pagination.

    week_offset=0 → current week (Mon 00:00 UTC – Sun 23:59 UTC).
    week_offset=1 → previous week, etc.

    Returns (trades_in_week, week_label, has_older_data).
    """
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    # Monday 00:00 of target week
    current_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    week_start = current_monday - timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=7)

    # Read enough lines to cover requested depth.
    # Estimate: ~150 trades/week × (offset+2) weeks of buffer.
    buffer_weeks = week_offset + 2
    n = 150 * buffer_weeks
    all_trades = _read_jsonl_tail(logs_dir / "trade_history.jsonl", n, _BYTES_TRADES)

    week_trades: list[dict[str, Any]] = []
    has_older = False
    start_ts = week_start.isoformat()
    end_ts = week_end.isoformat()

    for t in all_trades:
        ts = t.get("exit_timestamp", "")
        if not ts:
            continue
        if ts < start_ts:
            has_older = True
        elif ts < end_ts:
            week_trades.append(t)

    # Week label: "DD - DD Mon YYYY" or "DD Mon - DD Mon YYYY" if month spans.
    _MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sun = week_start + timedelta(days=6)
    if week_start.month == sun.month:
        label = (f"{week_start.day} - {sun.day} "
                 f"{_MONTHS[week_start.month - 1]} {week_start.year}")
    else:
        label = (f"{week_start.day} {_MONTHS[week_start.month - 1]} - "
                 f"{sun.day} {_MONTHS[sun.month - 1]} {week_start.year}")

    return week_trades, label, has_older
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/presentation/test_readers_week.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/presentation/dashboard/readers.py tests/unit/presentation/test_readers_week.py
git commit -m "feat(dashboard): add read_trades_by_week for weekly pagination"
```

---

### Task 3: Backend — `/api/trades/history` Endpoint

**Files:**
- Modify: `src/presentation/dashboard/routes.py`

- [ ] **Step 1: Add endpoint to routes.py**

Add inside `register_routes()`, after the `api_sport_roi` handler:

```python
    @app.route("/api/trades/history")
    def api_trades_history():
        from flask import request
        offset = request.args.get("week_offset", 0, type=int)
        raw, label, has_older = readers.read_trades_by_week(logs_dir, offset)
        events = computed.exit_events(raw)
        return jsonify({
            "trades": events,
            "week_label": label,
            "week_offset": offset,
            "has_older": has_older,
            "total_in_week": len(events),
        })
```

Note: `from flask import request` is added inline because the existing `routes.py` only imports `Flask, jsonify, render_template`. Adding `request` to the top-level import is also fine.

- [ ] **Step 2: Add `request` to top-level import**

Update the existing import line in `routes.py`:

```python
from flask import Flask, jsonify, render_template, request
```

Then remove the inline import from step 1.

- [ ] **Step 3: Verify no import errors**

Run:
```bash
python -c "from src.presentation.dashboard.routes import register_routes; print('OK')"
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add src/presentation/dashboard/routes.py
git commit -m "feat(dashboard): add /api/trades/history weekly endpoint"
```

---

### Task 4: Frontend — modal.css

**Files:**
- Create: `src/presentation/dashboard/static/css/modal.css`

- [ ] **Step 1: Create modal.css**

Create `src/presentation/dashboard/static/css/modal.css`:

```css
/* Trade History Modal — full-screen overlay + weekly trade viewer.
 * Renk referansları var(--*) ile — hex literal yasak (TDD §5.7.4).
 */

/* ── Overlay ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}
.modal-overlay.visible { opacity: 1; }

/* ── Container ── */
.modal-container {
  width: 94vw;
  max-width: 1400px;
  max-height: 90vh;
  background: var(--panel);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Header ── */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}
.modal-header h2 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}
.modal-close {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.modal-close:hover {
  color: var(--text);
  background: var(--panel-hover);
}

/* ── Week navigation ── */
.modal-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px 24px;
  font-size: 13px;
  color: var(--muted);
}
.modal-nav-btn {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.modal-nav-btn:hover { color: var(--text); background: var(--panel-hover); }
.modal-nav-btn:disabled { opacity: 0.3; cursor: default; }
.modal-nav-btn:disabled:hover { color: var(--muted); background: none; }
.modal-nav-label { font-weight: 600; color: var(--text); }

/* ── Hero metrics ── */
.modal-hero {
  display: flex;
  gap: 12px;
  padding: 8px 24px 12px;
}
.modal-hero-card {
  flex: 1;
  background: var(--panel-raised);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  text-align: center;
}
.modal-hero-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.modal-hero-label {
  font-size: 10px;
  color: var(--muted);
  margin-top: 2px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* ── Chart area ── */
.modal-chart-wrap {
  padding: 0 24px;
  min-height: 160px;
  max-height: 200px;
}

/* ── Trade table ── */
.modal-table-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px 20px;
}
.modal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.modal-table th {
  text-align: left;
  color: var(--muted);
  font-weight: 600;
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-soft);
  position: sticky;
  top: 0;
  background: var(--panel);
  z-index: 1;
}
.modal-table td {
  padding: 7px 6px;
  border-bottom: 1px solid var(--border-soft);
  color: var(--text);
}
.modal-table tr:hover td { background: var(--panel-raised); }

/* ── Reason badge ── */
.modal-reason {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.modal-reason--green { color: var(--green); background: var(--green-dim); }
.modal-reason--red   { color: var(--red);   background: var(--red-dim); }
.modal-reason--orange { color: var(--orange); background: var(--orange-dim); }
.modal-reason--blue  { color: var(--blue);  background: var(--blue-dim); }
.modal-reason--muted { color: var(--muted); background: rgba(148,163,184,0.08); }

/* ── Direction badge ── */
.modal-dir {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}
.modal-dir--yes { color: var(--green); background: var(--green-dim); }
.modal-dir--no  { color: var(--red);   background: var(--red-dim); }

/* ── "All" trigger button ── */
.modal-trigger {
  padding: 3px 10px;
  font-size: 10px;
  font-family: inherit;
  font-weight: 600;
  color: var(--blue);
  background: var(--blue-dim);
  border: none;
  border-radius: 100px;
  cursor: pointer;
  margin-left: 8px;
  transition: background 0.15s;
}
.modal-trigger:hover { background: var(--panel-hover); }

/* ── Empty state ── */
.modal-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--muted);
  font-size: 13px;
}

/* ── Scrollbar ── */
.modal-table-wrap::-webkit-scrollbar { width: 6px; }
.modal-table-wrap::-webkit-scrollbar-thumb {
  background: var(--border-soft);
  border-radius: 3px;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/presentation/dashboard/static/css/modal.css
git commit -m "feat(dashboard): add modal.css for trade history overlay"
```

---

### Task 5: Frontend — trade_history_modal.js

**Files:**
- Create: `src/presentation/dashboard/static/js/trade_history_modal.js`

- [ ] **Step 1: Create trade_history_modal.js**

Create `src/presentation/dashboard/static/js/trade_history_modal.js`:

```javascript
/* Trade History Modal — full-screen weekly trade viewer.
 *
 * Namespace: TRADE_HISTORY (global).
 * Dependencies: FMT (fmt.js), ICONS (icons.js), COLORS (dashboard.js).
 * Chart.js must be loaded before this file.
 *
 * Spec: docs/superpowers/specs/2026-04-18-trade-history-modal-design.md
 */
(function (global) {
  "use strict";

  // ── Exit reason badge mapping (spec §3) ──
  const REASON_MAP = {
    tp_hit:              { emoji: "\uD83C\uDFAF", label: "Take Profit", color: "green" },
    sl_hit:              { emoji: "\uD83D\uDED1", label: "Stop Loss",   color: "red" },
    graduated_sl:        { emoji: "\uD83D\uDED1", label: "Grad. SL",    color: "red" },
    scale_out_tier_1:    { emoji: "\uD83D\uDCCA", label: "Scale T1",    color: "orange" },
    scale_out_tier_2:    { emoji: "\uD83D\uDCCA", label: "Scale T2",    color: "orange" },
    near_resolve:        { emoji: "\u23F0",       label: "Near Resolve", color: "blue" },
    market_flip:         { emoji: "\uD83D\uDD04", label: "Market Flip",  color: "red" },
    score_exit:          { emoji: "\u26A1",       label: "Score Exit",   color: "red" },
    hold_revoked:        { emoji: "\u26A0\uFE0F", label: "Hold Revoked", color: "red" },
    catastrophic_bounce: { emoji: "\uD83D\uDCA5", label: "Catastrophic", color: "red" },
    manual:              { emoji: "\u270B",       label: "Manual",       color: "muted" },
  };

  const _MONTH = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"];

  let _overlay = null;
  let _chart = null;
  let _offset = 0;

  // ── DOM builders ──

  function _createOverlay() {
    const ov = document.createElement("div");
    ov.className = "modal-overlay";
    ov.innerHTML = `
      <div class="modal-container">
        <div class="modal-header">
          <h2>Trade History</h2>
          <button class="modal-close" id="modal-close">&times;</button>
        </div>
        <div class="modal-nav">
          <button class="modal-nav-btn" id="modal-prev">&laquo;</button>
          <span class="modal-nav-label" id="modal-week-label">--</span>
          <button class="modal-nav-btn" id="modal-next">&raquo;</button>
        </div>
        <div class="modal-hero" id="modal-hero"></div>
        <div class="modal-chart-wrap"><canvas id="modal-chart"></canvas></div>
        <div class="modal-table-wrap" id="modal-table-wrap"></div>
      </div>`;
    document.body.appendChild(ov);
    // Close handlers
    ov.addEventListener("click", (e) => { if (e.target === ov) _close(); });
    ov.querySelector("#modal-close").addEventListener("click", _close);
    ov.querySelector("#modal-prev").addEventListener("click", () => _navigate(1));
    ov.querySelector("#modal-next").addEventListener("click", () => _navigate(-1));
    return ov;
  }

  function _initChart() {
    const C = global.COLORS || {};
    const ctx = document.getElementById("modal-chart").getContext("2d");
    return new Chart(ctx, {
      type: "bar",
      data: { labels: [], datasets: [{ data: [], backgroundColor: [],
        borderRadius: 4, borderSkipped: false, maxBarThickness: 28 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true, displayColors: false,
            callbacks: {
              title: (items) => {
                if (!items[0]) return "";
                const t = items[0].dataset._tooltips;
                return t ? t[items[0].dataIndex] || "" : "";
              },
              label: (ctx) => {
                const v = ctx.parsed.y;
                return (v >= 0 ? "+" : "-") + "$" + Math.abs(v).toFixed(2);
              },
            },
          },
        },
        scales: {
          x: { display: true, grid: { display: false },
            ticks: { color: C.axisLabel || "rgba(148,163,184,0.5)",
              font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
          y: { display: true, grid: { color: C.gridLine || "rgba(148,163,184,0.06)" },
            ticks: { color: C.axisLabel || "rgba(148,163,184,0.5)",
              font: { size: 10 }, callback: (v) => "$" + v } },
        },
      },
    });
  }

  // ── Render helpers ──

  function _renderHero(trades) {
    const el = document.getElementById("modal-hero");
    const total = trades.length;
    const pnl = trades.reduce((s, t) => s + Number(t.exit_pnl_usdc || 0), 0);
    const wins = trades.filter((t) => Number(t.exit_pnl_usdc || 0) > 0).length;
    const wr = total > 0 ? Math.round((wins / total) * 100) : 0;
    const C = global.COLORS || {};
    const pnlColor = pnl >= 0 ? (C.green || "#08D391") : (C.red || "#D7323C");
    const wrColor = wr >= 50 ? (C.green || "#08D391") : (C.red || "#D7323C");
    el.innerHTML =
      `<div class="modal-hero-card">` +
        `<div class="modal-hero-value" style="color:${pnlColor}">${FMT.usdSigned(pnl)}</div>` +
        `<div class="modal-hero-label">Weekly PnL</div></div>` +
      `<div class="modal-hero-card">` +
        `<div class="modal-hero-value" style="color:${wrColor}">${wr}%</div>` +
        `<div class="modal-hero-label">Win Rate</div></div>` +
      `<div class="modal-hero-card">` +
        `<div class="modal-hero-value">${total}</div>` +
        `<div class="modal-hero-label">Trades</div></div>`;
  }

  function _renderChart(trades) {
    const C = global.COLORS || {};
    const chron = [...trades].reverse();
    const labels = chron.map((t) => {
      const d = new Date(t.exit_timestamp);
      if (isNaN(d.getTime())) return "";
      return `${d.getDate()} ${_MONTH[d.getMonth()]} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
    });
    const data = chron.map((t) => Number(t.exit_pnl_usdc || 0));
    const bg = data.map((v) => v >= 0 ? (C.green || "#08D391") : (C.red || "#D7323C"));
    const tooltips = chron.map((t) => FMT.teamsText(t.question, t.slug));
    _chart.data.labels = labels;
    _chart.data.datasets[0].data = data;
    _chart.data.datasets[0].backgroundColor = bg;
    _chart.data.datasets[0].hoverBackgroundColor = bg;
    _chart.data.datasets[0]._tooltips = tooltips;
    _chart.update("none");
  }

  function _holdTime(entry, exit) {
    if (!entry || !exit) return "--";
    const ms = new Date(exit).getTime() - new Date(entry).getTime();
    if (isNaN(ms) || ms < 0) return "--";
    const mins = Math.floor(ms / 60000);
    if (mins < 60) return mins + "m";
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h + "h " + String(m).padStart(2, "0") + "m";
  }

  function _reasonBadge(reason) {
    const r = REASON_MAP[reason];
    if (!r) {
      return `<span class="modal-reason modal-reason--muted">${FMT.escapeHtml(reason || "--")}</span>`;
    }
    return `<span class="modal-reason modal-reason--${r.color}">${r.emoji} ${r.label}</span>`;
  }

  function _dirBadge(direction) {
    const isYes = direction === "BUY_YES";
    const cls = isYes ? "modal-dir--yes" : "modal-dir--no";
    return `<span class="modal-dir ${cls}">${isYes ? "YES" : "NO"}</span>`;
  }

  function _renderTable(trades) {
    const wrap = document.getElementById("modal-table-wrap");
    if (!trades.length) {
      wrap.innerHTML = '<div class="modal-empty">No trades this week.</div>';
      return;
    }
    const rows = trades.map((t) => {
      const d = new Date(t.exit_timestamp);
      const dateStr = isNaN(d.getTime()) ? "--"
        : `${d.getDate()} ${_MONTH[d.getMonth()]} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
      const icon = global.ICONS ? global.ICONS.getSportEmoji(t.sport_tag, t.slug) : "";
      const pnl = Number(t.exit_pnl_usdc || 0);
      const cls = pnl >= 0 ? "pnl-pos" : "pnl-neg";
      return `<tr>
        <td>${dateStr}</td>
        <td>${icon}</td>
        <td>${FMT.teamsText(t.question, t.slug)}</td>
        <td>${_dirBadge(t.direction)}</td>
        <td>${_holdTime(t.entry_timestamp, t.exit_timestamp)}</td>
        <td class="${cls}">${FMT.usdSigned(pnl)}</td>
        <td>${_reasonBadge(t.exit_reason)}</td>
      </tr>`;
    }).join("");
    wrap.innerHTML =
      `<table class="modal-table">
        <thead><tr>
          <th>Date</th><th></th><th>Match</th><th>Dir</th>
          <th>Hold</th><th>PnL</th><th>Reason</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  // ── Data + navigation ──

  async function _loadWeek(weekOffset) {
    _offset = weekOffset;
    try {
      const r = await fetch("/api/trades/history?week_offset=" + _offset + "&_=" + Date.now());
      if (!r.ok) throw new Error(r.status);
      const data = await r.json();
      document.getElementById("modal-week-label").textContent = data.week_label;
      document.getElementById("modal-prev").disabled = !data.has_older;
      const nextBtn = document.getElementById("modal-next");
      nextBtn.style.visibility = _offset === 0 ? "hidden" : "visible";
      _renderHero(data.trades);
      if (data.trades.length) {
        document.querySelector(".modal-chart-wrap").style.display = "";
        _renderChart(data.trades);
      } else {
        document.querySelector(".modal-chart-wrap").style.display = "none";
      }
      _renderTable(data.trades);
    } catch (e) {
      console.error("Trade history load error:", e);
      document.getElementById("modal-table-wrap").innerHTML =
        '<div class="modal-empty">Failed to load trades.</div>';
    }
  }

  function _navigate(delta) {
    const next = _offset + delta;
    if (next < 0) return;
    _loadWeek(next);
  }

  // ── Open / Close ──

  function _open() {
    if (!_overlay) {
      _overlay = _createOverlay();
      _chart = _initChart();
    }
    _offset = 0;
    _overlay.style.display = "flex";
    requestAnimationFrame(() => _overlay.classList.add("visible"));
    _loadWeek(0);
  }

  function _close() {
    if (!_overlay) return;
    _overlay.classList.remove("visible");
    setTimeout(() => { _overlay.style.display = "none"; }, 200);
  }

  function _onKeydown(e) {
    if (e.key === "Escape" && _overlay && _overlay.style.display !== "none") {
      _close();
    }
  }

  // ── Init ──
  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-trade-history");
    if (btn) btn.addEventListener("click", _open);
    document.addEventListener("keydown", _onKeydown);
  });

  global.TRADE_HISTORY = { open: _open, close: _close };
})(window);
```

- [ ] **Step 2: Verify line count**

Run: `wc -l src/presentation/dashboard/static/js/trade_history_modal.js`
Expected: ≤ 250 lines.

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/static/js/trade_history_modal.js
git commit -m "feat(dashboard): add trade history modal JS (hero + chart + table)"
```

---

### Task 6: HTML Wiring — dashboard.html

**Files:**
- Modify: `src/presentation/dashboard/templates/dashboard.html`

- [ ] **Step 1: Add modal.css link**

In `dashboard.html`, after the existing CSS links (after line 16 `branches.css`):

```html
  <link rel="stylesheet" href="{{ url_for('static', filename='css/modal.css') }}" />
```

- [ ] **Step 2: Add "All" button to Per Trade PnL panel**

Replace the Per Trade PnL panel-header (lines 139-146):

```html
        <div class="chart-panel">
          <div class="panel-header">
            <span>Per Trade PnL</span>
            <button class="modal-trigger" id="btn-trade-history" title="All trades">All</button>
            <div class="chart-tabs" data-chart="pnl">
              <button class="chart-tab" data-period="24h">24h</button>
              <button class="chart-tab" data-period="7d">7d</button>
              <button class="chart-tab active" data-period="30d">30d</button>
              <button class="chart-tab" data-period="1y">1y</button>
            </div>
          </div>
```

- [ ] **Step 3: Add trade_history_modal.js script**

After the `branches.js` script tag (after line 187):

```html
  <script src="{{ url_for('static', filename='js/trade_history_modal.js') }}"></script>
```

- [ ] **Step 4: Commit**

```bash
git add src/presentation/dashboard/templates/dashboard.html
git commit -m "feat(dashboard): wire All button + modal CSS/JS in HTML"
```

---

### Task 7: Backend — `entry_timestamp` in Exit Events

**Files:**
- Modify: `src/presentation/dashboard/computed.py`

The `exit_events()` function currently doesn't pass `entry_timestamp` through for full-close events (it does `dict(t)` which includes it), but partial scale-out events miss it. Fix:

- [ ] **Step 1: Add entry_timestamp to partial events in computed.py**

In `computed.py`, inside `exit_events()`, add `entry_timestamp` to the partial event dict:

```python
        for pe in (t.get("partial_exits") or []):
            events.append({
                "slug": t.get("slug", ""),
                "sport_tag": t.get("sport_tag", ""),
                "direction": t.get("direction", ""),
                "entry_price": t.get("entry_price"),
                "entry_timestamp": t.get("entry_timestamp", ""),  # NEW — hold time
                "question": t.get("question", ""),
                "exit_price": None,
                "exit_pnl_usdc": pe.get("realized_pnl_usdc", 0.0),
                "exit_reason": f"scale_out_tier_{pe.get('tier', '?')}",
                "exit_timestamp": pe.get("timestamp", ""),
                "partial": True,
                "sell_pct": pe.get("sell_pct", 0.0),
            })
```

- [ ] **Step 2: Run existing tests**

Run: `pytest tests/ -q`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/presentation/dashboard/computed.py
git commit -m "fix(dashboard): include entry_timestamp in partial exit events"
```

---

### Task 8: Manual Smoke Test + Final Verification

- [ ] **Step 1: Verify all file line counts**

Run:
```bash
wc -l src/presentation/dashboard/static/js/dashboard.js src/presentation/dashboard/static/js/chart_tabs.js src/presentation/dashboard/static/js/trade_history_modal.js src/presentation/dashboard/static/css/modal.css
```

Expected: All ≤ 400 lines.

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -q`
Expected: All pass.

- [ ] **Step 3: Start dashboard and test modal**

Run: `python src/main.py --mode dry_run` (or however dashboard starts)

Manual checks:
1. "All" button visible in Per Trade PnL header
2. Click "All" → modal opens with dark overlay
3. Hero metrics show PnL / Win Rate / Trades
4. Bar chart renders (or "No trades" if empty)
5. Table shows Date / Sport / Match / Dir / Hold / PnL / Reason columns
6. Reason badges have emoji + color
7. `◄` navigates to previous week
8. `►` hidden on current week
9. `X`, `Escape`, overlay click all close modal
10. Main dashboard continues polling behind modal

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "feat(dashboard): trade history modal complete (SPEC-007)"
```
