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

  // Exit reason label + renk artık FMT.exitReasonLabel + FMT.effectiveTone
  // tek kaynaktan. Eski yerel REASON_MAP kaldırıldı (TODO-006 konsolidasyonu).

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
          <button class="modal-nav-btn" id="modal-prev" title="Previous month">&#9664;</button>
          <span class="modal-nav-label" id="modal-month-label">--</span>
          <button class="modal-nav-btn" id="modal-next" title="Next month">&#9654;</button>
        </div>
        <div class="modal-view-tabs">
          <button class="modal-view-tab active" data-view="chart">Chart</button>
          <button class="modal-view-tab" data-view="list">List</button>
          <div class="modal-hero" id="modal-hero"></div>
        </div>
        <div class="modal-view" id="modal-view-chart">
          <div class="modal-chart-row">
            <div class="modal-chart-yaxis" id="modal-chart-yaxis"></div>
            <div class="modal-chart-wrap"><div class="modal-chart-inner"><canvas id="modal-chart"></canvas></div></div>
          </div>
        </div>
        <div class="modal-view" id="modal-view-list" style="display:none">
          <div class="modal-table-wrap" id="modal-table-wrap"></div>
        </div>
      </div>`;
    document.body.appendChild(ov);
    // Close handlers
    ov.addEventListener("click", (e) => { if (e.target === ov) _close(); });
    ov.querySelector("#modal-close").addEventListener("click", _close);
    ov.querySelector("#modal-prev").addEventListener("click", () => _navigate(1));
    ov.querySelector("#modal-next").addEventListener("click", () => _navigate(-1));
    // View tab switching (Chart / List)
    ov.querySelectorAll(".modal-view-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        ov.querySelectorAll(".modal-view-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const view = tab.dataset.view;
        ov.querySelector("#modal-view-chart").style.display = view === "chart" ? "" : "none";
        ov.querySelector("#modal-view-list").style.display = view === "list" ? "" : "none";
      });
    });
    // Mouse wheel → horizontal scroll on chart area
    const chartWrap = ov.querySelector(".modal-chart-wrap");
    if (chartWrap) {
      chartWrap.addEventListener("wheel", (e) => {
        if (chartWrap.scrollWidth <= chartWrap.clientWidth) return;
        if (e.deltaY === 0) return;
        e.preventDefault();
        chartWrap.scrollLeft += e.deltaY;
      }, { passive: false });
    }
    return ov;
  }

  // Dollar format for y-axis ticks
  const _fmtDollar = (v) => {
    const abs = Math.abs(v);
    const body = abs >= 1000 ? (abs / 1000).toFixed(2) + "k" : abs.toFixed(0);
    return (v < 0 ? "-" : "") + "$" + body;
  };

  function _initChart() {
    const C = global.COLORS || {};
    const ctx = document.getElementById("modal-chart").getContext("2d");
    return new Chart(ctx, {
      type: "bar",
      data: { labels: [], datasets: [{ data: [], backgroundColor: [],
        borderRadius: 4, borderSkipped: false, maxBarThickness: 28 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        layout: { padding: { top: 24, bottom: 24 } },
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
            suggestedMin: -50, suggestedMax: 50,
            ticks: { display: false, stepSize: 25 },
            afterFit: (s) => { s.width = 0; } },
        },
      },
      plugins: [{
        id: "modalYAxis",
        afterUpdate(chart) {
          const target = document.getElementById("modal-chart-yaxis");
          const yScale = chart.scales && chart.scales.y;
          if (!target || !yScale || !yScale.ticks) return;
          target.innerHTML = yScale.ticks.map((t) => {
            const y = yScale.getPixelForValue(t.value);
            return `<div class="chart-y-tick" style="top:${y}px">${_fmtDollar(t.value)}</div>`;
          }).join("");
        },
      }],
    });
  }

  // ── Render helpers ──

  function _renderHero(trades) {
    const el = document.getElementById("modal-hero");
    const total = trades.length;
    const pnl = trades.reduce((s, t) => s + Number(t.exit_pnl_usdc || 0), 0);
    const wins = trades.filter((t) => Number(t.exit_pnl_usdc || 0) > 0).length;
    const wr = total > 0 ? Math.round((wins / total) * 100) : 0;
    // Replay simulation: aydaki bütün fix delta'larının toplamı.
    // Sadece replay_simulation alanı dolu trade'lerde anlamlı; yoksa 0.
    const simDelta = trades.reduce((s, t) => {
      if (t.replay_simulation && t.replay_simulation.fixes) {
        return s + t.replay_simulation.fixes.reduce(
          (ss, f) => ss + Number(f.delta_usdc || 0), 0,
        );
      }
      return s;
    }, 0);
    const C = global.COLORS || {};
    const pnlColor = pnl >= 0 ? (C.green || "#08D391") : (C.red || "#D7323C");
    const wrColor = wr >= 50 ? (C.green || "#08D391") : (C.red || "#D7323C");
    const simColor = simDelta >= 0 ? (C.green || "#08D391") : (C.red || "#D7323C");
    const simCard = simDelta !== 0
      ? `<div class="modal-hero-card" title="Fixes aktif olsaydı aydaki net etki">` +
          `<div class="modal-hero-value" style="color:${simColor}">${FMT.usdSignedHtml(simDelta)}</div>` +
          `<div class="modal-hero-label">If-Fixes</div></div>`
      : "";
    el.innerHTML =
      `<div class="modal-hero-card">` +
        `<div class="modal-hero-value" style="color:${pnlColor}">${FMT.usdSignedHtml(pnl)}</div>` +
        `<div class="modal-hero-label">Weekly PnL</div></div>` +
      `<div class="modal-hero-card">` +
        `<div class="modal-hero-value" style="color:${wrColor}">${wr}%</div>` +
        `<div class="modal-hero-label">Win Rate</div></div>` +
      `<div class="modal-hero-card">` +
        `<div class="modal-hero-value">${total}</div>` +
        `<div class="modal-hero-label">Trades</div></div>` +
      simCard;
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
    // Scrollable: fixed min-width per bar (like main dashboard 30d chart).
    // Chart fills with trades; excess scrolls right.
    const barMinPx = 14;
    const inner = _chart.canvas.parentElement;
    if (inner) {
      const containerW = inner.parentElement ? inner.parentElement.clientWidth : 800;
      inner.style.width = Math.max(chron.length * barMinPx, containerW) + "px";
    }
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

  // tone → modal renk class'ı. pos→green, neg→red, neutral→muted.
  const _TONE_TO_COLOR = { pos: "green", neg: "red", neutral: "muted" };

  function _reasonBadge(reason, pnl) {
    const label = FMT.exitReasonLabel(reason);
    if (!label.text) {
      return `<span class="modal-reason modal-reason--muted">--</span>`;
    }
    const tone = FMT.effectiveTone(label, pnl);
    const colorCls = _TONE_TO_COLOR[tone] || "muted";
    const prefix = label.emoji ? label.emoji + " " : "";
    return `<span class="modal-reason modal-reason--${colorCls}">${prefix}${FMT.escapeHtml(label.text)}</span>`;
  }

  function _dirBadge(direction) {
    const isYes = direction === "BUY_YES";
    const cls = isYes ? "modal-dir--yes" : "modal-dir--no";
    return `<span class="modal-dir ${cls}">${isYes ? "YES" : "NO"}</span>`;
  }

  function _renderTable(trades) {
    const wrap = document.getElementById("modal-table-wrap");
    if (!trades.length) {
      wrap.innerHTML = '<div class="modal-empty">No trades this month.</div>';
      return;
    }
    const rows = trades.map((t) => {
      const d = new Date(t.exit_timestamp);
      const dateStr = isNaN(d.getTime()) ? "--"
        : `${d.getDate()} ${_MONTH[d.getMonth()]} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
      const icon = global.ICONS ? global.ICONS.getSportEmoji(t.sport_tag, t.slug) : "";
      const pnl = Number(t.exit_pnl_usdc || 0);
      const cls = pnl >= 0 ? "pnl-pos" : "pnl-neg";
      // Replay simulation: tüm fix delta'larını topla, en büyük etkili fix label'ını title'a koy.
      const sim = t.replay_simulation;
      let simCell = `<td class="modal-sim-cell"></td>`;
      if (sim && sim.fixes && sim.fixes.length) {
        const totalDelta = sim.fixes.reduce((s, f) => s + Number(f.delta_usdc || 0), 0);
        const dcls = totalDelta >= 0 ? "pnl-pos" : "pnl-neg";
        const fixSummary = sim.fixes.map(
          (f) => `${FMT.replaySimFixLabel(f.label)}: ${Number(f.delta_usdc || 0).toFixed(2)}`,
        ).join(" | ");
        simCell = `<td class="modal-sim-cell ${dcls}" title="${FMT.escapeHtml(fixSummary)}">${FMT.usdSignedHtml(totalDelta)}</td>`;
      }
      return `<tr>
        <td>${dateStr}</td>
        <td>${icon}</td>
        <td>${FMT.teamsText(t.question, t.slug)}</td>
        <td>${_dirBadge(t.direction)}</td>
        <td>${_holdTime(t.entry_timestamp, t.exit_timestamp)}</td>
        <td class="${cls}">${FMT.usdSignedHtml(pnl)}</td>
        ${simCell}
        <td>${_reasonBadge(t.exit_reason, pnl)}<button class="help-btn" type="button" onclick="event.stopPropagation(); event.preventDefault(); showSkipHelp('', 'exit', '${(String(t.exit_reason || "")).replace(/'/g, "").replace(/"/g, "")}')" title="Çıkış sebepleri açıkla">?</button></td>
      </tr>`;
    }).join("");
    const header =
      `<thead><tr>` +
        `<th>Date</th><th></th><th>Match</th><th>Dir</th>` +
        `<th>Hold</th><th>PnL</th><th title="Fixes aktif olsa toplam delta">If-Fixes</th><th>Reason</th>` +
      `</tr></thead>`;
    wrap.innerHTML =
      `<table class="modal-table">${header}<tbody>${rows}</tbody></table>`;
  }

  // ── Data + navigation ──

  async function _loadMonth(monthOffset) {
    _offset = monthOffset;
    try {
      const modeParam = (global.REPLAY_MODE && global.REPLAY_MODE.get() === "simulated")
        ? "&mode=simulated" : "";
      const r = await fetch("/api/trades/history?month_offset=" + _offset + "&_=" + Date.now() + modeParam);
      if (!r.ok) throw new Error(r.status);
      const data = await r.json();
      // "May 2026" -> "May" bold + "2026" dim
      const lbl = data.month_label || data.week_label || "--";
      const ym = lbl.match(/^(.+?)(\d{4})$/);
      if (ym) {
        document.getElementById("modal-month-label").innerHTML =
          ym[1].trim() + ' <span class="modal-nav-year">' + ym[2] + '</span>';
      } else {
        document.getElementById("modal-month-label").textContent = lbl;
      }
      // ◄ hidden when no older trades exist
      document.getElementById("modal-prev").style.visibility = data.has_older ? "visible" : "hidden";
      // ► always visible; disabled (opacity 40%) at current month
      const nextBtn = document.getElementById("modal-next");
      nextBtn.disabled = _offset === 0;
      nextBtn.style.visibility = "visible";
      _renderHero(data.trades);
      // Always render both — visible view depends on active tab.
      _renderChart(data.trades);
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
    _loadMonth(next);
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
    _loadMonth(0);
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
