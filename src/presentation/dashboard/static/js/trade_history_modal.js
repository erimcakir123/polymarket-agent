/* Trade Log Modal — basit liste, hafta navigation YOK, chart YOK.
 *
 * Namespace: TRADE_HISTORY (global) — public API geriye uyumlu.
 * Dependencies: FMT (fmt.js), ICONS (icons.js).
 *
 * Tum trade'leri /api/trades/positions?n=5000 ile cekip pozisyon-bazli
 * (her bahis = 1 baslik, scale-out'lar alt-event) kart listesinde gosterir.
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

  function _dirBadge(direction, slug) {
    const isYes = direction === "BUY_YES";
    const cls = isYes ? "modal-dir--yes" : "modal-dir--no";
    // Metin = oynanan taraf (takım/oyuncu kodu); slug çözülemezse YES/NO fallback.
    return `<span class="modal-dir ${cls}">${FMT.escapeHtml(FMT.sideCode(direction, slug))}</span>`;
  }

  function _totalPnl(t) {
    let total = Number(t.exit_pnl_usdc || 0);
    const partials = Array.isArray(t.partial_exits) ? t.partial_exits : [];
    for (const p of partials) total += Number(p.realized_pnl_usdc || 0);
    return total;
  }

  function _formatDate(iso) {
    if (!iso) return "--";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "--";
    return `${d.getDate()} ${_MONTH[d.getMonth()]} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
  }

  // Giriş → çıkış fiyat akışı: "girdi 42¢ → sattı 51¢". Giriş fiyatı pozisyon
  // boyunca sabit; her alt-satır o adımda kaça satıldığını gösterir.
  function _priceFlow(entryPrice, exitPrice) {
    const e = (entryPrice !== undefined && entryPrice !== null) ? FMT.cents(entryPrice) : "--";
    const x = (exitPrice !== undefined && exitPrice !== null) ? FMT.cents(exitPrice) : "--";
    // Etiketler ("entry"/"→ sold") muted; fiyatlar belirgin kalır.
    return `<span class="trade-flow-lbl">entry</span> ${e} <span class="trade-flow-lbl">→ sold</span> ${x}`;
  }

  // Veri alanlarını ince dikey ayraçla birleştir (boş parçalar atlanır).
  function _joinDiv(parts) {
    return parts.filter(Boolean).join('<i class="trade-div"></i>');
  }

  // Market tipi etiketi (ML / TOTAL / SPREAD / tenis varyantları) — fmt.js tek kaynak.
  function _marketBadge(question, slug, sportsMarketType) {
    const m = FMT.marketType(question, slug, sportsMarketType);
    return m ? `<span class="trade-card-mkt">${FMT.escapeHtml(m)}</span>` : "";
  }

  function _renderSubRow(p, idx, entryPrice) {
    const pnl = Number(p.realized_pnl_usdc || 0);
    const cls = pnl >= 0 ? "pnl-pos" : "pnl-neg";
    // Partial exit = scale-out. Emoji + etiket tek kaynaktan (fmt.js scale_out
    // branch'i PnL işaretine göre 🎯 Take Profit / 🔻 Partial sell döndürür).
    const label = FMT.exitReasonLabel("scale_out", pnl);
    const emoji = label.emoji ? label.emoji + " " : "";
    const sellPct = (p.sell_pct !== undefined && p.sell_pct !== null && Number(p.sell_pct) > 0)
      ? `%${(Number(p.sell_pct) * 100).toFixed(0)}` : "--";
    const tier = p.tier ? `T${p.tier}` : `#${idx + 1}`;
    const right = _joinDiv([
      `<span class="trade-sub-pct">${sellPct}</span>`,
      `<span class="trade-sub-flow">${_priceFlow(entryPrice, p.price)}</span>`,
      `<span class="trade-sub-time">${_formatDate(p.timestamp)}</span>`,
      `<span class="trade-sub-pnl ${cls}">${FMT.usdSignedHtml(pnl)}</span>`,
    ]);
    return `<div class="trade-sub-row">
      <span class="trade-sub-tag">${emoji}${tier} · ${FMT.escapeHtml(label.text)}</span>
      <span class="trade-sub-right">${right}</span>
    </div>`;
  }

  function _renderFinalSubRow(t) {
    if (t.exit_price === null || t.exit_price === undefined) return "";
    const pnl = Number(t.exit_pnl_usdc || 0);
    const cls = pnl >= 0 ? "pnl-pos" : "pnl-neg";
    // Final çıkış: emoji'li sebep etiketi tek kaynaktan (fmt.js exitReasonLabel).
    const label = FMT.exitReasonLabel(t.exit_reason, pnl);
    const emoji = label.emoji ? label.emoji + " " : "";
    const text = label.text || (t.exit_reason || "exit");
    const right = _joinDiv([
      `<span class="trade-sub-pct">--</span>`,
      `<span class="trade-sub-flow">${_priceFlow(t.entry_price, t.exit_price)}</span>`,
      `<span class="trade-sub-time">${_formatDate(t.exit_timestamp)}</span>`,
      `<span class="trade-sub-pnl ${cls}">${FMT.usdSignedHtml(pnl)}</span>`,
    ]);
    return `<div class="trade-sub-row trade-sub-row--final">
      <span class="trade-sub-tag">${emoji}final · ${FMT.escapeHtml(text)}</span>
      <span class="trade-sub-right">${right}</span>
    </div>`;
  }

  function _renderCard(t, idx) {
    const total = _totalPnl(t);
    const cls = total >= 0 ? "pnl-pos" : "pnl-neg";
    const icon = global.ICONS ? global.ICONS.getSportEmoji(t.sport_tag, t.slug) : "";
    const partials = Array.isArray(t.partial_exits) ? t.partial_exits : [];
    const hasFinal = t.exit_price !== null && t.exit_price !== undefined;
    const subCount = partials.length + (hasFinal ? 1 : 0);
    const subRows = partials.map((p, i) => _renderSubRow(p, i, t.entry_price)).join("")
      + _renderFinalSubRow(t);
    // Açık pozisyon: "Opened: <giriş>". Kapanmış: "<giriş> → <çıkış>".
    const entryT = _formatDate(t.entry_timestamp);
    const timesText = t.exit_timestamp
      ? `${entryT} → ${_formatDate(t.exit_timestamp)}`
      : `Opened: ${entryT}`;
    const right = _joinDiv([
      t.direction ? _dirBadge(t.direction, t.slug) : "",
      `<span class="trade-card-times">${timesText}</span>`,
      _reasonBadge(t.exit_reason, total),
      `<span class="trade-card-sub-count">${subCount} part${subCount === 1 ? "" : "s"}</span>`,
      `<span class="trade-card-pnl ${cls}">${FMT.usdSignedHtml(total)}</span>`,
    ]);
    return `<div class="trade-card" data-idx="${idx}">
      <button class="trade-card-head" type="button" aria-expanded="false">
        <span class="trade-card-left">
          <span class="trade-card-caret">▶</span>
          <span class="trade-card-icon">${icon}</span>
          <span class="trade-card-teams">${FMT.teamsText(t.question, t.slug)}</span>
          ${_marketBadge(t.question, t.slug, t.sports_market_type)}
        </span>
        <span class="trade-card-right">${right}</span>
      </button>
      <div class="trade-card-body">${subRows || '<div class="trade-sub-empty">No sub-events</div>'}</div>
    </div>`;
  }

  function _bindCardToggles(wrap) {
    wrap.querySelectorAll(".trade-card-head").forEach((btn) => {
      btn.addEventListener("click", () => {
        const card = btn.closest(".trade-card");
        if (!card) return;
        const expanded = card.classList.toggle("expanded");
        btn.setAttribute("aria-expanded", expanded ? "true" : "false");
      });
    });
  }

  function _renderTable(trades) {
    const wrap = document.getElementById("modal-table-wrap");
    if (!trades || !trades.length) {
      wrap.innerHTML = '<div class="modal-empty">No trades yet.</div>';
      return;
    }
    // Gün sınırına ayraç: liste exit zamanına göre sıralı → YEREL exit tarihi
    // değişince araya çizgi (sadece exit_timestamp güvenilir; entry boş olabilir).
    let prevDay = null;
    const cards = trades.map((t, i) => {
      const day = FMT.localDay(t.exit_timestamp || t.entry_timestamp);
      const sep = prevDay !== null && day && day !== prevDay
        ? '<div class="trade-day-sep" aria-hidden="true"></div>' : "";
      prevDay = day;
      return sep + _renderCard(t, i);
    }).join("");
    wrap.innerHTML = `<div class="trade-card-list">${cards}</div>`;
    _bindCardToggles(wrap);
  }

  async function _load() {
    const wrap = document.getElementById("modal-table-wrap");
    if (wrap) wrap.innerHTML = '<div class="modal-empty">Loading...</div>';
    try {
      const r = await fetch("/api/trades/positions?n=" + _LOG_FETCH_LIMIT + "&_=" + Date.now());
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
