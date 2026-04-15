/* PolyAgent Dashboard — core client logic.
 *
 * Modüller: CONFIG, FMT, ICONS, API, CHARTS, RENDER, MAIN.
 * FEED modülü feed.js'te (ayrı dosya, 400-satır kuralı).
 * FMT + ICONS window'a expose edilir → feed.js kullanır.
 */
(function (global) {
  "use strict";

  // ── CONFIG (sabitler — magic number yasağı) ──
  const CONFIG = {
    pollIntervalMs: 5000,
    waterfallMaxBars: 40,
    stageRecentSec: 15,         // stage_at kaç saniyeden yeniyse aktif sayılır
    idleTickMs: 1000,           // idle countdown re-render intervali
    msPerMin: 60000,            // dakika→ms dönüştürme sabiti
    barRadius: 14,              // bar chart köşe yuvarlaması (kart --radius ile aynı)
  };

  const MODE = document.body.dataset.mode || "dry_run";
  const MAX_POSITIONS = parseInt(document.body.dataset.maxPositions || "20", 10);

  // ── FMT (formatters) ──
  // HTML döndürenler (`*Html`) <span class="dec"> ile decimal kısmı %50 opacity.
  const FMT = {
    _splitDecimal(n, digits) {
      const abs = Math.abs(n).toFixed(digits);
      const [i, d] = abs.split(".");
      return { intPart: i, decPart: d || "" };
    },
    usd(n) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      return (n < 0 ? "-" : "") + "$" + Math.abs(n).toFixed(2);
    },
    usdHtml(n) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      const { intPart, decPart } = this._splitDecimal(n, 2);
      const sign = n < 0 ? "-" : "";
      return `${sign}$${intPart}<span class="dec">.${decPart}</span>`;
    },
    usdSigned(n) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      return (n >= 0 ? "+" : "-") + "$" + Math.abs(n).toFixed(2);
    },
    usdSignedHtml(n) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      const { intPart, decPart } = this._splitDecimal(n, 2);
      const sign = n >= 0 ? "+" : "-";
      return `${sign}$${intPart}<span class="dec">.${decPart}</span>`;
    },
    pct(n, digits) {
      digits = digits == null ? 1 : digits;
      if (n === null || n === undefined || isNaN(n)) return "--";
      return n.toFixed(digits) + "%";
    },
    pctHtml(n, digits) {
      digits = digits == null ? 1 : digits;
      if (n === null || n === undefined || isNaN(n)) return "--";
      if (digits === 0) return n.toFixed(0) + "%";
      const { intPart, decPart } = this._splitDecimal(n, digits);
      const sign = n < 0 ? "-" : "";
      return `${sign}${intPart}<span class="dec">.${decPart}</span>%`;
    },
    pnlClass(n) {
      // 0 → beyaz, pozitif → yeşil, negatif → kırmızı.
      if (n > 0.001) return "pnl-pos";
      if (n < -0.001) return "pnl-neg";
      return "pnl-zero";
    },
    unrealizedClass(n) {
      // Open PnL: 0 → beyaz, pozitif → mavi, negatif → kırmızı.
      if (n > 0.001) return "unr-pos";
      if (n < -0.001) return "unr-neg";
      return "pnl-zero";
    },
    time(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    },
    relTime(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      const diffMin = Math.floor((Date.now() - d.getTime()) / 60000);
      if (diffMin < 1) return "just now";
      if (diffMin < 60) return diffMin + "m ago";
      const h = Math.floor(diffMin / 60);
      if (h < 24) return h + "h ago";
      return Math.floor(h / 24) + "d ago";
    },
    polyUrl(slug) {
      if (!slug) return "#";
      return "https://polymarket.com/event/" + encodeURIComponent(slug);
    },
    cents(price) { return Math.round(price * 100) + "¢"; },
    pctSigned(n, digits) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      const d = digits == null ? 0 : digits;
      return (n >= 0 ? "+" : "") + n.toFixed(d) + "%";
    },
    escapeHtml(s) {
      return String(s)
        .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
        .replace(/</g, "&lt;").replace(/>/g, "&gt;");
    },
  };

  // ── ICONS (sport → emoji/img) ──
  const ICONS = {
    getSportEmoji(sportTag, slug) {
      const s = (sportTag || "").toLowerCase();
      const sl = (slug || "").toLowerCase();
      if (s.startsWith("tennis") || sl.startsWith("atp-") || sl.startsWith("wta-") || sl.startsWith("itf-")) {
        return '<img src="/static/icons/tennis.png" alt="🎾">';
      }
      if (s.includes("nba") || s.includes("basketball") || s.includes("wnba") || s.includes("euroleague") || s.includes("ncaab")) return "🏀";
      if (s.includes("nhl") || s.includes("icehockey") || s.includes("khl") || s.includes("shl")) return "🏒";
      if (s === "mlb" || s.includes("baseball") || s.includes("mlb")) return "⚾";
      if (s.includes("nfl") || s.includes("americanfootball")) return "🏈";
      if (s.includes("ufc") || s.includes("mma")) return "🥊";
      if (s.includes("chess") || sl.startsWith("chess")) return "♟️";
      if (s.includes("cricket") || s.includes("ipl") || s.includes("psl")) return "🏏";
      if (s.includes("csgo") || s.includes("cs2") || s.includes("lol") || s.includes("dota") || s.includes("valorant")) return "🎮";
      if (s.includes("golf") || s.includes("pga") || s.includes("lpga")) return "⛳";
      if (s.includes("rugby") || s.includes("nrl")) return "🏉";
      if (s.includes("soccer") || s.includes("football") || this._isSoccer(sl)) return "⚽";
      return "🎯";
    },
    _isSoccer(sl) {
      const prefixes = ["uel-", "ucl-", "epl-", "uefa", "tur-", "esp-", "ita-", "ger-", "fra-",
        "bra-", "arg-", "mex-", "por-", "ned-", "mls-", "jpn-", "fifa", "eng-"];
      return prefixes.some((p) => sl.startsWith(p));
    },
  };

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
  };

  // ── CHARTS (Chart.js) ──
  const COLORS = {
    green: "#22c55e",
    red: "#ef4444",
    amber: "#f59e0b",
    blue: "#3b82f6",
    teal: "#14b8a6",
    muted: "#64748b",
    track: "rgba(148, 163, 184, 0.08)",
    gridLine: "rgba(148, 163, 184, 0.06)",
    axisLabel: "rgba(148, 163, 184, 0.5)",
  };

  const CHARTS = {
    equity: null, waterfall: null, lp: null, slots: null,

    initAll() {
      this._initLine("equity-chart", "equity", COLORS.green, "rgba(34, 197, 94, 0.14)");
      this._initBar("waterfall-chart", "waterfall");
      this._initGauge("lp-gauge", "lp", COLORS.green);
      this._initGauge("slots-gauge", "slots", COLORS.blue);
    },

    _initLine(canvasId, key, border, fill) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      this[key] = new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{
          data: [], borderColor: border, backgroundColor: fill,
          borderWidth: 2, tension: 0.3, fill: true, pointRadius: 0,
        }] },
        options: this._baseOpts(true),
      });
    },

    _initBar(canvasId, key) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      this[key] = new Chart(ctx, {
        type: "bar",
        data: { labels: [], datasets: [{ data: [], backgroundColor: [],
          borderRadius: CONFIG.barRadius, borderSkipped: false }] },
        options: this._baseOpts(true),
      });
    },

    _baseOpts(showY) {
      return {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: {
          x: { display: false, grid: { display: false } },
          y: { display: showY, grid: { color: COLORS.gridLine },
            ticks: { color: COLORS.axisLabel, font: { size: 10 } } },
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

    setEquity(series) {
      this.equity.data.labels = series.map((s) => s.timestamp || "");
      this.equity.data.datasets[0].data = series.map((s) =>
        (s.bankroll || 0) + (s.invested || 0) + (s.unrealized_pnl || 0));
      this.equity.update("none");
    },

    setWaterfall(trades) {
      const limited = trades.slice(0, CONFIG.waterfallMaxBars).reverse();
      this.waterfall.data.labels = limited.map((_, i) => String(i + 1));
      const data = limited.map((t) => Number(t.exit_pnl_usdc || 0));
      this.waterfall.data.datasets[0].data = data;
      // Default: soluk (Branches paleti — hover'sız bar'lar daha koyu görünür)
      this.waterfall.data.datasets[0].backgroundColor =
        data.map((v) => (v >= 0 ? "rgba(34, 197, 94, 0.5)" : "rgba(239, 68, 68, 0.5)"));
      // Hover: parlak full renk
      this.waterfall.data.datasets[0].hoverBackgroundColor =
        data.map((v) => (v >= 0 ? COLORS.green : COLORS.red));
      this.waterfall.update("none");
    },
  };

  // ── RENDER (DOM updates) ──
  const RENDER = {
    status(data) {
      // Light cycle: Online (bot canlı) / Offline
      const botAlive = !!data.bot_alive;
      this._applyCycle("cg-light", "light",
        botAlive ? "Online" : "Offline", botAlive);

      // Hard cycle: stage'e göre etiket
      if (!botAlive) {
        this._applyCycle("cg-hard", "offline", "Offline", false);
        return;
      }
      const stage = (data.stage || "").toLowerCase();
      const stageRecent = this._isRecent(data.stage_at, CONFIG.stageRecentSec);
      let label, live;
      if (stage === "scanning" && stageRecent) { label = "Scanning"; live = true; }
      else if (stage === "analyzing" && stageRecent) { label = "Analyzing"; live = true; }
      else if (stage === "executing" && stageRecent) { label = "Executing"; live = true; }
      else if (stage === "idle" || !stageRecent) {
        label = this._idleLabel(data.next_heavy_at);
        live = false;
      }
      else { label = "Waiting"; live = false; }
      this._applyCycle("cg-hard", "hard", label, live);
    },

    _idleLabel(nextHeavyIso) {
      if (!nextHeavyIso) return "Idle";
      const target = new Date(nextHeavyIso).getTime();
      if (isNaN(target)) return "Idle";
      const diff = Math.max(0, target - Date.now());
      const mins = Math.floor(diff / CONFIG.msPerMin);
      const secs = Math.floor((diff % CONFIG.msPerMin) / 1000);
      const mm = String(mins).padStart(2, "0");
      const ss = String(secs).padStart(2, "0");
      return `Idle - next ${mm}:${ss}`;
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
        : data.status === "Stopped" ? COLORS.red : COLORS.amber;
      CHARTS.setGauge("lp", data.risk_pct, color);
    },

    slots(data) {
      document.getElementById("slots-current").textContent = data.current;
      document.getElementById("slots-max").textContent = data.max;
      const pct = data.max > 0 ? (data.current / data.max) * 100 : 0;
      CHARTS.setGauge("slots", pct, COLORS.blue);
      const tags = [
        { key: "normal", label: "NOR", cls: "tag-nor" },
        { key: "volatility_swing", label: "VS", cls: "tag-vs" },
        { key: "consensus", label: "CON", cls: "tag-con" },
        { key: "early", label: "EAR", cls: "tag-ear" },
      ];
      document.getElementById("slot-tags").innerHTML = tags.map((t) => {
        const n = data.by_reason[t.key] || 0;
        const activeCls = n > 0 ? " active" : "";
        return '<span class="slot-tag ' + t.cls + activeCls + '">' + t.label + " " + n + "</span>";
      }).join("");
    },

  };

  // ── MAIN ──
  const MAIN = {
    async refresh() {
      try {
        const [status, summary, equityHistory,
               positions, trades, skipped, stock, stats, sportRoi] = await Promise.all([
          API.status(), API.summary(),
          API.equityHistory(), API.positions(), API.trades(), API.skipped(), API.stock(),
          API.stats(), API.sportRoi(),
        ]);
        RENDER.status(status);
        RENDER.metrics(summary.equity);
        RENDER.wlStats(stats);
        RENDER.slots(summary.slots);
        RENDER.lossProtection(summary.loss_protection);
        CHARTS.setEquity(equityHistory);
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

    init() {
      document.getElementById("slots-max").textContent = MAX_POSITIONS;
      CHARTS.initAll();
      global.FEED.bindTabs();
      this.refresh();
      setInterval(() => this.refresh(), CONFIG.pollIntervalMs);
    },
  };

  // ── Expose for feed.js ──
  global.FMT = FMT;
  global.ICONS = ICONS;

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

  document.addEventListener("DOMContentLoaded", () => MAIN.init());
})(window);
