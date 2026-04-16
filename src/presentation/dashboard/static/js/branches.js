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
  const NEAR_ZERO_ROI = 0.02;

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
      const sorted = [...leagues].sort((a, b) => Math.abs(b.roi || 0) - Math.abs(a.roi || 0));
      tree.innerHTML = sorted.map((l) => {
        const share = totalInvested > 0 ? (l.invested / totalInvested) : 0;
        return this._block(l, share);
      }).join("");
    },

    _block(l, share) {
      const roi = l.roi || 0;
      const roiStr = (roi >= 0 ? "+" : "") + (roi * 100).toFixed(0) + "%";
      const pnlSign = l.net_pnl >= 0 ? "+" : "-";
      const pnlStr = `${pnlSign}$${Math.abs(l.net_pnl).toFixed(0)} / $${(l.invested || 0).toFixed(0)}`;
      const wr = Math.round((l.win_rate || 0) * 100);
      const ties = Math.max(0, (l.trades || 0) - (l.wins || 0) - (l.losses || 0));
      const showExtra = share >= LARGE_SHARE_THRESHOLD;
      const cls = this._classFor(roi);
      const tip = FMT.escapeHtml(
        `Win rate: ${wr}% · ${l.wins}W / ${l.losses}L` + (ties > 0 ? ` / ${ties}T` : "")
      );
      const grow = roi > 0 ? roi * 100 : 1;
      return `<div class="tree-block ${cls}" style="flex-grow:${grow}" data-tip="${tip}">
        <div class="tree-block-label">${FMT.escapeHtml(l.league || "—")}</div>
        <div class="tree-block-roi">${roiStr}</div>
        <div class="tree-block-sub">${pnlStr}</div>
        ${showExtra ? `<div class="tree-block-sub">${l.trades} trades</div>` : ""}
      </div>`;
    },

    _classFor(roi) {
      if (Math.abs(roi) < NEAR_ZERO_ROI) return "tree-blue";
      return roi > 0 ? "tree-green" : "tree-red";
    },
  };

  global.BRANCHES = BRANCHES;
})(window);
