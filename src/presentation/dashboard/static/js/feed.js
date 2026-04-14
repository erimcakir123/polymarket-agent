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
      const items = this.state.data[tab] || [];
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

    _title(slug) {
      return `<span class="feed-market">${FMT.escapeHtml(slug || "--")}</span>`;
    },

    _teamsTitle(question, slug) {
      // "Arizona Diamondbacks vs. Baltimore Orioles" → "Diamondbacks vs Orioles"
      if (!question) return FMT.escapeHtml(slug || "--");
      const parts = question.split(/\s+vs\.?\s+/i);
      if (parts.length !== 2) return FMT.escapeHtml(question);
      const shortSide = (s) => {
        const tokens = s.trim().split(/\s+/);
        return tokens[tokens.length - 1] || s;
      };
      return FMT.escapeHtml(`${shortSide(parts[0])} vs ${shortSide(parts[1])}`);
    },

    _confPill(conf) {
      const c = (conf || "?").toUpperCase();
      const cls = c === "A" ? "conf-a" : c === "B" ? "conf-b" : c === "C" ? "conf-c" : "conf-unk";
      return `<span class="feed-conf ${cls}">${c}</span>`;
    },

    _countdownPill(matchStartIso, matchLive) {
      if (!matchStartIso) return "";
      const start = new Date(matchStartIso).getTime();
      if (isNaN(start)) return "";
      const diff = start - Date.now();
      if (diff <= 0) {
        if (matchLive) return `<span class="feed-countdown live">LIVE</span>`;
        return "";
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
      const dir = p.direction === "BUY_YES" ? "YES" : "NO";
      const dirCls = p.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      // Token-native PnL: shares × current_price − size_usdc. Direction-agnostic
      // çünkü current_price pozisyonun token'ına aittir (YES/NO).
      const pnl = p.shares * p.current_price - p.size_usdc;
      const pnlPct = p.size_usdc > 0 ? (pnl / p.size_usdc) * 100 : 0;
      const odds = Math.round((p.anchor_probability || 0) * 1000) / 10;
      return `${this._cardOpen(p.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            <span class="feed-market">${this._teamsTitle(p.question, p.slug)}</span></div>
          <div class="feed-badges">${this._confPill(p.confidence)}<span class="feed-badge ${dirCls}">${dir}</span></div>
        </div>
        <div class="feed-details">
          <span>Entry ${FMT.cents(p.entry_price)}</span>
          <span>Now ${FMT.cents(p.current_price)}</span>
          <span>Odds ${odds.toFixed(1)}%</span>
        </div>
        <div class="feed-impact">
          <div class="feed-impact-bar"><div class="feed-impact-bar-fill${pnl < 0 ? " neg" : ""}"
            style="width:${Math.min(100, Math.abs(pnlPct))}%"></div></div>
          <span class="${FMT.unrealizedClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
        </div>
        <div class="feed-time">
          <span>$${p.size_usdc.toFixed(0)}</span>
          <span class="feed-entry-reason">${p.entry_reason || "normal"}</span>
          ${this._countdownPill(p.match_start_iso, p.match_live)}
        </div>
      </a>`;
    },

    _exitedCard(t) {
      const icon = ICONS.getSportEmoji(t.sport_tag, t.slug);
      const dir = t.direction === "BUY_YES" ? "YES" : "NO";
      const dirCls = t.direction === "BUY_YES" ? "badge-yes" : "badge-no";
      const pnl = Number(t.exit_pnl_usdc || 0);
      return `${this._cardOpen(t.slug)}
        <div class="feed-top">
          <div class="feed-market-wrap"><span class="feed-tick">${icon}</span>
            ${this._title(t.slug)}</div>
          <span class="feed-badge ${dirCls}">${dir}</span>
        </div>
        <div class="feed-details">
          <span>Entry ${FMT.cents(t.entry_price)}</span>
          <span>Exit ${FMT.cents(t.exit_price || 0)}</span>
          <span>${t.exit_reason || ""}</span>
        </div>
        <div class="feed-impact">
          <span class="${FMT.pnlClass(pnl)}">${FMT.usdSignedHtml(pnl)}</span>
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
            ${this._title(s.slug)}</div>
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
            ${this._title(q.slug)}</div>
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
