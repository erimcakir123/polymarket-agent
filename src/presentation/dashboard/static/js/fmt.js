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
    // Soccer team codes (SPEC-015 3-way). Slug'dan isim üretimi; draw+home+away
    // sub-market'lerin ortak event başlığı için.
    // Argentina (Primera)
    ban: "CA Banfield", bar: "CA Barracas Central", bel: "CA Belgrano",
    cah: "CA Huracán", pla: "CA Platense", rie: "CD Riestra",
    slo: "CA San Lorenzo", tal: "CA Talleres", vel: "CA Vélez Sarsfield",
    riv1: "River Plate",
    // Chile (Primera)
    cuc: "U. Católica", cul: "U. La Calera",
    // Colombia (Primera A)
    ad1: "América de Cali", mif: "Millonarios", onc: "Once Caldas",
    // Denmark (Superliga)
    agf: "Aarhus GF", mid: "FC Midtjylland",
    // England (EPL)
    cry: "Crystal Palace", wes: "West Ham",
    // Spain (Segunda)
    dep: "Dep. La Coruña", mir: "CD Mirandés",
    // France (Ligue 2)
    lav: "Stade Lavallois", usd: "USL Dunkerque",
    // India (Super League)
    pun: "Punjab FC",
    // Peru (Liga 1)
    cs1: "CS Cienciano",
    // Portugal (Primeira)
    est: "Estoril Praia", mor: "Moreirense FC",
    // Romania (Liga 1)
    fcb: "FC Botoşani", fcs: "FCSB", ffc: "Farul Constanţa",
    fmb: "FC Metaloglobus",
    // Italy (Serie A) — "sea" league code
    fio: "Fiorentina", lec: "US Lecce",
    // Turkey (Süper Lig)
    gfk: "Gaziantep FK", kay: "Kayserispor",
    // Ukraine (Premier League)
    ole: "Oleksandriya", pol: "FK Polissia",
    shd: "Shakhtar Donetsk", ver: "Veres Rivne",
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
      // 3-way market slug (<league>-<home>-<away>-<date>-<outcome>) → parent
      // event slug = outcome suffix'i at. Aksi halde 2-way slug aynen geçer.
      const threeWay = String(slug).match(
        /^([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2})-[a-z0-9]+$/i
      );
      const base = threeWay ? threeWay[1] : slug;
      return "https://polymarket.com/event/" + encodeURIComponent(base);
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
      // Soccer 3-way: "Will X vs. Y end in a draw?" → "X vs Y"
      const draw = String(q).match(/^Will\s+(.+?)\s+vs\.?\s+(.+?)\s+end\s+in\s+a\s+draw\??$/i);
      if (draw) return `${draw[1].trim()} vs ${draw[2].trim()}`;
      // Soccer 3-way home/away: "Will X win?" tek takım — slug'a devret
      if (/^Will\s+.+\s+win\??$/i.test(q)) return null;
      const parts = String(q).split(/\s+vs\.?\s+/i);
      if (parts.length !== 2) return null;
      // Turnuva prefix'i (Porsche Tennis Grand Prix: Eva Lys) — son ":" sonrasını al.
      let a = parts[0].trim();
      if (a.includes(":")) a = a.split(":").pop().trim();
      return `${a} vs ${parts[1].trim().replace(/\?$/, "").trim()}`;
    },
    _fromSlug(slug) {
      if (!slug) return null;
      const s = String(slug);
      const team = s.match(/^[a-z0-9]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}$/i);
      if (team) return `${this._expandCode(team[1])} vs ${this._expandCode(team[2])}`;
      // Soccer 3-way: <league>-<home>-<away>-<date>-<outcome> (outcome = home/away code or "draw")
      const threeWay = s.match(/^[a-z0-9]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}-[a-z0-9]+$/i);
      if (threeWay) return `${this._expandCode(threeWay[1])} vs ${this._expandCode(threeWay[2])}`;
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
    // Raw exit_reason → { text, emoji, tone }. Tek kaynak — map burada yaşar.
    // Producer: src/models/enums.py::ExitReason + computed.py scale_out_tier_N synth.
    // Python tarafında yeni reason eklendiğinde bu map'e de branch eklenmeli.
    // tone ∈ { "pos", "neg", "neutral" } → CSS class seçimi.
    exitReasonLabel(raw) {
      const r = String(raw || "");
      if (!r) return { text: "", emoji: "", tone: "neutral" };
      // Partial scale-out: computed.py synth ediyor → scale_out_tier_N → Take Profit.
      // Config'de şu an tek tier (sell_pct 0.40 @ midpoint) — rakam gereksiz.
      // İleride tier sayısı artarsa bu dal tekrar genişletilir.
      if (/^scale_out_tier_\d+$/.test(r)) return { text: "Take Profit", emoji: "🎯", tone: "pos" };
      if (r === "scale_out") return { text: "Take Profit", emoji: "🎯", tone: "pos" };
      if (r === "near_resolve") return { text: "Near resolve", emoji: "✅", tone: "pos" };
      if (r === "market_flip") return { text: "Market flipped", emoji: "🔄", tone: "neg" };
      if (r === "score_exit") return { text: "Score against", emoji: "⚠️", tone: "neg" };
      if (r === "hold_revoked") return { text: "Hold revoked", emoji: "🔓", tone: "neg" };
      if (r === "never_in_profit") return { text: "Never profited", emoji: "🥀", tone: "neg" };
      if (r === "ultra_low_guard") return { text: "Ultra-low guard", emoji: "🛡️", tone: "neg" };
      // Fallback — raw string, neutral
      return { text: r, emoji: "", tone: "neutral" };
    },
    // ms → "Xh Ym" / "Xm" / "Xs" (truncate, do not round up).
    durationShort(ms) {
      if (ms === null || ms === undefined || isNaN(ms) || ms < 0) return "";
      const totalSec = Math.floor(ms / 1000);
      if (totalSec < 60) return totalSec + "s";
      const totalMin = Math.floor(totalSec / 60);
      if (totalMin < 60) return totalMin + "m";
      const h = Math.floor(totalMin / 60);
      const m = totalMin % 60;
      return h + "h " + m + "m";
    },
    // 2-way: BUY_YES → slug home-code, BUY_NO → away-code.
    // 3-way (SPEC-015): son segment bahis ettiğimiz outcome (home/away/draw).
    // Slug eşleşmezse "YES"/"NO" fallback.
    sideCode(direction, slug) {
      const s = String(slug || "");
      // 3-way first (daha uzun pattern, outcome suffix ile biter)
      const threeWay = s.match(
        /^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-([a-z0-9]+)$/i
      );
      if (threeWay) return threeWay[1].toUpperCase();
      // 2-way
      const twoWay = s.match(
        /^[a-z0-9]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}$/i
      );
      if (twoWay) return (direction === "BUY_YES" ? twoWay[1] : twoWay[2]).toUpperCase();
      return direction === "BUY_YES" ? "YES" : "NO";
    },
  };

  global.FMT = FMT;
})(window);
