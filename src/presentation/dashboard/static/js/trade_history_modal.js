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
        <div class="modal-chart-wrap"><div class="modal-chart-inner"><canvas id="modal-chart"></canvas></div></div>
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
    // Scrollable width — min 14px per bar, like main dashboard PnL chart.
    const minPx = 14;
    const inner = _chart.canvas.parentElement;
    if (inner) inner.style.width = Math.max(chron.length * minPx, inner.parentElement.clientWidth) + "px";
    _chart.update("none");
    _chart.resize();
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
        '<div class="modal-empty">Failed to load trades.<br><small>' + String(e) + '</small></div>';
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
