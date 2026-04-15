/* ICONS — sport_tag/slug → emoji veya <img> HTML (dashboard feed cards).
 *
 * Tüm fonksiyonlar pure. Çıktı HTML string — innerHTML'e yazılır.
 */
(function (global) {
  "use strict";

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

  global.ICONS = ICONS;
})(window);
