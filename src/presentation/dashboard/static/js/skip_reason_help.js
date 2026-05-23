"use strict";

/**
 * Skip reason listesi (sport-specific). Her sport için:
 *   { reason_code: "Türkçe açıklama" }
 *
 * Producer: src/strategy/entry/gate.py + sport-specific filters.
 * Yeni reason eklenince burayı da güncelle.
 */
window.SKIP_REASON_HELP = (function () {

  // GENERAL reasons — TÜM sport'larda geçerli
  const GENERAL = {
    "CIRCUIT_BREAKER_ACTIVE":  "Bugün çok kaybettik, bot mola verdi. Yarın tekrar açılır.",
    "COOLDOWN_ACTIVE":         "Üst üste kayıpları durdurmak için 1 saat ara.",
    "INACTIVE_SPORT":          "Bu spor şu an kapalı.",
    "MATCH_FINISHED":          "Maç bitmiş zaten.",
    "MATCH_TOO_FAR_ELAPSED":   "Maç çok ilerlemiş, geç kalındı.",
    "BLACKLISTED":             "Bu maç bilinçli olarak engellendi.",
    "MANIPULATION_HIGH":       "Bu maçın fiyatı şüpheli — biri fiyatla oynuyor olabilir.",
    "BELOW_MIN_BET":           "Açacağımız bahis çok küçük, mantıksız.",
    "CONFIDENCE_C":            "Yeterli bahis bürosu bu maç için açıkta değil — güvenilir veri yok.",
    "CONFIDENCE_NOT_A":        "Sharp bookmaker konfirmasyonu yok — sadece en güvenilir A grade pozisyonlara giriyoruz.",
    "BOOKMAKER_PROB_TOO_LOW":  "Bahis büroları bizim seçtiğimiz tarafa %55'ten az şans veriyor — favori değil.",
    "GAP_TOO_LOW":             "Bizim hesabımızla Polymarket fiyatı çok yakın — kâr fırsatı yok.",
    "VOLUME_TOO_LOW":          "Bu maçta yeterli bahis hacmi yok — pozisyon açarsak fiyat sallanır.",
    "SPREAD_UNPARSEABLE":      "Bahis çizgisini okuyamadık, atladık.",
    "TOTAL_UNPARSEABLE":       "Toplam-skor bahsinin sayısını okuyamadık.",
    "EVENT_NO_MATCH":          "Bahis bürolarında bu maç bulunmadı — eşleştiremedik.",
    "HANDLER_REJECT":          "Bu spora özel kurallar engelledi.",
    "event_already_held":      "Bu maçta zaten 3 pozisyon var (max=3).",
    "EVENT_ALREADY_HELD":      "Bu maçta zaten 3 pozisyon var (max=3).",
    "same_market_type_per_event": "Bu maçta aynı tür markette (ML/totals/spread) zaten açık pozisyon var.",
    "SAME_MARKET_TYPE_PER_EVENT": "Bu maçta aynı tür markette (ML/totals/spread) zaten açık pozisyon var.",
  };

  // NHL — bookmaker_prob path + NHL-specific filters
  const NHL = Object.assign({}, GENERAL, {
    // GENERAL override'ları — NHL eşikleri farklı
    "GAP_TOO_LOW":             "Bizim hesabımızla Polymarket fiyatı çok yakın — kâr fırsatı yok.",
    "VOLUME_TOO_LOW":          "Bu hokey maçında yeterli işlem hacmi yok.",
    "BOOKMAKER_PROB_TOO_LOW":  "Bahis büroları bu hokey pozisyonuna %55'ten az şans veriyor — favori değil.",
    // NHL-specific reason kodları
    "GOALIE_UNCONFIRMED":               "Kaleci henüz belli değil — bekliyoruz.",
    "NHL_PUCK_LINE_VOLUME_LOW":         "Bu hokey spread bahsinde yeterli işlem hacmi yok.",
    "NHL_TOTALS_VOLUME_LOW":            "Bu hokey toplam-gol bahsinde yeterli işlem hacmi yok.",
    "NHL_PUCK_LINE_PRICE_OUT_OF_RANGE": "Hokey spread fiyatı çok uçuk (ya çok düşük ya çok yüksek).",
    "NHL_TOTALS_PRICE_OUT_OF_RANGE":    "Hokey toplam-gol fiyatı çok uçuk.",
  });

  // NBA — bookmaker_prob + ESPN injury + B2B modifier
  const NBA = Object.assign({}, GENERAL, {
    // GENERAL override'ları — NBA eşikleri farklı
    "GAP_TOO_LOW":             "Bizim hesabımızla Polymarket fiyatı çok yakın — kâr fırsatı yok.",
    "VOLUME_TOO_LOW":          "Bu basketbol maçında yeterli işlem hacmi yok.",
    "BOOKMAKER_PROB_TOO_LOW":  "Bahis büroları bu basketbol pozisyonuna %60'tan az şans veriyor — favori değil.",
    // NBA-specific reason kodları (edge modifier — girişi engellemiyor, sadece azaltıyor)
    "INJURY_OWN_TEAM": "Bizim takımda yeni sakatlık var — bot daha temkinli.",
    "B2B_OPPONENT":    "Rakip art arda 2 maç oynuyor (yorgun) — bizim için avantaj.",
  });

  // MLB — internal Pythagorean + log5 + pitcher model
  const MLB = Object.assign({}, GENERAL, {
    "MLB_QUESTION_PARSE_FAIL":                   "Polymarket'in maç sorusunu anlayamadık.",
    "MLB_ENRICHER_UNAVAILABLE":                  "Beyzbol istatistik veya hava durumu servisi şu an çalışmıyor.",
    "MLB_ENRICHMENT_NONE":                       "Beyzbol verisi gelmedi — maç ertelenmiş veya iptal olmuş olabilir.",
    "MLB_ENRICHMENT_ERROR":                      "Veri çekerken hata oldu.",
    "MLB_GATE_REJECT:PITCHER_UNCONFIRMED":       "Atıcı henüz belli değil.",
    "MLB_GATE_REJECT:RAIN_SKIP":                 "Yağmur ihtimali yüksek — maç iptal olabilir.",
    "MLB_GATE_REJECT:RUNLINE_MINUS_15_FORBIDDEN":"Bu tür bahsi (-1.5 favori) açmıyoruz, kâr çıkmıyor.",
    "MLB_GATE_REJECT:OUTSIDE_PRE_GAME_WINDOW":   "Maç ya çok erken ya çok geç — uygun saat değil.",
    "MLB_GATE_REJECT:LOW_VOLUME":                "İşlem hacmi yetersiz.",
    "MLB_GATE_REJECT:LOW_LIQUIDITY":             "Likidite yetersiz.",
    "MLB_GATE_REJECT:PRICE_OUT_OF_RANGE":        "Fiyat çok uçuk (0.20'nin altı veya 0.75'in üstü).",
    "MLB_GATE_REJECT:GAP_BELOW_THRESHOLD":       "Bizim hesabımızla Polymarket fiyatı çok yakın — kâr fırsatı yok.",
    "MLB_GATE_REJECT:FAIR_PRICE_NONE":           "Hesabı yapamadık — eksik veri var.",
    "MLB_GATE_REJECT:SIZE_ZERO":                 "Açılacak miktar çok küçük çıktı, mantıksız.",
    "MLB_CONFIDENCE_NOT_A":                      "Sharp bookmaker konfirmasyonu yok — sadece en güvenilir A grade pozisyonlara giriyoruz.",
  });

  // TENNIS — Phase 1 v1, observer/paper hybrid
  const TENNIS = Object.assign({}, GENERAL, {
    // GENERAL override'ları — Tennis eşikleri farklı
    "GAP_TOO_LOW":    "Bizim hesabımızla Polymarket fiyatı çok yakın — kâr fırsatı yok.",
    "VOLUME_TOO_LOW": "Bu tenis maçında yeterli işlem hacmi yok.",
    // Tennis-specific reason kodları
    "TENNIS_PHASE_DISABLED":       "Tenis bahsi config'te kapalı.",
    "TENNIS_RANKING_TOO_LOW":      "Oyuncu top 100'de değil — düşük güvenli pas.",
    "TENNIS_RANKING_GAP_TOO_HIGH": "İki oyuncu arasında çok büyük seviye farkı — şike riski filtresi.",
    "TENNIS_BO5_NOT_SUPPORTED":    "Grand Slam 5-set maçı — şu an sadece 3-set destekleniyor.",
    "TENNIS_TIER_FILTER_DROPPED":  "Küçük turnuva (Challenger/ITF) — bot bunlara girmiyor.",
  });

  // EXIT REASONS — tüm sportlar için ortak kullanım
  const EXIT_REASONS = {
    // Genel
    "near_resolve":      "Maç bitiyor, kazandık — kâr al.",
    "scale_out":         "Yarısını sat, kâra geç.",
    "stop_loss":         "Fiyat çok düştü — zararı durduruyoruz.",
    "structural_damage": "Fiyat çok kötüye gitti — daha fazla bekleme.",
    "predictive_dead":   "Bu maç artık dönmüyor — çıkıyoruz.",
    "market_flip":       "Pozisyon ters döndü — kapat.",
    "score_exit":        "Skor aleyhe büyüdü — kayıp kabul.",
    "hold_revoked":      "Tutma kararı geri alındı.",
    "never_in_profit":   "Hiç kâra geçmedik, kayıp olarak kapat.",
    "ultra_low_guard":   "Fiyat çok düşük — koruma satışı.",
    "blind_sl":          "Skor gelmedi, körü körüne kapatıyoruz.",
    // NHL
    "nhl_near_resolve":                  "Hokey maçı bitiyor, kazandık — kâr al.",
    "nhl_scale_out":                     "Hokey bahsinin yarısını sat, kâra geç.",
    "nhl_shootout_profit":               "Penaltılarda 50/50 — riski azalt.",
    "nhl_predictive_dead":               "Bu hokey maçı artık dönmüyor — çıkıyoruz.",
    "nhl_structural_damage":             "Hokey fiyatı çok kötüye gitti — kapat.",
    "nhl_puck_line_near_resolve":        "Hokey spread maçı bitiyor — kâr al.",
    "nhl_puck_line_scale_out":           "Hokey spread bahsinin yarısını sat.",
    "nhl_puck_line_predictive_dead":     "Hokey spread artık dönmüyor — çıkıyoruz.",
    "nhl_puck_line_structural_damage":   "Hokey spread fiyatı çok kötüye gitti — kapat.",
    "nhl_totals_near_resolve":           "Hokey toplam-gol maçı bitiyor — kâr al.",
    "nhl_totals_scale_out":              "Hokey toplam-gol bahsinin yarısını sat.",
    "nhl_totals_predictive_dead":        "Hokey toplam-gol artık dönmüyor — çıkıyoruz.",
    "nhl_totals_structural_damage":      "Hokey toplam-gol fiyatı çok kötüye gitti — kapat.",
    // MLB
    "mlb_near_resolve":                  "Beyzbol maçı bitiyor, kazandık — kâr al.",
    "mlb_scale_out":                     "Beyzbol bahsinin yarısını sat, kâra geç.",
    "mlb_m1_seventh_deficit_5":          "Beyzbol 7. inning, 5+ run geride — geri dönüş çok zor.",
    "mlb_m2_eighth_deficit_3":           "Beyzbol 8. inning, 3+ run geride — kapat.",
    "mlb_m3_ninth_deficit_1":            "Beyzbol 9. inning, geride — son şans bitti.",
    "mlb_predictive_dead":               "Bu beyzbol maçı artık dönmüyor — çıkıyoruz.",
    "mlb_structural_damage":             "Beyzbol fiyatı çok kötüye gitti — kapat.",
    "mlb_run_line_near_resolve":         "Beyzbol run line maçı bitiyor — kâr al.",
    "mlb_run_line_scale_out":            "Beyzbol run line bahsinin yarısını sat.",
    "mlb_run_line_predictive_dead":      "Beyzbol run line artık dönmüyor — çıkıyoruz.",
    "mlb_run_line_structural_damage":    "Beyzbol run line fiyatı çok kötüye gitti — kapat.",
    "mlb_totals_near_resolve":           "Beyzbol toplam-skor maçı bitiyor — kâr al.",
    "mlb_totals_scale_out":              "Beyzbol toplam-skor bahsinin yarısını sat.",
    "mlb_totals_predictive_dead":        "Beyzbol toplam-skor artık dönmüyor — çıkıyoruz.",
    "mlb_totals_structural_damage":      "Beyzbol toplam-skor fiyatı çok kötüye gitti — kapat.",
    // Tennis
    "tennis_near_resolve":               "Tenis maçı bitiyor, kazandık — kâr al.",
    "tennis_profit_lock":                "Tenis fiyatı çok yükseldi — kazancı kilitle.",
    "tennis_set_loss_decisive":          "Kritik set kaybı — pozisyon kötüye gidiyor.",
    "tennis_set_loss_bagel":             "Set 6-0 kaybedildi — ağır kayıp.",
    "tennis_mathematical_death":         "Tenis matematiksel olarak bitti — geri dönüş imkânsız.",
    "tennis_structural_damage":          "Tenis fiyatı çok kötüye gitti — kapat.",
  };

  /**
   * Sport tag'inden o spor için ilgili tüm skip reason'ları döndür.
   * Format: { reason_code: "Türkçe açıklama" }
   */
  function getSkipReasonsForSport(sportTag) {
    const sport = (sportTag || "").toLowerCase();
    if (sport.includes("mlb") || sport === "baseball") return MLB;
    if (sport.includes("nhl") || sport === "icehockey_nhl" || sport === "hockey") return NHL;
    if (sport.includes("nba") || sport === "basketball_nba" || sport === "basketball") return NBA;
    if (sport.includes("tennis") || sport.startsWith("atp") || sport.startsWith("wta")) return TENNIS;
    return GENERAL;
  }

  function getAllExitReasons() {
    return EXIT_REASONS;
  }

  return { getSkipReasonsForSport, getAllExitReasons };
})();

// ── Popup UI ──────────────────────────────────────────────────────────────────

window.showSkipHelp = function (sportTag, kind, currentReason) {
  const popup   = document.getElementById("skip-help-popup");
  const listEl  = document.getElementById("skip-help-list");
  const titleEl = popup.querySelector(".skip-help-title");

  let reasons;
  if (kind === "exit") {
    reasons = window.SKIP_REASON_HELP.getAllExitReasons();
    titleEl.textContent = "Çıkış Sebepleri";
  } else {
    reasons = window.SKIP_REASON_HELP.getSkipReasonsForSport(sportTag);
    const sportLabel = sportTag ? " (" + sportTag.toUpperCase() + ")" : "";
    titleEl.textContent = "Skip Sebepleri" + sportLabel;
  }

  listEl.innerHTML = "";

  // Mevcut reason: bazen ":DETAIL" suffix var (ör. "MLB_GATE_REJECT:GAP_BELOW_THRESHOLD edge=-0.153")
  // Önce full match dene, yoksa prefix match (colon-detail strip için).
  const cur = String(currentReason || "").trim();
  let matchedKey = null;
  if (cur) {
    if (Object.prototype.hasOwnProperty.call(reasons, cur)) {
      matchedKey = cur;
    } else {
      for (const k of Object.keys(reasons)) {
        if (cur.startsWith(k)) {
          matchedKey = k;
          break;
        }
      }
    }
  }

  // Render: önce CURRENT (varsa) + ayraç, sonra diğerleri
  if (matchedKey) {
    const currentItem = document.createElement("div");
    currentItem.className = "skip-help-item skip-help-current";
    currentItem.innerHTML =
      '<div class="code">' + matchedKey + '</div>' +
      '<div class="desc">' + reasons[matchedKey] + '</div>';
    listEl.appendChild(currentItem);

    const divider = document.createElement("div");
    divider.className = "skip-help-divider";
    divider.textContent = "Diğer olası sebepler";
    listEl.appendChild(divider);
  }

  for (const [code, desc] of Object.entries(reasons)) {
    if (code === matchedKey) continue; // current zaten yukarıda
    const item = document.createElement("div");
    item.className = "skip-help-item";
    item.innerHTML =
      '<div class="code">'  + code + '</div>' +
      '<div class="desc">'  + desc + '</div>';
    listEl.appendChild(item);
  }

  popup.classList.remove("hidden");
};

window.hideSkipHelp = function () {
  document.getElementById("skip-help-popup").classList.add("hidden");
};

document.addEventListener("DOMContentLoaded", function () {
  // Kapat butonu
  const closeBtn = document.querySelector(".skip-help-close");
  if (closeBtn) closeBtn.addEventListener("click", window.hideSkipHelp);

  // Overlay tıklaması
  const popup = document.getElementById("skip-help-popup");
  if (popup) {
    popup.addEventListener("click", function (e) {
      if (e.target === this) window.hideSkipHelp();
    });
  }

  // Escape tuşu
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") window.hideSkipHelp();
  });
});
