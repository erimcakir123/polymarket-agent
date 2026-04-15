/* FMT namespace — pure display helpers + TEAM_NAMES map.
 *
 * Tüm fonksiyonlar pure (I/O yok). Döndürülen string'ler HTML-escape'li.
 * Kontrat: docs/dashboard-fmt-contract.md
 */
(function (global) {
  "use strict";

  // Team code → full city/team adı. Slug'dan title üretimi için kullanılır.
  const TEAM_NAMES = {
    // MLB
    ari: "Arizona", atl: "Atlanta", bal: "Baltimore", bos: "Boston",
    chc: "Chi. Cubs", cws: "Chi. Sox", chw: "Chi. Sox", cin: "Cincinnati",
    cle: "Cleveland", col: "Colorado", det: "Detroit", hou: "Houston",
    kc: "Kansas City", kcr: "Kansas City", laa: "LA Angels", lad: "LA Dodgers",
    mia: "Miami", mil: "Milwaukee", min: "Minnesota", nym: "NY Mets",
    nyy: "NY Yankees", oak: "Oakland", phi: "Philadelphia", pit: "Pittsburgh",
    sd: "San Diego", sdp: "San Diego", sf: "San Francisco", sfg: "San Francisco",
    sea: "Seattle", stl: "St. Louis", tb: "Tampa Bay", tbr: "Tampa Bay",
    tex: "Texas", tor: "Toronto", was: "Washington", wsh: "Washington",
    // NHL (çakışan kodlar MLB ile aynı şehir)
    ana: "Anaheim", buf: "Buffalo", cgy: "Calgary", car: "Carolina",
    chi: "Chicago", cbj: "Columbus", dal: "Dallas", edm: "Edmonton",
    fla: "Florida", lak: "LA Kings", mon: "Montreal", mtl: "Montreal",
    nsh: "Nashville", nj: "NJ Devils", njd: "NJ Devils", nyi: "NY Islanders",
    nyr: "NY Rangers", ott: "Ottawa", sj: "San Jose", sjs: "San Jose",
    tbl: "Tampa Bay", van: "Vancouver", vgk: "Vegas", wpg: "Winnipeg",
  };

  const FMT = {
    _splitDecimal(n, digits) {
      const d = digits == null ? 2 : digits;
      const parts = Math.abs(n).toFixed(d).split(".");
      return { intPart: parts[0], decPart: parts[1] || "" };
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
    pctSignedHtml(n, digits) {
      if (n === null || n === undefined || isNaN(n)) return "--";
      const { intPart, decPart } = this._splitDecimal(n, digits);
      const sign = n < 0 ? "-" : "";
      return `${sign}${intPart}<span class="dec">.${decPart}</span>%`;
    },
    pnlClass(n) {
      if (n > 0.001) return "pnl-pos";
      if (n < -0.001) return "pnl-neg";
      return "pnl-zero";
    },
    unrealizedClass(n) {
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
    // Market başlığı — question > slug pattern > slug fallback. HTML-escape'li.
    teamsText(question, slug) {
      return this.escapeHtml(
        this._fromQuestion(question) || this._fromSlug(slug) || (slug || "--")
      );
    },
    _fromQuestion(q) {
      if (!q) return null;
      const parts = String(q).split(/\s+vs\.?\s+/i);
      if (parts.length !== 2) return null;
      return `${parts[0].trim()} vs ${parts[1].trim()}`;
    },
    _fromSlug(slug) {
      if (!slug) return null;
      const s = String(slug);
      const team = s.match(/^[a-z]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}$/i);
      if (team) return `${this._expandCode(team[1])} vs ${this._expandCode(team[2])}`;
      const winner = s.match(/winner-([a-z-]+)$/i);
      if (winner) {
        return winner[1].split("-").map(
          (w) => w.charAt(0).toUpperCase() + w.slice(1)
        ).join(" ");
      }
      return null;
    },
    _expandCode(code) {
      const key = code.toLowerCase();
      if (TEAM_NAMES[key]) return TEAM_NAMES[key];
      return code.length <= 4 ? code.toUpperCase()
        : code.charAt(0).toUpperCase() + code.slice(1).toLowerCase();
    },
    // BUY_YES → slug yes-code; BUY_NO → no-code. Slug eşleşmezse "YES"/"NO".
    sideCode(direction, slug) {
      const m = String(slug || "").match(
        /^[a-z]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}$/i
      );
      if (!m) return direction === "BUY_YES" ? "YES" : "NO";
      return (direction === "BUY_YES" ? m[1] : m[2]).toUpperCase();
    },
  };

  global.FMT = FMT;
})(window);
