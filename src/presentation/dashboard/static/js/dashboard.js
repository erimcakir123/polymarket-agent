/* PolyAgent Dashboard — core client logic.
 *
 * Modüller: CONFIG, API, CHARTS, RENDER, MAIN.
 * FMT namespace → fmt.js (ayrı dosya, önce yüklenir).
 * ICONS namespace → icons.js (ayrı dosya, önce yüklenir).
 * FEED modülü feed.js'te (ayrı dosya, 400-satır kuralı).
 */
(function (global) {
  "use strict";

  // ── CONFIG (sabitler — magic number yasağı) ──
  const CONFIG = {
    pollIntervalMs: 5000,
    // waterfallMaxBars kaldırıldı — period filter yeterli, cap gereksiz overlap yaratıyordu.
    stageRecentSec: 600,        // stage_at kaç saniyeden yeniyse aktif sayılır (tenis enrichment 5-10dk)
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

  // ── API (fetch wrappers) ──
  const API = {
    async _json(path) {
      const r = await fetch(path + "?_=" + Date.now());
      if (!r.ok) throw new Error(path + " " + r.status);
      return r.json();
    },
    status() { return this._json("/api/status"); },
    summary() { return this._json("/api/summary"); },
    equityHistory() { return this._json("/api/equity_history"); },
    positions() { return this._json("/api/positions"); },
    trades() { return this._json("/api/trades"); },
    skipped() { return this._json("/api/skipped"); },
    stock() { return this._json("/api/stock"); },
    stats() { return this._json("/api/stats"); },
    sportRoi() { return this._json("/api/sport_roi"); },
    calibration() { return this._json("/api/calibration"); },
  };

  // ── CHARTS (Chart.js) — palette CSS'ten okunur, hex literal YASAK ──
  // Lazy init — script parse anında CSS henüz uygulanmamış olabilir.
  // getComputedStyle boş dönerse null.map() crash → tüm IIFE düşer.
  // COLORS ilk `initAll` çağrısında doldurulur (DOMContentLoaded sonrası).
  const _cssVar = (name) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const _rgba = (varName, alpha) => {
    const raw = _cssVar(varName);
    const hex = raw.replace("#", "");
    const match = hex.match(/.{2}/g);
    if (!match) return `rgba(0, 0, 0, ${alpha})`;  // CSS henüz yok — güvenli fallback
    const [r, g, b] = match.map((h) => parseInt(h, 16));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };
  const COLORS = {};
  function _initColors() {
    Object.assign(COLORS, {
      green:     _cssVar("--green")      || "#08D391",
      red:       _cssVar("--red")        || "#D7323C",
      redHover:  _cssVar("--red-hover")  || "#F4454F",
      blue:      _cssVar("--blue")       || "#0F9AB2",
      orange:    _cssVar("--orange")     || "#FB971E",
      muted:     _cssVar("--muted-dim")  || "#64748b",
      greenFill: _rgba("--green", 0.14),
      greenDim:  _rgba("--green", 0.5),
      track: "rgba(148, 163, 184, 0.08)",
      gridLine: "rgba(148, 163, 184, 0.06)",
      axisLabel: _cssVar("--axis-label") || "rgba(148, 163, 184, 0.5)",
    });
  }

  const CHARTS = {
    equity: null, waterfall: null, lp: null,
    initAll() {
      this._initLine("equity-chart", "equity", COLORS.green, COLORS.greenFill);
      this._initBar("waterfall-chart", "waterfall");
      this._initGauge("lp-gauge", "lp", COLORS.green);
    },

    _initLine(canvasId, key, border, fill) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      this[key] = new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{
          data: [], borderColor: border, backgroundColor: fill,
          borderWidth: 2, fill: true, pointRadius: 0,
          // Stepped — sadece exit/realize anında değişir, aralar düz plateau.
          stepped: "before",
          tension: 0,
        }] },
        options: this._baseOpts(true),
      });
    },

    _initBar(canvasId, key) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      this[key] = new Chart(ctx, {
        type: "bar",
        data: { labels: [], datasets: [{
          data: [], backgroundColor: [],
          borderRadius: CONFIG.barRadius, borderSkipped: false,
          maxBarThickness: 28,  // cap — padding yok, bar doğal slotunda
        }] },
        options: this._baseOpts(true),
      });
    },

    _baseOpts(showY) {
      const tickStyle = { color: COLORS.axisLabel, font: { size: 10 } };
      return {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true, bodyFont: { weight: "bold" } } },
        scales: {
          x: { display: true, grid: { display: false },
            ticks: { ...tickStyle, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
          // Y-axis labels externalYAxis plugin tarafından DOM'a yazılır (sticky).
          // Canvas'taki y-axis grid çizer ama kendi label'ı gizli; width=0.
          y: { display: showY, grid: { color: COLORS.gridLine },
            ticks: { ...tickStyle, display: false },
            afterFit: (s) => { s.width = 0; } },
        },
      };
    },

    _initGauge(canvasId, key, color) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      this[key] = new Chart(ctx, {
        type: "doughnut",
        data: { datasets: [{
          data: [0, 100], backgroundColor: [color, COLORS.track],
          borderWidth: 0, cutout: "72%", circumference: 180, rotation: 270,
        }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
        },
      });
    },

    setGauge(key, pct, color) {
      const p = Math.max(0, Math.min(100, pct));
      this[key].data.datasets[0].data = [p, 100 - p];
      if (color) this[key].data.datasets[0].backgroundColor[0] = color;
      this[key].update("none");
    },

    setEquity(trades, initialBankroll) {
      // DECISIONS §5.7.7: initial + cumulative realized PnL; period + resolution per spec §3.
      const period = CHART_STATE.equityPeriod;
      const resolution = global.FILTER.RESOLUTION_BY_PERIOD[period] || "event";
      const windowTrades = global.FILTER.filterByPeriod(trades, period);
      const points = global.FILTER.cumulativeByResolution(windowTrades, initialBankroll, resolution);
      const baseline = Number(initialBankroll) || 0;
      this.equity.data.labels = [""].concat(points.map((p, i) =>
        period === "1y" ? "W" + (i + 1) : global.FILTER.periodLabel(p.timestamp, period)));
      const seriesValues = [baseline].concat(points.map((p) => p.value));
      this.equity.data.datasets[0].data = seriesValues;
      // Y-axis veriye sikica fit — Chart.js default suggestedMax cok genis padding
      // ekliyordu ($1.18 peak iken $1.25k tavan). $50 snap, peak hemen ustte.
      const _CHART_Y_SNAP = 50;
      const dMin = Math.min(...seriesValues);
      const dMax = Math.max(...seriesValues);
      this.equity.options.scales.y.min = Math.floor(dMin / _CHART_Y_SNAP) * _CHART_Y_SNAP;
      this.equity.options.scales.y.max = Math.ceil(dMax / _CHART_Y_SNAP) * _CHART_Y_SNAP;
      // Parent wrap width — Chart.js responsive observer → canvas internal senkron (hitbox).
      this.equity.canvas.parentElement.style.width = ((points.length + 1) * CONFIG.equityBarMinPx) + "px";

      const sum = global.FILTER.periodSum(windowTrades);
      const sumEl = document.getElementById("equity-period-summary");
      if (sumEl) {
        const cls = sum >= 0 ? "pnl-pos" : "pnl-neg";
        const sign = sum >= 0 ? "+" : "−";
        const n = windowTrades.length;
        sumEl.innerHTML =
          `<strong class="${cls}">${sign}$${Math.abs(sum).toFixed(2)}</strong> · ` +
          `${n} trade${n === 1 ? "" : "s"}`;
      }
      this.equity.update("none");
      this.equity.resize();  // hitbox alignment — canvas internal size must track CSS minWidth
    },

    setWaterfall(trades) {
      // Period filter + resolution bucketing (equity chart ile aynı mantık).
      const period = CHART_STATE.pnlPeriod;
      const resolution = global.FILTER.RESOLUTION_BY_PERIOD[period] || "event";
      const windowTrades = global.FILTER.filterByPeriod(trades, period);
      const buckets = global.FILTER.pnlByResolution(windowTrades, resolution);
      // Event modunda takım adları (chronological sıra — windowTrades reversed).
      const chronTrades = resolution === "event" ? [...windowTrades].reverse() : [];
      // Minimum 12 slot — az bar varsa sola yaslanır.
      const MIN_SLOTS = 12;
      const slots = Math.max(buckets.length, MIN_SLOTS);
      const labels = new Array(slots).fill("");
      const data = new Array(slots).fill(null);
      const tooltips = new Array(slots).fill("");
      buckets.forEach((b, i) => {
        labels[i] = period === "1y" ? "W" + (i + 1) : global.FILTER.periodLabel(b.timestamp, period);
        data[i] = Number(b.pnl || 0);
        if (resolution === "event" && chronTrades[i]) {
          tooltips[i] = FMT.teamsText(chronTrades[i].question, chronTrades[i].slug);
        } else if (resolution !== "event") {
          tooltips[i] = b.count + " trade";
        }
      });
      this.waterfall.data.labels = labels;
      this.waterfall.data.datasets[0].data = data;
      this.waterfall.data.datasets[0]._tooltips = tooltips;
      this.waterfall.data.datasets[0].backgroundColor =
        data.map((v) => (v == null ? "transparent" : (v >= 0 ? COLORS.green : COLORS.red)));
      this.waterfall.data.datasets[0].hoverBackgroundColor =
        data.map((v) => (v == null ? "transparent" : (v >= 0 ? COLORS.green : COLORS.red)));

      this.waterfall.canvas.parentElement.style.width = (slots * CONFIG.pnlBarMinPx) + "px";
      // Tooltip: event modunda takım adı, bucket modunda trade sayısı.
      this.waterfall.options.plugins.tooltip = {
        enabled: true, displayColors: false,
        callbacks: {
          title: (items) => {
            if (!items || !items[0]) return "";
            const idx = items[0].dataIndex;
            const tip = items[0].dataset._tooltips && items[0].dataset._tooltips[idx];
            return tip || "";
          },
          label: (ctx) => (ctx.parsed.y > 0 ? "+" : ctx.parsed.y < 0 ? "-" : "")
            + `$${Math.abs(ctx.parsed.y).toFixed(2)}`,
          labelTextColor: (ctx) => Math.abs(ctx.parsed.y) < 1e-9 ? COLORS.blue
            : (ctx.parsed.y > 0 ? COLORS.green : COLORS.red),
        },
      };
      this.waterfall.update("none");
      this.waterfall.resize();  // hitbox alignment after minWidth change
    },
  };

  // ── RENDER (DOM updates) ──
  const RENDER = {
    status(data) {
      // Bot offline → her iki cycle de "offline" variant (muted).
      const botAlive = !!data.bot_alive;
      if (!botAlive) {
        this._applyCycle("cg-light", "offline", "Offline", false);
        this._applyCycle("cg-hard", "offline", "Offline", false);
        return;
      }
      // Light her 5sn tick'liyor ama anlamlı "aktif iş" sadece heartbeat anı —
      // sürekli pulse ile hard'ı gereksiz yere söndürmemek için static.
      this._applyCycle("cg-light", "light", "Online", false);
      const stage = (data.stage || "").toLowerCase();
      const stageRecent = this._isRecent(data.stage_at, CONFIG.stageRecentSec);
      let label, live;
      if (stage === "scanning" && stageRecent) { label = "Scanning"; live = true; }
      else if (stage === "analyzing" && stageRecent) { label = "Analyzing"; live = true; }
      else if (stage === "executing" && stageRecent) { label = "Executing"; live = true; }
      else if (stage === "idle" || !stageRecent) {
        label = this._countdownLabel(data.next_heavy_at);
        live = false;
      }
      else {
        label = this._countdownLabel(data.next_heavy_at);
        live = false;
      }
      this._applyCycle("cg-hard", "hard", label, live);
    },

    _countdownLabel(nextHeavyIso) {
      if (!nextHeavyIso) return "--:--";
      const target = new Date(nextHeavyIso).getTime();
      if (isNaN(target)) return "--:--";
      const diff = Math.max(0, target - Date.now());
      const mins = Math.floor(diff / CONFIG.msPerMin);
      const secs = Math.floor((diff % CONFIG.msPerMin) / 1000);
      const mm = String(mins).padStart(2, "0");
      const ss = String(secs).padStart(2, "0");
      return `${mm}:${ss}`;
    },

    _applyCycle(id, variant, label, live) {
      document.getElementById(id).className = "cycle-group " + variant;
      document.getElementById(id + "-status").textContent = label;
      const dot = document.querySelector("#" + id + " .cycle-dot");
      if (dot) dot.classList.toggle("live", live);
    },

    _isRecent(iso, maxSeconds) {
      if (!iso) return false;
      const d = new Date(iso);
      if (isNaN(d.getTime())) return false;
      return (Date.now() - d.getTime()) / 1000 <= maxSeconds;
    },

    metrics(data) {
      document.getElementById("m-balance").innerHTML = FMT.usdHtml(data.total_equity);
      document.getElementById("m-balance-sub").innerHTML =
        data.position_count + " open · " + FMT.usdHtml(data.bankroll);

      this._valueCard("m-open-pnl", data.open_pnl, FMT.unrealizedClass);
      const openPct = data.total_equity > 0 ? (data.open_pnl / data.total_equity) * 100 : 0;
      document.getElementById("m-open-pnl-pct").textContent = FMT.pctSigned(openPct, 0);

      this._valueCard("m-realized-pnl", data.realized_pnl, FMT.pnlClass);

      const lockedEl = document.getElementById("m-locked");
      lockedEl.innerHTML = FMT.usdHtml(data.locked);
      lockedEl.className = "card-value locked-color";
      document.getElementById("m-locked-sub").textContent =
        data.position_count + " position" + (data.position_count === 1 ? "" : "s");

      document.getElementById("m-peak").innerHTML = FMT.usdHtml(data.peak_balance);
      const dd = data.drawdown_pct;
      document.getElementById("m-drawdown").innerHTML =
        dd > 0 ? FMT.pctHtml(dd) + " drawdown" : "at peak";
    },

    wlStats(data) {
      document.getElementById("m-wl").textContent =
        (data.wins || 0) + "W / " + (data.losses || 0) + "L";
    },

    _valueCard(id, value, classFn) {
      const el = document.getElementById(id);
      el.innerHTML = FMT.usdSignedHtml(value);
      el.className = "card-value " + classFn(value);
    },

    lossProtection(data) {
      document.getElementById("lp-risk").textContent = FMT.pct(data.risk_pct, 0);
      document.getElementById("lp-down").textContent = FMT.pct(data.down_pct, 0);
      document.getElementById("lp-stop").textContent = FMT.pct(data.stop_at_pct, 0);
      const statusEl = document.getElementById("lp-status");
      statusEl.textContent = data.status;
      const cls = data.status === "Safe" ? "green" : data.status === "Stopped" ? "red" : "amber";
      statusEl.className = "text-" + cls;
      const color = data.status === "Safe" ? COLORS.green
        : data.status === "Stopped" ? COLORS.red : COLORS.orange;
      CHARTS.setGauge("lp", data.risk_pct, color);
    },

    calibration(data) {
      // Matrix canvas (sol taraf: predicted vs actual scatter)
      _drawCalibrationMatrix(data);
      // Skor
      const scoreEl = document.getElementById("calib-score");
      if (data.overall_score_pct !== null && data.overall_score_pct !== undefined) {
        scoreEl.textContent = data.overall_score_pct.toFixed(0);
      } else {
        scoreEl.textContent = "—";
      }
      // Last calculated — format "2 Jun 15:30" (low opacity, beside title)
      const updEl = document.getElementById("calib-updated");
      if (data.last_updated_ts) {
        const d = new Date(data.last_updated_ts * 1000);
        const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
        const day = d.getDate();
        const mon = months[d.getMonth()];
        const hh = String(d.getHours()).padStart(2, "0");
        const mm = String(d.getMinutes()).padStart(2, "0");
        updEl.textContent = "Last calculated " + day + " " + mon + " " + hh + ":" + mm;
      } else {
        updEl.textContent = "Not yet computed";
      }
      // Bin satırları — YETERSIZ VERIDE DE iskelet göster, bar'lar dolar
      const binsEl = document.getElementById("calib-bins");
      // English labels mapping
      const LABELS = {
        underdog:     "Underdog call",
        hafif_favori: "Slight favorite",
        net_favori:   "Clear favorite",
        ezici_favori: "Heavy favorite",
      };
      const NOTES = {
        "Dogru tahmin": "On target",
        "Henuz veri yok": "Awaiting data",
      };

      binsEl.innerHTML = data.bins.map((b) => {
        const label = LABELS[b.bin] || b.label;
        if (b.status === "pending") {
          // Order: header → text → progress bar (bottom)
          const progressPct = Math.min(100, (b.n / data.min_trades_per_bin) * 100);
          return '<div class="calib-bin pending">' +
            '<div class="calib-bin-row">' +
              '<span class="calib-bin-label">' + label +
                ' <span class="calib-bin-range">(' + b.range_pct + '%)</span></span>' +
              '<span class="calib-bin-note">' + b.n + '/' + data.min_trades_per_bin + ' trades</span>' +
            '</div>' +
            '<div class="calib-bin-detail">Waiting for predictions to resolve</div>' +
            '<div class="calib-double-bar">' +
              '<div class="calib-bar"><div class="calib-bar-fill" style="width:' + progressPct + '%"></div></div>' +
            '</div>' +
          '</div>';
        }
        let note = b.note.replace("Dogru tahmin", "On target")
          .replace(/(\d+) puan iyimser — buyuk sapma/, "$1pp optimistic — large gap")
          .replace(/(\d+) puan temkinli — buyuk sapma/, "$1pp cautious — large gap")
          .replace(/(\d+) puan iyimser/, "$1pp optimistic")
          .replace(/(\d+) puan temkinli/, "$1pp cautious");
        const predictedPct = Math.min(100, Math.max(0, b.predicted_pct));
        const actualPct = Math.min(100, Math.max(0, b.actual_pct));
        // Order: header (label + note) → detail text → bars at bottom
        return '<div class="calib-bin ' + b.status + '">' +
          '<div class="calib-bin-row">' +
            '<span class="calib-bin-label">' + label +
              ' <span class="calib-bin-range">(' + b.range_pct + '%)</span></span>' +
            '<span class="calib-bin-note">● ' + note + '</span>' +
          '</div>' +
          '<div class="calib-bin-detail">' + b.n + ' trades resolved</div>' +
          '<div class="calib-double-bar">' +
            '<div class="calib-bar-row"><span class="calib-bar-name">Predicted</span>' +
              '<div class="calib-bar"><div class="calib-bar-fill predicted" style="width:' + predictedPct + '%"></div></div>' +
              '<span class="calib-bar-val">' + b.predicted_pct + '%</span></div>' +
            '<div class="calib-bar-row"><span class="calib-bar-name">Actual</span>' +
              '<div class="calib-bar"><div class="calib-bar-fill actual" style="width:' + actualPct + '%"></div></div>' +
              '<span class="calib-bar-val">' + b.actual_pct + '%</span></div>' +
          '</div>' +
          '</div>';
      }).join("");
    },
  };

  // ── Calibration matrix (canvas X-Y scatter) ──
  function _drawCalibrationMatrix(data) {
    const canvas = document.getElementById("calib-matrix");
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth || 520;
    const H = canvas.clientHeight || 360;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    // Generous spacing for hierarchy (extra left for rotated axis label)
    const padL = 84, padR = 24, padT = 32, padB = 56;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const FONT_AXIS = '11px "Inter", system-ui, sans-serif';
    const FONT_TICK = '10.5px "Inter", system-ui, sans-serif';
    const FONT_LEGEND = '10px "Inter", system-ui, sans-serif';
    const FONT_LABEL = 'bold 10px "Inter", system-ui, sans-serif';

    // Grid + ticks
    ctx.strokeStyle = "rgba(255,255,255,0.05)";
    ctx.lineWidth = 1;
    ctx.font = FONT_TICK;
    ctx.fillStyle = "rgba(255,255,255,0.4)";
    for (let i = 0; i <= 4; i++) {
      const pct = i * 25;
      const x = padL + (i / 4) * plotW;
      const y = padT + plotH - (i / 4) * plotH;
      ctx.beginPath();
      ctx.moveTo(x, padT); ctx.lineTo(x, padT + plotH);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(padL, y); ctx.lineTo(padL + plotW, y);
      ctx.stroke();
      ctx.textAlign = "center";
      ctx.fillText(pct + "%", x, padT + plotH + 18);
      ctx.textAlign = "right";
      ctx.fillText(pct + "%", padL - 10, y + 4);
    }

    // Ideal diagonal line
    ctx.strokeStyle = "rgba(96, 165, 250, 0.55)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(padL, padT + plotH);
    ctx.lineTo(padL + plotW, padT);
    ctx.stroke();
    ctx.setLineDash([]);

    // Axis labels — well-spaced from ticks
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.font = FONT_AXIS;
    ctx.textAlign = "center";
    ctx.fillText("Predicted probability", padL + plotW / 2, H - 14);
    ctx.save();
    ctx.translate(20, padT + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("Actual win rate", 0, 0);
    ctx.restore();

    // Bin dots
    const colors = {
      green: "#4ade80", yellow: "#fbbf24", red: "#f87171",
      pending: "rgba(255,255,255,0.3)",
    };
    data.bins.forEach((b) => {
      const lo = parseInt(b.range_pct.split("-")[0]);
      const hi = parseInt(b.range_pct.split("-")[1]);
      const predicted = b.predicted_pct != null ? b.predicted_pct : (lo + hi) / 2;
      const actual = b.actual_pct != null ? b.actual_pct : (lo + hi) / 2;
      const x = padL + (predicted / 100) * plotW;
      const y = padT + plotH - (actual / 100) * plotH;
      const isPending = b.status === "pending";
      const r = isPending ? 7 : 9 + Math.min(7, b.n / 5);
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = colors[b.status] || colors.pending;
      ctx.globalAlpha = isPending ? 0.35 : 0.92;
      ctx.fill();
      ctx.strokeStyle = "rgba(0,0,0,0.45)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.globalAlpha = 1;
      if (!isPending && b.n >= 10) {
        ctx.fillStyle = "rgba(0,0,0,0.75)";
        ctx.font = FONT_LABEL;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(b.n, x, y);
        ctx.textBaseline = "alphabetic";
      }
    });

    // Legend — top, well-spaced
    ctx.font = FONT_LEGEND;
    ctx.textAlign = "left";
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.fillText("- - -  Ideal calibration (model = actual)", padL + 4, padT - 12);
  }

  // ── Session start (topbar opasite 0.6) ──
  // Inline: sadece "1.5d" (uptime). Tam tarih hover tooltip'inde — diger
  // trading app'lerinin yaptigi gibi (compact summary + detail on hover).
  const _MONTHS_TR_SHORT = [
    "Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara",
  ];
  const _MS_PER_DAY = 86400000;
  function _renderSessionStart() {
    const el = document.querySelector(".session-start");
    if (!el) return;
    const iso = el.dataset.iso || "";
    if (!iso) { el.textContent = ""; el.title = ""; return; }
    const d = new Date(iso);
    if (isNaN(d.getTime())) { el.textContent = ""; el.title = ""; return; }
    const ageDays = ((Date.now() - d.getTime()) / _MS_PER_DAY).toFixed(1);
    el.textContent = `${ageDays}d`;
    const day = d.getDate();
    const mon = _MONTHS_TR_SHORT[d.getMonth()];
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    el.title = `Session start: ${day} ${mon} ${hh}:${mm}`;
  }

  // ── MAIN ──
  const MAIN = {
    async refresh() {
      _renderSessionStart();  // Sure ilerlesin: 1.5h -> 2.3h -> 1.0 days ...
      try {
        const [status, summary,
               positions, trades, skipped, stock, stats, sportRoi, calibration] = await Promise.all([
          API.status(), API.summary(),
          API.positions(), API.trades(), API.skipped(), API.stock(),
          API.stats(), API.sportRoi(), API.calibration(),
        ]);
        LAST.trades = Array.isArray(trades) ? trades : [];  // cache for tab clicks
        RENDER.status(status);
        RENDER.metrics(summary.equity);
        RENDER.wlStats(stats);
        RENDER.calibration(calibration);
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
    init() {
      _initColors();
      global.COLORS = COLORS;  // modal JS needs palette access
      _renderSessionStart();
      CHARTS.initAll();
      global.CHART_TABS.bind({
        charts: CHARTS,
        state: CHART_STATE,
        cache: LAST,
        initialBankroll: INITIAL_BANKROLL,
        render: RENDER,
        idleTickMs: CONFIG.idleTickMs,
      });
      global.FEED.bindTabs();
      this.refresh();
      setInterval(() => this.refresh(), CONFIG.pollIntervalMs);
    },
  };
  document.addEventListener("DOMContentLoaded", () => MAIN.init());
})(window);
