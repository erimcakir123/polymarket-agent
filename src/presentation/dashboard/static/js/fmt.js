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
    // NBA (MLB/NHL ile çakışmayanlar — bos/hou/det/mil/min/phi/was/tor/cle/atl
    // mevcut MLB/NHL kayıtlarından şehir adını alır)
    bkn: "Brooklyn", cha: "Charlotte", den: "Denver", gsw: "Golden State",
    ind: "Indiana", lac: "LA Clippers", lal: "LA Lakers", mem: "Memphis",
    nop: "New Orleans", nyk: "NY Knicks", okc: "Oklahoma City", orl: "Orlando",
    phx: "Phoenix", por: "Portland", sac: "Sacramento", sas: "San Antonio",
    uta: "Utah",
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
      // Market slug → parent event slug. Tarih (YYYY-MM-DD) sonrasındaki tüm
      // market suffix'i (3-way outcome, NBA/NFL spread, MLB total, vb.) atılır.
      // Polymarket'te bet sayfası event seviyesinde açılır.
      const m = String(slug).match(
        /^([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2})(?:-.+)?$/i
      );
      const base = m ? m[1] : slug;
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
    // Market başlığı — match_title (backend 3-way enrichment) > question >
    // slug fallback. HTML-escape'li. SPEC-015: soccer/rugby/afl/handball 3-way
    // home/away sub-market'inin ham question'ı tek takım taşır; backend draw
    // sub-market'inden türetilen "X vs Y" match_title'ı tercih edilir.
    teamsText(question, slug, matchTitle) {
      return this.escapeHtml(
        (matchTitle && String(matchTitle).trim())
        || this._fromQuestion(question)
        || this._fromSlug(slug)
        || (slug || "--")
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
      // Unified pattern: <league>-<t1>-<t2>-YYYY-MM-DD ile başlar, tarih sonrası
      // suffix opsiyonel — hem 2-way moneyline (suffix yok), hem soccer 3-way
      // outcome (`-arsenal`/`-draw`), hem NBA spread (`-spread-away-4pt5`),
      // hem MLB total (`-total-over-8pt5`) tek regex ile yakalanır.
      const team = s.match(/^[a-z0-9]+-([a-z0-9]{2,15})-([a-z0-9]{2,15})-\d{4}-\d{2}-\d{2}(?:-.+)?$/i);
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
    // Market type kısa etiketi — kart badge'inde gösterilir.
    // 2026-05-31: sports_market_type field'i öncelikli (backend canonical),
    // sonra question prefix'i, en son slug suffix'i.
    // Tennis 6 ek tipi: set_handicap, set_totals, match_totals, first_set_winner,
    // first_set_totals, completed_match.
    marketType(question, slug, sportsMarketType) {
      const smt = String(sportsMarketType || "").toLowerCase();
      if (smt === "moneyline") return "ML";
      if (smt === "spreads") return "SPREAD";
      if (smt === "totals") return "TOTAL";
      if (smt === "tennis_set_handicap") return "SET HCP";
      if (smt === "tennis_set_totals") return "SET O/U";
      if (smt === "tennis_match_totals") return "MATCH O/U";
      if (smt === "tennis_first_set_winner") return "1ST SET";
      if (smt === "tennis_first_set_totals") return "1ST SET O/U";
      if (smt === "tennis_completed_match") return "FULL";
      const q = String(question || "");
      if (/^Spread\b/i.test(q)) return "SPREAD";
      if (/^Total\b/i.test(q)) return "TOTAL";
      if (/^Moneyline\b/i.test(q)) return "ML";
      if (/end\s+in\s+a\s+draw\??$/i.test(q)) return "DRAW";
      if (/^Will\s+.+\s+win\??$/i.test(q)) return "WIN";
      const s = String(slug || "");
      const suffix = s.match(/^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}-([a-z]+)/i);
      if (!suffix) return "ML";
      const tag = suffix[1].toLowerCase();
      if (tag === "spread") return "SPREAD";
      if (tag === "total") return "TOTAL";
      if (tag === "draw") return "DRAW";
      return "WIN";
    },
    // Raw exit_reason → { text, emoji, tone }. Tek kaynak — map burada yaşar.
    // Producer: src/models/enums.py::ExitReason + computed.py scale_out_tier_N synth.
    // Spor-specific bloklar: NHL (moneyline/puck-line/totals), Tennis, MLB (moneyline/run-line/totals).
    // Python tarafında yeni reason eklendiğinde bu map'e de branch eklenmeli.
    // tone ∈ { "pos", "neg", "neutral" } → CSS class seçimi.
    exitReasonLabel(raw, pnl) {
      const r = String(raw || "");
      if (!r) return { text: "", emoji: "", tone: "neutral" };
      // Scale-out: scale_out_tier_N synth ediyor computed.py'de. Etiket PnL'ye
      // göre kâr ise "Take Profit", zarar ise "Partial sell" (kullanıcı talebi
      // 2026-06-02: aynı pozisyonun zararlı kademe çıkışına "Take Profit" yazmak
      // yanıltıcı — ekrana hangi anlamla satış yapıldığı PnL işaretiyle eşleşsin).
      const isLoss = typeof pnl === "number" && pnl < 0;
      if (/^scale_out_tier_\d+$/.test(r) || r === "scale_out") {
        return isLoss
          ? { text: "Partial sell", emoji: "🔻", tone: "neg" }
          : { text: "Take Profit", emoji: "🎯", tone: "pos" };
      }
      if (r === "near_resolve") return { text: "Near resolve", emoji: "✅", tone: "pos" };
      if (r === "market_flip") return { text: "Market flipped", emoji: "🔄", tone: "neg" };
      if (r === "score_exit") return { text: "Score against", emoji: "⚠️", tone: "neg" };
      if (r === "hold_revoked") return { text: "Hold revoked", emoji: "🔓", tone: "neg" };
      if (r === "never_in_profit") return { text: "Never profited", emoji: "🥀", tone: "neg" };
      if (r === "ultra_low_guard") return { text: "Ultra-low guard", emoji: "🛡️", tone: "neg" };

      // Stop loss
      if (r === "stop_loss") return { text: "Stop loss", emoji: "🛑", tone: "neg" };
      if (r === "blind_sl") return { text: "Blind SL", emoji: "🔇", tone: "neg" };
      if (r === "predictive_dead") return { text: "Predictive dead", emoji: "💀", tone: "neg" };

      // NHL exits
      if (r === "nhl_near_resolve") return { text: "Near resolve (NHL)", emoji: "✅", tone: "pos" };
      if (r === "nhl_scale_out") return { text: "Take Profit (NHL)", emoji: "🎯", tone: "pos" };
      if (r === "nhl_shootout_profit") return { text: "Shootout kâr", emoji: "🥅", tone: "pos" };
      if (r === "nhl_predictive_dead") return { text: "Predictive dead (NHL)", emoji: "💀", tone: "neg" };
      if (r === "nhl_structural_damage") return { text: "Structural damage (NHL)", emoji: "📉", tone: "neg" };

      // NHL Puck Line
      if (r === "nhl_puck_line_near_resolve") return { text: "Near resolve (Puck Line)", emoji: "✅", tone: "pos" };
      if (r === "nhl_puck_line_scale_out") return { text: "Take Profit (Puck Line)", emoji: "🎯", tone: "pos" };
      if (r === "nhl_puck_line_predictive_dead") return { text: "Predictive dead (Puck Line)", emoji: "💀", tone: "neg" };
      if (r === "nhl_puck_line_structural_damage") return { text: "Structural damage (Puck Line)", emoji: "📉", tone: "neg" };
      if (r === "nhl_puck_line_hold") return { text: "Hold (Puck Line)", emoji: "⏸️", tone: "neutral" };

      // NHL Totals
      if (r === "nhl_totals_near_resolve") return { text: "Near resolve (Totals)", emoji: "✅", tone: "pos" };
      if (r === "nhl_totals_scale_out") return { text: "Take Profit (Totals)", emoji: "🎯", tone: "pos" };
      if (r === "nhl_totals_predictive_dead") return { text: "Predictive dead (Totals)", emoji: "💀", tone: "neg" };
      if (r === "nhl_totals_structural_damage") return { text: "Structural damage (Totals)", emoji: "📉", tone: "neg" };
      if (r === "nhl_totals_hold") return { text: "Hold (Totals)", emoji: "⏸️", tone: "neutral" };

      // Tennis exits
      if (r === "tennis_near_resolve") return { text: "Near resolve (Tennis)", emoji: "✅", tone: "pos" };
      if (r === "tennis_profit_lock") return { text: "Profit lock (Tennis)", emoji: "🔒", tone: "pos" };
      if (r === "tennis_set_loss_decisive") return { text: "Set kaybı — kritik", emoji: "🎾", tone: "neg" };
      if (r === "tennis_set_loss_bagel") return { text: "Set kaybı — bagel", emoji: "🥯", tone: "neg" };
      if (r === "tennis_mathematical_death") return { text: "Matematiksel ölü", emoji: "☠️", tone: "neg" };
      if (r === "tennis_structural_damage") return { text: "Structural damage (Tennis)", emoji: "📉", tone: "neg" };

      // MLB Moneyline
      if (r === "mlb_near_resolve") return { text: "Near resolve (MLB)", emoji: "✅", tone: "pos" };
      if (r === "mlb_scale_out") return { text: "Take Profit (MLB)", emoji: "🎯", tone: "pos" };
      if (r === "mlb_m1_seventh_deficit_5") return { text: "M1: 7. inning, fark 5+", emoji: "⚾", tone: "neg" };
      if (r === "mlb_m2_eighth_deficit_3") return { text: "M2: 8. inning, fark 3+", emoji: "⚾", tone: "neg" };
      if (r === "mlb_m3_ninth_deficit_1") return { text: "M3: 9. inning, fark 1+", emoji: "⚾", tone: "neg" };
      if (r === "mlb_predictive_dead") return { text: "Predictive dead (MLB)", emoji: "💀", tone: "neg" };
      if (r === "mlb_structural_damage") return { text: "Structural damage (MLB)", emoji: "📉", tone: "neg" };

      // MLB Run Line
      if (r === "mlb_run_line_near_resolve") return { text: "Near resolve (Run Line)", emoji: "✅", tone: "pos" };
      if (r === "mlb_run_line_scale_out") return { text: "Take Profit (Run Line)", emoji: "🎯", tone: "pos" };
      if (r === "mlb_run_line_predictive_dead") return { text: "Predictive dead (Run Line)", emoji: "💀", tone: "neg" };
      if (r === "mlb_run_line_structural_damage") return { text: "Structural damage (Run Line)", emoji: "📉", tone: "neg" };

      // MLB Totals
      if (r === "mlb_totals_near_resolve") return { text: "Near resolve (MLB Totals)", emoji: "✅", tone: "pos" };
      if (r === "mlb_totals_scale_out") return { text: "Take Profit (MLB Totals)", emoji: "🎯", tone: "pos" };
      if (r === "mlb_totals_predictive_dead") return { text: "Predictive dead (MLB Totals)", emoji: "💀", tone: "neg" };
      if (r === "mlb_totals_structural_damage") return { text: "Structural damage (MLB Totals)", emoji: "📉", tone: "neg" };

      // Fallback — raw string, neutral
      return { text: r, emoji: "", tone: "neutral" };
    },
    // Label tone'u PnL ile overlay: reason doğası "pos" olsa bile (örn. Near
    // Resolve) gerçek PnL negatifse görsel kırmızı olsun. "neg"/"neutral"
    // kendilerinde kalır çünkü zaten doğru renk taşıyorlar.
    effectiveTone(label, pnl) {
      if (label && label.tone === "pos" && Number(pnl) < 0) return "neg";
      return label ? label.tone : "neutral";
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
