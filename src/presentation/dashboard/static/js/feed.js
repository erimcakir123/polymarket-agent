/* Trade feed rendering — 4 sekme (Active / Exited / Skipped / Stock).
 *
 * FMT + ICONS global'lerini kullanır (dashboard.js'te tanımlı). God function yok;
 * her tip için ayrı kart render fonksiyonu.
 */
(function (global) {
  "use strict";

  const MAX_ITEMS = 100;
  const MS_PER_MIN = 60000;

  const FEED = {
    state: { tab: "active", data: { active: [], exited: [], skipped: [], stock: [] } },

    bindTabs() {
      document.querySelectorAll(".feed-tab").forEach((btn) => {
        btn.addEventListener("click", () => this.setTab(btn.dataset.tab));
      });
    },

    setTab(tab) {
      this.state.tab = tab;
      document.querySelectorAll(".feed-tab").forEach((b) =>
        b.classList.toggle("active", b.dataset.tab === tab));
      this.render();
    },

    update({ active, exited, skipped, stock }) {
      this.state.data = { active, exited, skipped, stock };
      this.render();
    },

    render() {
      const tab = this.state.tab;
      // Her sekmede en erken maç başı yukarıda. match_start_iso yoksa en sona.
      const items = (this.state.data[tab] || []).slice().sort((a, b) => {
        const aKey = a.match_start_iso || "9999-12-31";
        const bKey = b.match_start_iso || "9999-12-31";
        return aKey.localeCompare(bKey);
      });
      const scroll = document.getElementById("feed-scroll");
      document.getElementById("feed-count").textContent = items.length;
      if (items.length === 0) {
        scroll.innerHTML = '<div class="feed-empty">No ' + tab + " items.</div>";
        return;
      }
      scroll.innerHTML = items.slice(0, MAX_ITEMS).map((it) => this._card(tab, it)).join("");
    },

    _card(tab, it) {
      if (tab === "active") return this._activeCard(it);
      if (tab === "exited") return this._exitedCard(it);
      if (tab === "skipped") return this._skippedCard(it);
      return this._stockCard(it);
    },

    _marketTitle(question, slug) {
      return `<span class="feed-market">${FMT.teamsText(question, slug)}</span>`;
    },

    _confPill(conf) {
      const c = (conf || "?").toUpperCase();
      const cls = c === "A" ? "conf-a" : c === "B" ? "conf-b" : c === "C" ? "conf-c" : "conf-unk";
      return `<span class="feed-conf ${cls}">${FMT.escapeHtml(c)}</span>`;
    },

    _countdownPill(matchStartIso, _matchLive) {
      if (!matchStartIso) return "";
      const start = new Date(matchStartIso).getTime();
      if (isNaN(start)) return "";
      const diff = start - Date.now();
      if (diff <= 0) {
        return `<span class="feed-countdown live">LIVE</span>`;
      }
      const mins = Math.floor(diff / MS_PER_MIN);
      const hours = Math.floor(mins / 60);
      const remMins = mins % 60;
      const label = hours > 0 ? `${hours}h ${remMins}m` : `${mins}m`;
      return `<span class="feed-countdown">${label}</span>`;
    },

    _cardOpen(slug) {
      const url = FMT.polyUrl(slug);
      return `<a class="feed-item" href="${url}" target="_blank" rel="noopener noreferrer">`;
    },

    _activeCard(p) {
      const icon = ICONS.getSportEmoji(p.sport_tag, p.slug);
      const dir = FMT.sideCode(p.direction, p.slug);
      const dirCls = p.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      // Token-native PnL: shares × current_price − size_usdc. Direction-agnostic
      // çünkü current_price pozisyonun token'ına aittir (YES/NO).
      const pnl = p.shares * p.current_price - p.size_usdc;
      const pnlPct = p.size_usdc > 0 ? (pnl / p.size_usdc) * 100 : 0;
      // Odds: direction-adjusted. BUY_NO → (1 − P(YES)). Entry/Now zaten
      // token-native saklanıyor (BUY_NO pozisyonunda NO fiyatı).
      const anchor = p.anchor_probability || 0;
      const oddsRaw = p.direction === "BUY_NO" ? (1 - anchor) : anchor;
      const odds = Math.round(oddsRaw * 1000) / 10;
      return `${this._cardOpen(p.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            ${this._marketTitle(p.question, p.slug)}</div>
          <div class="feed-badges">${this._confPill(p.confidence)}<span class="feed-badge ${dirCls}">${dir}</span></div>
        </div>
        <div class="feed-entry-reason-row">${FMT.escapeHtml(p.entry_reason || "normal")}</div>
        <div class="feed-details">
          <span>Entry ${FMT.cents(p.entry_price)}</span>
          <span>Now ${FMT.cents(p.current_price)}</span>
          <span>Odds ${odds.toFixed(1)}%</span>
        </div>
        <div class="feed-impact">
          <div class="feed-impact-bar" style="--fill:${Math.min(100, Math.abs(pnlPct))}%">
            <div class="feed-impact-bar-fill${pnl < 0 ? " neg" : ""}"></div>
            <span class="feed-pnl-dollar ${FMT.unrealizedClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
            <span class="feed-pnl-pct ${FMT.unrealizedClass(pnl)}">(${FMT.pctSigned(pnlPct, 1)})</span>
          </div>
        </div>
        <div class="feed-time">
          <span>$${p.size_usdc.toFixed(0)}</span>
          ${this._countdownPill(p.match_start_iso, p.match_live)}
        </div>
      </a>`;
    },

    _exitedCard(t) {
      const icon = ICONS.getSportEmoji(t.sport_tag, t.slug);
      const dir = FMT.sideCode(t.direction, t.slug);
      const dirCls = t.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      const pnl = Number(t.exit_pnl_usdc || 0);
      // Partial scale-out event (pozisyon hâlâ açık) — Exit fiyatı yazılmaz,
      // PARTIAL badge + sell_pct gösterilir.
      const isPartial = !!t.partial;
      const exitCell = isPartial
        ? `<span>Partial ${Math.round((t.sell_pct || 0) * 100)}%</span>`
        : `<span>Exit ${FMT.cents(t.exit_price || 0)}</span>`;
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
          <span>Entry ${FMT.cents(t.entry_price)}</span>
          ${exitCell}
        </div>
        <div class="feed-impact">
          <span class="${FMT.pnlClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
          <span class="feed-exit-reason">${FMT.escapeHtml(t.exit_reason || "")}</span>
        </div>
        <div class="feed-time"><span>${FMT.relTime(t.exit_timestamp)}</span>
          <span>${t.final_outcome || ""}</span></div>
      </a>`;
    },

    _skippedCard(s) {
      const icon = ICONS.getSportEmoji(s.sport_tag, s.slug);
      return `${this._cardOpen(s.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            ${this._marketTitle(s.question, s.slug)}</div>
          <span class="feed-badge">SKIP</span>
        </div>
        <div class="feed-details"><span>${s.skip_reason || "?"}</span>
          ${s.skip_detail ? "<span>" + s.skip_detail + "</span>" : ""}</div>
        <div class="feed-time"><span>${FMT.relTime(s.timestamp)}</span></div>
      </a>`;
    },

    _stockCard(q) {
      const icon = ICONS.getSportEmoji(q.sport_tag, q.slug);
      return `${this._cardOpen(q.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            ${this._marketTitle(q.question, q.slug)}</div>
        </div>
        <div class="feed-details">
          <span>YES ${FMT.cents(q.yes_price)}</span>
          <span>Liq $${(q.liquidity || 0).toFixed(0)}</span>
        </div>
        <div class="feed-time"><span>${FMT.relTime(q.match_start_iso)}</span></div>
      </a>`;
    },
  };

  global.FEED = FEED;
})(window);
