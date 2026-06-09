"""Sport-specific trading rules (DECISIONS §7.2). MVP 2-way sports only.

Draw-possible sporlar TODO-001 kapsamında, bu dosyada YOK.
"""
from __future__ import annotations

from typing import Any

# ── MVP sport rules (2-way) ──
SPORT_RULES: dict[str, dict] = {
    "nba": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "halftime_exit": True,
        "halftime_exit_deficit": 15,
        "score_source": "espn",
        "espn_sport": "basketball",
        "espn_league": "nba",
        # NBA totals KORUNUR (+$21 kanıt, T-Wolves 225.5). Spread için exit
        # mantığı yok (Faz 1 rollback Task 3 silindi) + veri yok (0 trade) →
        # scanner'da blokla. Faz 2'de kanıtla açma kararı verilir.
        "spread_blocked": True,
        # 2026-06-02 (kullanıcı kararı): NBA totals + spread → BİMODAL ($15 cap).
        # Eski varsayım (SL yakalar, küçük adım) YANLIŞTI: maç bittiğinde
        # Polymarket binary çözer ($1 veya $0). SL son anı yakalayamaz.
        # WNBA Min-Phx 167.5 OVER kanıtı: tek trade -$50 tam yanma. $50 → $15.
        "bimodal_market_types": ["totals", "spread", "spreads"],
    },
    "nfl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.25,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
        # SPEC-W: NFL empirical veri yok; mantık orta (35-55 puan, +3-7 adım).
        # Konservatif boş — empirical kanıt gelene kadar non-bimodal.
        "bimodal_market_types": [],
    },
    "nhl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 2.5,
        "period_exit": True,
        "period_exit_deficit": 3,
        "score_source": "espn",
        "espn_sport": "hockey",
        "espn_league": "nhl",
        # Eski projede 4 günde 13W/2L +$126 ML-only kanıtı (SPEC-L 2026-05-11).
        # NHL spread/totals trade'leri için kanıt yok → moneyline-only.
        "moneyline_only": True,
        # SPEC-W: NHL ML audit n=6 ort -%50 → BIMODAL kanıt. Totals/spread
        # mantıksal yüksek risk (5-7 gol, +1 gol büyük etki). Hepsi bimodal.
        "bimodal_market_types": ["moneyline", "totals", "spread", "spreads"],
    },
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
        "submarket_anchor": {
            "moneyline": "model",  # SPEC-S Faz C (2026-05-23)
            "totals": "model",
            "run_line": "model",
        },
        # SPEC-W: empirical — MLB totals %73, run_line %93, nrfi %69, ML %79
        # kademeli (n=13-15). 8-12 koşu + orta adım = SL yakalar. Bimodal yok.
        "bimodal_market_types": [],
    },
    "tennis": {
        # 2026-05-31: 0.30 → 0.50. Kullanıcı analizinde Sackmann moneyline %70
        # doğru AMA -$62 kayıp. Anchor < %30 (deep dog) → %81 doğru AMA -$29.
        # Sebep: tennis fiyat dalgalanması %30 SL aralığından büyük → erken
        # SL fire → bot satar → fiyat geri kâra döner → kaçırır. Gevşek SL
        # tahmini paraya çevirme şansı verir.
        "stop_loss_pct": 0.50,
        "match_duration_hours": 2.0,
        "start_source": "espn",
        "espn_sport": "tennis",
        "espn_leagues": ("atp", "wta"),
        # 2026-05-31 Adım 3: per-market Sackmann pricer'lar aktif. Anchor
        # bookmaker yerine model'den gelir — odds_enricher h2h fiyatını alt
        # marketlere kopyalama cascade bug'ı çözüldü. Eksik veride pricer
        # None döner → entry skip.
        # SPEC-Z28 (2026-06-09): tennis_match_totals TAMAMEN KALDIRILDI
        # (allowed_sports_market_types'tan çıkarıldı; model %38 isabet, -$45;
        # bahisçi totals tenis akışının ~%8'ini kapsıyor).
        "submarket_anchor": {
            "moneyline": "model",
            "tennis_set_handicap": "model",
            "tennis_first_set_winner": "model",
            "tennis_set_totals": "model",
        },
        # SPEC-W: empirical — set_totals/set_handicap WTA ambiguous (bimodal),
        # match_totals ATP %53 no_sig_drop. ATP set_totals %60 kademeli
        # (non-bimodal). Tenis lab kendi worktree'sinde ayrı yapı kullanır.
        # 2026-05-31: ÖNCEKİ isimler ("set_totals", "set_handicap",
        # "match_total_games") YANLIŞTI — Polymarket prefix'li dönüyor
        # ("tennis_set_totals" vs.). Mismatch yüzünden bimodal sizing $15 cap
        # ÇALIŞMIYORDU, bot $50 fixed kullanıyordu = 3.3x risk.
        "bimodal_market_types": [
            "tennis_set_totals",
            "tennis_set_handicap",
        ],
    },
    "golf": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 4.0,
        "playoff_aware": True,
        # SPEC-W: golf empirical yok, audit yok. Konservatif boş.
        "bimodal_market_types": [],
    },
}

DEFAULT_RULES: dict[str, Any] = {
    "stop_loss_pct": 0.30,
    "match_duration_hours": 2.0,
}

# Basketball alt-ligleri: tum exit kurallarini NBA'den miras alir, sadece ESPN
# league override + (varsa) score_source devre disi. Sebep: BASKETBALL_TAGS
# fallback espn_league'i de NBA'ye ceviriyordu, score_enricher yanlis scoreboard
# sorguluyordu (WNBA/NCAAB maclari basketball/nba endpoint'inde yok)
# -> match_ended/match_live hicbir zaman True olmuyordu.
SPORT_RULES["wnba"] = {**SPORT_RULES["nba"], "espn_league": "wnba"}
SPORT_RULES["ncaab"] = {**SPORT_RULES["nba"], "espn_league": "mens-college-basketball"}
SPORT_RULES["cbb"] = {**SPORT_RULES["nba"], "espn_league": "mens-college-basketball"}
SPORT_RULES["wncaab"] = {**SPORT_RULES["nba"], "espn_league": "womens-college-basketball"}
SPORT_RULES["nbl"] = {**SPORT_RULES["nba"], "espn_league": "nbl"}
# Euroleague ESPN'de yok (endpoint 400) -> score_source kapali; NBA exit
# kurallari (SL, halftime) yine gecerli, sadece ESPN skor enrichment atlanir.
SPORT_RULES["euroleague"] = {**SPORT_RULES["nba"], "score_source": None}

# Basketball sport tags (NBA + WNBA + college + international leagues).
# Tek doğruluk kaynağı — hem scanner filter (spreads/totals gate) hem de
# exit dispatch (NBA exit guard) buradan import eder.
BASKETBALL_TAGS: frozenset[str] = frozenset({
    "nba", "wnba", "ncaab", "cbb", "wncaab", "euroleague", "nbl",
})

# Odds API key → internal sport key aliases (DECISIONS §7.1 MVP)
_ALIASES: dict[str, str] = {
    # Basketball — her alt-lig kendi SPORT_RULES entry'sine yonlenir (ESPN
    # league override icin). Plain "basketball" NBA'ye duser (geriye uyumlu).
    "basketball_nba": "nba",
    "basketball_wnba": "wnba",
    "basketball_ncaab": "ncaab",
    "basketball_wncaab": "wncaab",
    "basketball_euroleague": "euroleague",
    "basketball_nbl": "nbl",
    "basketball": "nba",
    # American Football
    "americanfootball_ncaaf": "nfl",
    "americanfootball_cfl": "nfl",
    "americanfootball_ufl": "nfl",
    "americanfootball": "nfl",
    # Ice Hockey
    "icehockey_nhl": "nhl",
    "icehockey_ahl": "nhl",
    "icehockey_liiga": "nhl",
    "icehockey_mestis": "nhl",
    "icehockey_sweden_hockey_league": "nhl",
    "icehockey_sweden_allsvenskan": "nhl",
    "icehockey": "nhl",
    # Baseball
    "baseball_mlb": "mlb",
    "baseball_milb": "mlb",
    "baseball_npb": "mlb",
    "baseball_kbo": "mlb",
    "baseball_ncaa": "mlb",
    "baseball": "mlb",
    # Tennis (geri açıldı 2026-05-22 — ESPN match_start için)
    "tennis_atp": "tennis",
    "tennis_wta": "tennis",
    "tennis_itf_men": "tennis",
    "tennis_itf_women": "tennis",
    "tennis": "tennis",
    # Golf
    "golf_lpga_tour": "golf",
    "golf_liv_tour": "golf",
}


def _normalize(sport_tag: str) -> str:
    tag = (sport_tag or "").lower().strip()
    if tag in SPORT_RULES:
        return tag
    if tag in _ALIASES:
        return _ALIASES[tag]
    return ""


def get_sport_rule(sport_tag: str, key: str, default: Any = None) -> Any:
    tag = _normalize(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    return rules.get(key, DEFAULT_RULES.get(key, default))


def get_stop_loss(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "stop_loss_pct", 0.30))


def get_match_duration_hours(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "match_duration_hours", 2.0))


def is_moneyline_only(sport_tag: str) -> bool:
    """Sport için yalnızca moneyline market'leri kabul edilir mi? (DECISIONS §7.2 NHL ML-only)."""
    return bool(get_sport_rule(sport_tag, "moneyline_only", False))


def is_spread_blocked(sport_tag: str) -> bool:
    """Sport için spread market'leri reddedilir mi? NBA: spread exit silindi (Task 3) + 0 trade kanıtı."""
    return bool(get_sport_rule(sport_tag, "spread_blocked", False))


def anchor_source(sport_tag: str, market_type: str) -> str:
    """Sport+market_type için anchor kaynağı: 'bookmaker' veya 'model'.

    Default 'bookmaker' — geriye uyumlu. 'model' override eden sport'lar
    SPORT_RULES içinde `submarket_anchor` dict'iyle ilan eder (SPEC-R).
    """
    overrides = get_sport_rule(sport_tag, "submarket_anchor", {})
    if not isinstance(overrides, dict):
        return "bookmaker"
    return str(overrides.get(market_type, "bookmaker"))


# 2026-06-02 (kullanıcı kararı): bimodal MARKET YAPISI gereği, sport bağımsız.
# Polymarket'te tüm totals/spreads/handicaps binary resolve eder ($1 veya $0),
# SL son anı yakalayamaz. Sport-bazlı liste kötü tasarımdı (MLB totals fixed $50
# alıyordu, WNBA Min-Phx $50 yandı).
_UNIVERSAL_BIMODAL_MARKET_TYPES = frozenset({
    "totals", "total", "spread", "spreads", "handicap",
    "tennis_set_handicap", "tennis_set_totals",
    "tennis_first_set_winner",
})


def is_bimodal_market(sport_tag: str, market_type: str) -> bool:
    """Bimodal market mi? Sport bağımsız — market yapısı belirler.

    Tüm totals/spreads/handicaps Polymarket'te binary resolve eder. SL kayıt
    altında değil — bu yüzden BÜYÜK risk, küçük cap ($15) ile sınırla.

    Returns:
        True → bimodal_bet_usdc ($15 cap) uygulanır.
        False → fixed_bet_usdc ($50) uygulanır (sadece moneyline).
    """
    if not market_type:
        return False
    return market_type.lower() in _UNIVERSAL_BIMODAL_MARKET_TYPES
