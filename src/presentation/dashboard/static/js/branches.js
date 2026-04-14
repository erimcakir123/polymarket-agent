/* Branches (Sport ROI Treemap) — dashboard Branşlar kartı.
 *
 * Her lig bir block; alan = invested oranı (flex-grow), renk = ROI.
 * Tooltip: trades/WR/net PnL/ROI/avg size.
 *
 * Bağımlılık: FMT (dashboard.js'te global) — decimal span + usdSigned vb.
 */
(function (global) {
  "use strict";

  const LARGE_SHARE_THRESHOLD = 0.12;  // Blok >= %12 ise ekstra satır göster

  const BRANCHES = {
    render(data) {
      this._renderTree(data.leagues || []);
    },

    _renderTree(leagues) {
      const tree = document.getElementById("branches-tree");
      if (!tree) return;
      if (leagues.length === 0) {
        tree.innerHTML = '<div class="feed-empty">No closed trades yet.</div>';
        return;
      }
      const totalInvested = leagues.reduce((sum, l) => sum + (l.invested || 0), 0);
      tree.innerHTML = leagues.map((l) => {
        const share = totalInvested > 0 ? (l.invested / totalInvested) : 0;
        return this._block(l, share);
      }).join("");
    },

    _block(l, share) {
      const bg = this._colorFor(l.roi || 0);
      const roiStr = FMT.pctSigned(l.roi * 100, 1);
      const pnlStr = (l.net_pnl >= 0 ? "+" : "-") + "$" + Math.abs(l.net_pnl).toFixed(0);
      const showExtra = share >= LARGE_SHARE_THRESHOLD;
      return `<div class="tree-block" style="flex-grow:${Math.max(1, share * 100)};background:${bg}" title="${this._tooltipText(l)}">
        <div class="tree-block-label">${FMT.escapeHtml(l.league || "—")}</div>
        <div class="tree-block-roi">${roiStr}</div>
        <div class="tree-block-sub">${pnlStr}</div>
        ${showExtra
          ? `<div class="tree-block-sub">${l.trades} trades · ${Math.round((l.win_rate || 0) * 100)}% WR</div>`
          : ""}
      </div>`;
    },

    _colorFor(roi) {
      // Near zero: mavi tint (unrealized pnl mavisi #3b82f6)
      // +: yeşil → koyu yeşil; −: kırmızı → koyu kırmızı
      if (Math.abs(roi) < 0.02) return "rgba(59, 130, 246, 0.32)";
      const intensity = Math.min(1, Math.abs(roi) / 0.3);
      if (roi > 0) return `rgba(34, 197, 94, ${0.18 + intensity * 0.55})`;
      return `rgba(239, 68, 68, ${0.18 + intensity * 0.55})`;
    },

    _tooltipText(l) {
      const roiPct = (l.roi * 100).toFixed(1);
      const wr = Math.round((l.win_rate || 0) * 100);
      const pnl = (l.net_pnl >= 0 ? "+$" : "-$") + Math.abs(l.net_pnl).toFixed(2);
      const avg = "$" + (l.avg_size || 0).toFixed(0);
      return FMT.escapeHtml(
        `${l.league}\n` +
        `Trades: ${l.trades} (${l.wins}W / ${l.losses}L)\n` +
        `Win rate: ${wr}%\n` +
        `Net P&L: ${pnl}\n` +
        `ROI: ${roiPct}%\n` +
        `Avg size: ${avg}`
      );
    },
  };

  global.BRANCHES = BRANCHES;
})(window);
