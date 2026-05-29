/* Trade Log Modal — basit liste, hafta navigation YOK, chart YOK.
 *
 * Namespace: TRADE_HISTORY (global) — public API geriye uyumlu.
 * Dependencies: FMT (fmt.js), ICONS (icons.js).
 *
 * Tum trade'leri /api/trades?n=5000 ile cekip kronolojik tabloda gosterir.
 * 2026-05-29: SPEC eski week-nav + chart/list tab'li modali sadelestirdi.
 */
(function (global) {
  "use strict";

  const _MONTH = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"];
  const _LOG_FETCH_LIMIT = 5000;

  let _overlay = null;

  function _createOverlay() {
    const ov = document.createElement("div");
    ov.className = "modal-overlay";
    ov.innerHTML = `
      <div class="modal-container modal-container--log">
        <div class="modal-header">
          <h2>Trade Log</h2>
          <button class="modal-close" id="modal-close">&times;</button>
        </div>
        <div class="modal-view">
          <div class="modal-table-wrap" id="modal-table-wrap"></div>
        </div>
      </div>`;
    document.body.appendChild(ov);
    ov.addEventListener("click", (e) => { if (e.target === ov) _close(); });
    ov.querySelector("#modal-close").addEventListener("click", _close);
    return ov;
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
    if (!trades || !trades.length) {
      wrap.innerHTML = '<div class="modal-empty">No trades yet.</div>';
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
        <td class="${cls}">${FMT.usdSignedHtml(pnl)}</td>
        <td>${_reasonBadge(t.exit_reason, pnl)}</td>
      </tr>`;
    }).join("");
    wrap.innerHTML =
      `<table class="modal-table"><tbody>${rows}</tbody></table>`;
  }

  async function _load() {
    const wrap = document.getElementById("modal-table-wrap");
    if (wrap) wrap.innerHTML = '<div class="modal-empty">Loading...</div>';
    try {
      const r = await fetch("/api/trades?n=" + _LOG_FETCH_LIMIT + "&_=" + Date.now());
      if (!r.ok) throw new Error(r.status);
      const trades = await r.json();
      _renderTable(trades);
    } catch (e) {
      console.error("Trade log load error:", e);
      if (wrap) {
        wrap.innerHTML =
          '<div class="modal-empty">Failed to load trades.<br><small>' + String(e) + '</small></div>';
      }
    }
  }

  function _open() {
    if (!_overlay) _overlay = _createOverlay();
    _overlay.style.display = "flex";
    requestAnimationFrame(() => _overlay.classList.add("visible"));
    _load();
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

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-trade-history");
    if (btn) btn.addEventListener("click", _open);
    document.addEventListener("keydown", _onKeydown);
  });

  global.TRADE_HISTORY = { open: _open, close: _close };
})(window);
