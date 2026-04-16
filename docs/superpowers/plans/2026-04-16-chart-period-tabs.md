# Chart Period Tabs + Adaptive Bucketing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard Total Equity + Per Trade PnL chart'larına period tab (24h/7d/30d/1y) + adaptif bucketing (event/hour/day/week) + CSS scroll; Total Equity'de tab-altı PnL özet satırı.

**Architecture:** Yeni pure JS module (`trade_filter.js`) tüm filtering/bucketing logic'ini taşır. `dashboard.js` state + render'ı yönetir, bucketing'i filter modülüne delege eder. HTML'e tab grubu + scroll wrapper + summary div eklenir. CSS'e 4 yeni class (mevcut palette token'ları kullanılır, yeni var yok). Backend dokunulmuyor.

**Tech Stack:** Vanilla JS (ES2015+), Chart.js 4.4.0, CSS3, Jinja2 template. JS test framework yok (manuel browser QA proje konvansiyonu).

**TDD refs:** §5.7.7 (Total Equity Chart — güncellenecek).

**ARCH_GUARD refs:** Kural 1 (presentation katmanı), Kural 3 (<400 satır), Kural 6 (magic number yok), Kural 10 (yeni dep yok).

---

## File Structure

**Create:**
- `src/presentation/dashboard/static/js/trade_filter.js` — pure filter + bucketing + sum

**Modify:**
- `src/presentation/dashboard/templates/dashboard.html` — tab HTML, chart-scroll wrapper, summary div, script tag
- `src/presentation/dashboard/static/css/dashboard.css` — `.chart-tabs`, `.chart-tab`, `.chart-scroll`, `.chart-summary`, `.panel-header` override
- `src/presentation/dashboard/static/js/dashboard.js` — CONFIG ek, CHART_STATE, LAST, `_bindChartTabs`, rewrite `setEquity` + `setWaterfall`, refresh cache update
- `TDD.md` §5.7.7 — period tabs + bucketing pattern notu

---

## Task 1: Create `trade_filter.js` pure module

**Files:**
- Create: `src/presentation/dashboard/static/js/trade_filter.js`

- [ ] **Step 1.1: Write the module**

```javascript
/* PolyAgent Dashboard — trade filtering + bucketing (pure, no I/O).
 *
 * Global namespace `FILTER`:
 *   filterByPeriod(trades, period) → trades[]
 *   cumulativeByResolution(trades, initial, resolution) → [{timestamp, value}]
 *   periodSum(trades) → number
 *   RESOLUTION_BY_PERIOD → { "24h": "event", "7d": "hour", "30d": "day", "1y": "week" }
 *
 * Spec: docs/superpowers/specs/2026-04-16-chart-period-tabs-design.md §3, §4.1
 */
(function (global) {
  "use strict";

  const HOURS_BY_PERIOD = { "24h": 24, "7d": 168, "30d": 720, "1y": 8760 };
  const RESOLUTION_BY_PERIOD = {
    "24h": "event",
    "7d": "hour",
    "30d": "day",
    "1y": "week",
  };

  function filterByPeriod(trades, period) {
    if (!trades) return [];
    const hours = HOURS_BY_PERIOD[period];
    if (!hours) return trades;
    const cutoff = Date.now() - hours * 3600 * 1000;
    return trades.filter((t) => {
      const ts = t && t.exit_timestamp ? Date.parse(t.exit_timestamp) : NaN;
      return Number.isFinite(ts) && ts >= cutoff;
    });
  }

  // ISO 8601 week key — Thursday-anchored, UTC-based.
  function _isoWeekKey(isoTs) {
    const d = new Date(isoTs);
    if (Number.isNaN(d.getTime())) return null;
    const tmp = new Date(
      Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
    );
    const dayNum = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((tmp - yearStart) / 86400000 + 1) / 7);
    return `${tmp.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
  }

  function _bucketKey(isoTs, resolution) {
    if (!isoTs) return null;
    if (resolution === "event") return isoTs;
    if (resolution === "hour") return isoTs.slice(0, 13);
    if (resolution === "day") return isoTs.slice(0, 10);
    if (resolution === "week") return _isoWeekKey(isoTs);
    return isoTs;
  }

  // Chronological cumsum, collapsed to bucket resolution.
  // Input: trades DESC-sorted by exit_timestamp (api/trades format).
  // Output: [{timestamp, value}] chronological (oldest → newest).
  function cumulativeByResolution(trades, initial, resolution) {
    const chron = [...(trades || [])].reverse();
    const byKey = new Map();
    let running = Number(initial) || 0;
    for (const t of chron) {
      running += Number(t.exit_pnl_usdc || 0);
      const key = _bucketKey(t.exit_timestamp, resolution);
      if (!key) continue;
      byKey.set(key, { timestamp: t.exit_timestamp, value: running });
    }
    return Array.from(byKey.values());
  }

  function periodSum(trades) {
    return (trades || []).reduce(
      (acc, t) => acc + Number(t.exit_pnl_usdc || 0),
      0
    );
  }

  global.FILTER = {
    filterByPeriod,
    cumulativeByResolution,
    periodSum,
    RESOLUTION_BY_PERIOD,
  };
})(window);
```

- [ ] **Step 1.2: Verify syntax via Node**

Run: `node -c "src/presentation/dashboard/static/js/trade_filter.js"`
Expected: no output (syntactically valid).

- [ ] **Step 1.3: Commit**

```bash
git add src/presentation/dashboard/static/js/trade_filter.js
git commit -m "feat(dashboard): add trade_filter pure module (filter + bucket + sum)"
```

---

## Task 2: Load `trade_filter.js` in template

**Files:**
- Modify: `src/presentation/dashboard/templates/dashboard.html:145-150`

- [ ] **Step 2.1: Add script tag**

In `dashboard.html` find the script section (around line 145-150) and insert `trade_filter.js` BEFORE `dashboard.js` (dashboard.js uses `FILTER`):

**OLD:**
```html
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="{{ url_for('static', filename='js/fmt.js') }}"></script>
  <script src="{{ url_for('static', filename='js/icons.js') }}"></script>
  <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
```

**NEW:**
```html
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="{{ url_for('static', filename='js/fmt.js') }}"></script>
  <script src="{{ url_for('static', filename='js/icons.js') }}"></script>
  <script src="{{ url_for('static', filename='js/trade_filter.js') }}"></script>
  <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
```

- [ ] **Step 2.2: Commit**

```bash
git add src/presentation/dashboard/templates/dashboard.html
git commit -m "chore(dashboard): load trade_filter before dashboard.js"
```

---

## Task 3: CSS — tabs, scroll, summary

**Files:**
- Modify: `src/presentation/dashboard/static/css/dashboard.css` (append to Charts section around line 276+)

- [ ] **Step 3.1: Append new styles**

Find the `/* ── Charts ── */` comment (around line 276) and append AFTER the existing `.chart-panel`/`.chart-fixed` rules (at end of file is also OK). Add:

```css
/* ── Chart period tabs + scroll + summary (spec 2026-04-16) ── */
.chart-panel .panel-header {
  justify-content: space-between;
}
.chart-tabs {
  display: flex;
  gap: 4px;
  margin-left: 12px;
}
.chart-tab {
  padding: 3px 8px;
  font-size: 10px;
  font-family: inherit;
  color: var(--muted);
  background: transparent;
  border: none;
  border-radius: 100px;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}
.chart-tab:hover { color: var(--text); }
.chart-tab:focus-visible { outline: 1px solid var(--border-soft); }
.chart-tab.active {
  color: var(--blue);
  background: var(--panel-hover);
}
.chart-summary {
  padding: 6px 0 8px;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.02em;
}
.chart-summary .pnl-pos { color: var(--green); }
.chart-summary .pnl-neg { color: var(--red); }
.chart-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  width: 100%;
  height: 100%;
}
.chart-scroll::-webkit-scrollbar { height: 6px; }
.chart-scroll::-webkit-scrollbar-thumb {
  background: var(--border-soft);
  border-radius: 3px;
}
```

- [ ] **Step 3.2: Verify CSS parses (visual spot check)**

Open `src/presentation/dashboard/static/css/dashboard.css` and confirm no unclosed braces at end. (Optional: run `npx csslint dashboard.css` if available.)

- [ ] **Step 3.3: Commit**

```bash
git add src/presentation/dashboard/static/css/dashboard.css
git commit -m "feat(dashboard): CSS for chart tabs, scroll, summary"
```

---

## Task 4: HTML — add tabs, chart-scroll wrapper, summary div

**Files:**
- Modify: `src/presentation/dashboard/templates/dashboard.html:114-124` (charts-row section)

- [ ] **Step 4.1: Replace charts-row**

Find (around line 114-124):

**OLD:**
```html
      <!-- Charts row -->
      <section class="charts-row">
        <div class="chart-panel">
          <div class="panel-header"><span class="card-icon">📈</span> Total Equity</div>
          <div class="chart-fixed"><canvas id="equity-chart"></canvas></div>
        </div>
        <div class="chart-panel">
          <div class="panel-header"><span class="card-icon">📊</span> Per Trade PnL</div>
          <div class="chart-fixed"><canvas id="waterfall-chart"></canvas></div>
        </div>
      </section>
```

**NEW:**
```html
      <!-- Charts row -->
      <section class="charts-row">
        <div class="chart-panel">
          <div class="panel-header">
            <span><span class="card-icon">📈</span> Total Equity</span>
            <div class="chart-tabs" data-chart="equity">
              <button class="chart-tab" data-period="24h">24h</button>
              <button class="chart-tab" data-period="7d">7d</button>
              <button class="chart-tab active" data-period="30d">30d</button>
              <button class="chart-tab" data-period="1y">1y</button>
            </div>
          </div>
          <div class="chart-summary" id="equity-period-summary"></div>
          <div class="chart-fixed">
            <div class="chart-scroll">
              <canvas id="equity-chart"></canvas>
            </div>
          </div>
        </div>
        <div class="chart-panel">
          <div class="panel-header">
            <span><span class="card-icon">📊</span> Per Trade PnL</span>
            <div class="chart-tabs" data-chart="pnl">
              <button class="chart-tab" data-period="24h">24h</button>
              <button class="chart-tab" data-period="7d">7d</button>
              <button class="chart-tab active" data-period="30d">30d</button>
              <button class="chart-tab" data-period="1y">1y</button>
            </div>
          </div>
          <div class="chart-fixed">
            <div class="chart-scroll">
              <canvas id="waterfall-chart"></canvas>
            </div>
          </div>
        </div>
      </section>
```

**Neden `<span>` wrapper:** panel-header flex ile `space-between` — sol taraf ikon+başlık tek span, sağ taraf tab grubu. Böylece icon ile text arası mevcut `gap: 6px` ayarı korunur (span içindeki boşluk).

- [ ] **Step 4.2: Commit**

```bash
git add src/presentation/dashboard/templates/dashboard.html
git commit -m "feat(dashboard): add period tabs + scroll wrapper + summary div to charts"
```

---

## Task 5: `dashboard.js` — CONFIG ek + CHART_STATE + LAST + INITIAL_BANKROLL reuse

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js:12-23` (CONFIG block + body data reads)

- [ ] **Step 5.1: Extend CONFIG + add CHART_STATE + LAST**

Find the CONFIG block (around lines 12-19) and the `MODE`/`MAX_POSITIONS`/`INITIAL_BANKROLL` reads immediately after:

**OLD:**
```javascript
  // ── CONFIG (sabitler — magic number yasağı) ──
  const CONFIG = {
    pollIntervalMs: 5000,
    waterfallMaxBars: 40,
    stageRecentSec: 180,        // stage_at kaç saniyeden yeniyse aktif sayılır (heavy cycle 1-2 dk)
    idleTickMs: 1000,           // idle countdown re-render intervali
    msPerMin: 60000,            // dakika→ms dönüştürme sabiti
    barRadius: 4,               // bar chart köşe yuvarlaması
  };

  const MODE = document.body.dataset.mode || "dry_run";
  const MAX_POSITIONS = parseInt(document.body.dataset.maxPositions || "20", 10);
  const INITIAL_BANKROLL = parseFloat(document.body.dataset.initialBankroll || "1000");
```

**NEW:**
```javascript
  // ── CONFIG (sabitler — magic number yasağı) ──
  const CONFIG = {
    pollIntervalMs: 5000,
    waterfallMaxBars: 40,
    stageRecentSec: 180,        // stage_at kaç saniyeden yeniyse aktif sayılır (heavy cycle 1-2 dk)
    idleTickMs: 1000,           // idle countdown re-render intervali
    msPerMin: 60000,            // dakika→ms dönüştürme sabiti
    barRadius: 4,               // bar chart köşe yuvarlaması
    equityBarMinPx: 18,         // Total Equity per-point min genişlik (scroll threshold)
    pnlBarMinPx: 14,            // Per Trade per-bar min genişlik (scroll threshold)
  };

  const MODE = document.body.dataset.mode || "dry_run";
  const MAX_POSITIONS = parseInt(document.body.dataset.maxPositions || "20", 10);
  const INITIAL_BANKROLL = parseFloat(document.body.dataset.initialBankroll || "1000");

  // ── Chart state (tab selection + trades cache) ──
  const CHART_STATE = { equityPeriod: "30d", pnlPeriod: "30d" };
  const LAST = { trades: [] };
```

- [ ] **Step 5.2: Commit**

```bash
git add src/presentation/dashboard/static/js/dashboard.js
git commit -m "feat(dashboard): CONFIG ek (equityBarMinPx/pnlBarMinPx) + CHART_STATE + LAST cache"
```

---

## Task 6: Rewrite `CHARTS.setEquity` — bucketing + summary

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js:146-164` (setEquity method)

- [ ] **Step 6.1: Replace `setEquity` body**

Find the current `setEquity` method (around lines 146-164). Replace with:

```javascript
    setEquity(trades, initialBankroll) {
      // TDD §5.7.7: chart = initial + cumulative realized PnL.
      // Period + resolution: spec 2026-04-16 §3.
      const period = CHART_STATE.equityPeriod;
      const resolution = global.FILTER.RESOLUTION_BY_PERIOD[period] || "event";
      const windowTrades = global.FILTER.filterByPeriod(trades, period);
      const points = global.FILTER.cumulativeByResolution(
        windowTrades, initialBankroll, resolution
      );

      const baseline = Number(initialBankroll) || 0;
      this.equity.data.labels = [""].concat(points.map((p) => p.timestamp || ""));
      this.equity.data.datasets[0].data = [baseline].concat(points.map((p) => p.value));

      // Canvas min-width — yoğun dilimde horizontal scroll tetiklenir.
      const minWidth = (points.length + 1) * CONFIG.equityBarMinPx;
      this.equity.canvas.style.minWidth = minWidth + "px";

      // Tab-altı period özeti.
      const sum = global.FILTER.periodSum(windowTrades);
      const sumEl = document.getElementById("equity-period-summary");
      if (sumEl) {
        const cls = sum >= 0 ? "pnl-pos" : "pnl-neg";
        const sign = sum >= 0 ? "+" : "−";
        const n = windowTrades.length;
        sumEl.innerHTML =
          `${period.toUpperCase()} PnL ` +
          `<span class="${cls}">${sign}$${Math.abs(sum).toFixed(2)}</span> ` +
          `· ${n} trade${n === 1 ? "" : "s"}`;
      }

      this.equity.update("none");
    },
```

- [ ] **Step 6.2: Commit**

```bash
git add src/presentation/dashboard/static/js/dashboard.js
git commit -m "feat(dashboard): setEquity with adaptive bucketing + tab-altı PnL summary"
```

---

## Task 7: Rewrite `CHARTS.setWaterfall` — period filter + scroll min-width

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js:156-194` (setWaterfall method)

- [ ] **Step 7.1: Replace `setWaterfall` head (filter + slice) + add min-width**

Find the current `setWaterfall` method. The tooltip config block inside is long; KEEP it as-is. Only change the data pipeline + add min-width. Replace the method as follows:

```javascript
    setWaterfall(trades) {
      // Period filter (event-level; her bar = bir exit, bucketing yapılmaz).
      const period = CHART_STATE.pnlPeriod;
      const windowTrades = global.FILTER.filterByPeriod(trades, period);
      const limited = windowTrades.slice(0, CONFIG.waterfallMaxBars).reverse();
      // Minimum 12 slot — az trade varsa bars sola yaslanır, sağ tarafta boşluk
      // kalır. Yeni trade geldiğinde sağa eklenir (reverse: kronolojik eski→yeni).
      const MIN_SLOTS = 12;
      const slots = Math.max(limited.length, MIN_SLOTS);
      const labels = new Array(slots).fill("");
      const data = new Array(slots).fill(null);
      limited.forEach((t, i) => {
        labels[i] = FMT.teamsText(t.question, t.slug);
        data[i] = Number(t.exit_pnl_usdc || 0);
      });
      this.waterfall.data.labels = labels;
      this.waterfall.data.datasets[0].data = data;
      this.waterfall.data.datasets[0].backgroundColor =
        data.map((v) => (v == null ? "transparent" : (v >= 0 ? COLORS.green : COLORS.red)));
      this.waterfall.data.datasets[0].hoverBackgroundColor =
        data.map((v) => (v == null ? "transparent" : (v >= 0 ? COLORS.green : COLORS.red)));

      // Canvas min-width — yoğun dilimde horizontal scroll.
      this.waterfall.canvas.style.minWidth = (slots * CONFIG.pnlBarMinPx) + "px";

      // Tooltip: color box yok, PnL renk kuralına göre (pozitif yeşil / 0 mavi / negatif kırmızı).
      this.waterfall.options.plugins.tooltip = {
        enabled: true,
        displayColors: false,
        callbacks: {
          label: (ctx) => {
            const v = ctx.parsed.y;
            const sign = v > 0 ? "+" : v < 0 ? "-" : "";
            return `${sign}$${Math.abs(v).toFixed(2)}`;
          },
          labelTextColor: (ctx) => {
            const v = ctx.parsed.y;
            if (Math.abs(v) < 1e-9) return COLORS.blue;
            return v > 0 ? COLORS.green : COLORS.red;
          },
        },
      };
      this.waterfall.update("none");
    },
```

**Not:** Eski versiyon `trades.slice(0, CONFIG.waterfallMaxBars).reverse()` kullanıyordu — tüm trade listesini direkt slice'lıyordu. Yeni versiyon period-filtered slice alır. Tooltip bloğu aynıdır.

- [ ] **Step 7.2: Commit**

```bash
git add src/presentation/dashboard/static/js/dashboard.js
git commit -m "feat(dashboard): setWaterfall period filter + scroll min-width"
```

---

## Task 8: `_bindChartTabs` + refresh cache update

**Files:**
- Modify: `src/presentation/dashboard/static/js/dashboard.js` (around CHARTS module end / MAIN module + DOMContentLoaded)

- [ ] **Step 8.1: Add `CHART_TAB_BINDING` + `_bindChartTabs`**

Find the end of the CHARTS module (after `setWaterfall`'s closing brace, but inside `CHARTS` object — or as module-level function below CHARTS; place it as a module-level function after CHARTS closes).

The closest existing pattern: after `};` that closes the `const CHARTS = { ... };` block, add:

```javascript
  // ── Tab binding (period filter) ──
  const CHART_TAB_BINDING = {
    equity: {
      stateKey: "equityPeriod",
      render: () => CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL),
    },
    pnl: {
      stateKey: "pnlPeriod",
      render: () => CHARTS.setWaterfall(LAST.trades),
    },
  };

  function _bindChartTabs() {
    document.querySelectorAll(".chart-tabs").forEach((group) => {
      const chart = group.dataset.chart;
      const binding = CHART_TAB_BINDING[chart];
      if (!binding) return;
      group.addEventListener("click", (e) => {
        const btn = e.target.closest(".chart-tab");
        if (!btn) return;
        group.querySelectorAll(".chart-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        CHART_STATE[binding.stateKey] = btn.dataset.period;
        binding.render();
      });
    });
  }
```

- [ ] **Step 8.2: Update `refresh()` to cache trades**

Find `MAIN.refresh` (around line 315). Replace:

**OLD:**
```javascript
    async refresh() {
      try {
        const [status, summary,
               positions, trades, skipped, stock, stats, sportRoi] = await Promise.all([
          API.status(), API.summary(),
          API.positions(), API.trades(), API.skipped(), API.stock(),
          API.stats(), API.sportRoi(),
        ]);
        RENDER.status(status);
        RENDER.metrics(summary.equity);
        RENDER.wlStats(stats);
        RENDER.slots(summary.slots);
        RENDER.lossProtection(summary.loss_protection);
        CHARTS.setEquity(trades, INITIAL_BANKROLL);
        CHARTS.setWaterfall(trades);
        global.FEED.update({
          active: Object.values(positions),
          exited: trades, skipped: skipped, stock: stock,
        });
        global.BRANCHES.render(sportRoi);
      } catch (e) {
        console.error("Refresh error:", e);
      }
    },
```

**NEW:**
```javascript
    async refresh() {
      try {
        const [status, summary,
               positions, trades, skipped, stock, stats, sportRoi] = await Promise.all([
          API.status(), API.summary(),
          API.positions(), API.trades(), API.skipped(), API.stock(),
          API.stats(), API.sportRoi(),
        ]);
        LAST.trades = trades;  // cache for tab clicks (5sn polling)
        RENDER.status(status);
        RENDER.metrics(summary.equity);
        RENDER.wlStats(stats);
        RENDER.slots(summary.slots);
        RENDER.lossProtection(summary.loss_protection);
        CHARTS.setEquity(LAST.trades, INITIAL_BANKROLL);
        CHARTS.setWaterfall(LAST.trades);
        global.FEED.update({
          active: Object.values(positions),
          exited: trades, skipped: skipped, stock: stock,
        });
        global.BRANCHES.render(sportRoi);
      } catch (e) {
        console.error("Refresh error:", e);
      }
    },
```

- [ ] **Step 8.3: Wire `_bindChartTabs` into startup**

Find `MAIN.start` or the DOMContentLoaded / init entry point. Likely there's a line like:

```javascript
  document.addEventListener("DOMContentLoaded", () => {
    CHARTS.initAll();
    MAIN.refresh();
    MAIN.startPolling();
    // ...
  });
```

Or inside `MAIN.start()`. If uncertain, grep for `DOMContentLoaded` or `initAll`:

Run: `grep -n "DOMContentLoaded\|initAll" src/presentation/dashboard/static/js/dashboard.js`

Add `_bindChartTabs();` call AFTER `CHARTS.initAll();` so the DOM tabs exist when we bind:

```javascript
    CHARTS.initAll();
    _bindChartTabs();       // ← new
    MAIN.refresh();
```

- [ ] **Step 8.4: Syntax check**

Run: `node -c "src/presentation/dashboard/static/js/dashboard.js"`
Expected: no output (valid syntax).

- [ ] **Step 8.5: Commit**

```bash
git add src/presentation/dashboard/static/js/dashboard.js
git commit -m "feat(dashboard): bind chart tabs + LAST.trades cache in refresh"
```

---

## Task 9: Update TDD §5.7.7

**Files:**
- Modify: `TDD.md` §5.7.7

- [ ] **Step 9.1: Replace §5.7.7 body**

Find the heading `#### 5.7.7 Total Equity Chart — Realized-Only Stepped` in `TDD.md`. Replace the body (below heading, before next `####` or `---` delimiter) with:

```markdown
#### 5.7.7 Total Equity Chart — Realized-Only Stepped + Period Tabs

Chart formülü: `initial_bankroll + Σ exit_pnl_usdc` (trade history üzerinden
kümülatif). **Unrealized hariç** — açık pozisyonların anlık fiyat
dalgalanması chart'ı kirletmez.

**Veri kaynağı:** `/api/trades` (`computed.exit_events`) — full-close exit'ler
+ partial scale-out event'leri. Client kronolojik sıraya çevirip
`exit_pnl_usdc` üzerinde kümülatif toplam yapar.

**Period tabs + adaptif bucketing (2026-04-16 fix, PLAN-009):**

| Tab | Granularity | Her nokta ne? | Tipik max |
|-----|------------|----------------|-----------|
| 24h | Event | Her exit = 1 basamak | ~50 |
| 7d  | Hourly | Saat sonu kümülatif | ~168 |
| 30d | Daily | Gün sonu kümülatif | 30 |
| 1y  | Weekly (ISO) | Hafta sonu kümülatif | 52 |

Default tab: `30d`. "All" yok — sınırsız scroll'u önlemek için (lifetime PnL
Balance kartında görünür). Yoğun dilimlerde (24h/7d) canvas `overflow-x: auto`
ile scroll.

Rendering: `stepped: "before"`, `tension: 0` — yumuşak eğri yerine
basamaklı plateau.

**Neden trade-cumsum + bucketing:** Eski implementasyon `equity_history.jsonl`
snapshot'larını çiziyordu; partial exit basis-leak'i (PLAN-008) nedeniyle
identity kırılıyordu. Trade cumsum inşaat gereği identity-correct;
bucketing ise geniş dilimlerde (30d/1y) nokta yoğunluğunu ekran-dostu
seviyede tutar.

Identity (her period için): son nokta = `initial + Σ exit_pnl_usdc`
(dilim içindeki). `30d` tab'ında chart sonu = başlangıç + son 30 günün
realized PnL toplamı.

**Tab-altı PnL özeti** (yalnızca Total Equity kartında):
Format: `{PERIOD} PnL {±$XX.XX} · {N} trades`. Pozitif yeşil, negatif
kırmızı. Per Trade PnL kartında bu satır yok.

**Per Trade PnL chart:** Aynı 4 tab kullanılır; period filter uygulanır
fakat bucketing YAPILMAZ — her bar bir exit event. `waterfallMaxBars = 40`
üst limit + CSS scroll ile eski trade'lere erişim.

Lokasyon:
- `static/js/trade_filter.js::FILTER.cumulativeByResolution`
- `static/js/dashboard.js::CHARTS.setEquity(trades, initialBankroll)`
```

- [ ] **Step 9.2: Commit**

```bash
git add TDD.md
git commit -m "docs(tdd): §5.7.7 period tabs + adaptive bucketing pattern (PLAN-009)"
```

---

## Task 10: Browser QA + Final commit

**Files:** none (manual verification)

- [ ] **Step 10.1: Start dev dashboard**

Run: `python -m src.main` (or existing dev start command) and open `http://localhost:5050/` in browser.

- [ ] **Step 10.2: QA Checklist**

Tick each:
- [ ] Sayfa yüklendiğinde her iki chart'ta `30d` tab'ı aktif (mavi/panel-hover background).
- [ ] Total Equity kartında tab-altı `30D PnL ±$X.XX · N trades` görünür; pozitif yeşil, negatif kırmızı.
- [ ] `24h` tab'ına tıkla → chart her exit için bir basamak gösterir; Per Trade yalnız son 24h bar'ı.
- [ ] `7d` tab → Total Equity saat bazlı nokta (aynı saatteki exit'ler tek noktaya collapse); Per Trade son 7 günün tüm bar'ları.
- [ ] `30d` tab → Total Equity günlük kapanış noktaları (≤30); Per Trade son 30 günün bar'ları.
- [ ] `1y` tab → Total Equity haftalık nokta (≤52); Per Trade son 365 günün bar'ları.
- [ ] Yoğun dilimde (Per Trade 7d/30d/1y) yatay scroll bar görünür, eski trade'lere scroll ile erişilebilir.
- [ ] Seyrek dilimde (24h az trade) scroll yok, canvas container'a sığar.
- [ ] İki chart bağımsız tab state tutar (Total Equity `7d` iken Per Trade `24h` olabilir).
- [ ] 5sn auto-refresh sonrasında aktif tab sıfırlanmaz, seçim korunur.
- [ ] Chart.js tooltip'leri tab değişiminde de doğru tetiklenir (hover).
- [ ] Browser console'da hata yok.
- [ ] Identity check: browser console'da aşağıdaki script `0` yazdırır (tolerans < 0.01):

```javascript
// Kopyala yapıştır:
(async () => {
  const trades = await (await fetch('/api/trades')).json();
  const sum = trades.reduce((a, t) => a + Number(t.exit_pnl_usdc || 0), 0);
  const summary = await (await fetch('/api/summary')).json();
  console.log('sum(trade exit_pnl)=', sum.toFixed(2),
              'stored realized=', summary.equity.realized_pnl.toFixed(2),
              'diff=', (sum - summary.equity.realized_pnl).toFixed(2));
})();
```

- [ ] **Step 10.3: Fix any issues**

If QA fails on any item → diagnose + fix inline → re-run QA → commit fix. Do NOT mark task complete until all ticks pass.

- [ ] **Step 10.4: Remove PLAN-009 from PLAN.md if added**

If PLAN-009 entry exists in `PLAN.md`, remove it per CLAUDE.md protocol (completed plans are deleted from PLAN.md; detailed plan doc in `docs/superpowers/plans/` stays as historical record).

- [ ] **Step 10.5: Final commit**

```bash
# If no further changes needed after QA:
echo "QA passed — no additional commits needed."

# If PLAN.md was touched:
git add PLAN.md
git commit -m "chore: remove PLAN-009 from PLAN.md (DONE)"
```

---

## Risk & Rollback

- **R1:** Chart.js `maintainAspectRatio` ile canvas `minWidth` çakışması → Task 10 QA'da yatay scroll testi bunu yakalar. Çakışma varsa `.chart-fixed { height: <fixed>; }` ekle.
- **R2:** `_bindChartTabs` DOMContentLoaded öncesi çağrılırsa tabs bulunmaz → Task 8.3 `CHARTS.initAll()` sonrası sıralaması bunu önler.
- **R3:** `FILTER` global'i dashboard.js yüklenmeden tanımsız olursa crash → Task 2 script tag sıralaması kritik (trade_filter.js ÖNCE).
- **R4:** Weekly ISO key farklı timezone'larda farklı değer üretebilir → Task 1 `_isoWeekKey` UTC-based, bot kayıtları UTC → tutarlı.

**Rollback:** Tek commit ise revert; çoklu commit ise `git revert <hash>..<hash>`. Backend değişmediği için data migration yok.

---

## Spec Coverage Self-Review

| Spec § | Covered by Task | OK |
|--------|-----------------|----|
| §2 Mimari karar (tabs + bucket + scroll) | 1, 3, 4, 6, 7 | ✓ |
| §3 Resolution tablosu | 1 (RESOLUTION_BY_PERIOD), 6 (uygular) | ✓ |
| §4.1 trade_filter.js | 1 | ✓ |
| §4.2 Tab HTML | 4 | ✓ |
| §4.3 CSS | 3 | ✓ |
| §4.4 JS state + binding | 5, 8 | ✓ |
| §4.5 setEquity | 6 | ✓ |
| §4.6 setWaterfall | 7 | ✓ |
| §4.7 Refresh akışı | 8.2 | ✓ |
| §4.8 CONFIG ekleri | 5 | ✓ |
| §6 Testing (manual QA) | 10.2 | ✓ |
| §7 TDD update | 9 | ✓ |
| §8 ARCH_GUARD | tüm task'larda self-check uygulanır | ✓ |

No gaps detected.
