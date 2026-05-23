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
        # SPEC-W (2026-05-23): empirical analiz — NBA totals %67, spread %100
        # kademeli (n=8-9). Yüksek puan + küçük adım = SL yakalar. Bimodal yok.
        "bimodal_market_types": [],
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
        "stop_loss_pct": 0.30,
        "match_duration_hours": 2.0,
        "start_source": "espn",
        "espn_sport": "tennis",
        "espn_leagues": ("atp", "wta"),
        # SPEC-W: empirical — set_totals/set_handicap WTA ambiguous (bimodal),
        # match_total_games ATP %53 no_sig_drop. ATP set_totals %60 kademeli
        # (non-bimodal). Tenis lab kendi worktree'sinde ayrı yapı kullanır.
        "bimodal_market_types": [
            "set_totals", "set_handicap", "match_total_games",
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

# Basketball sport tags (NBA + WNBA + college + international leagues).
# Tek doğruluk kaynağı — hem scanner filter (spreads/totals gate) hem de
# exit dispatch (NBA exit guard) buradan import eder.
BASKETBALL_TAGS: frozenset[str] = frozenset({
    "nba", "wnba", "ncaab", "cbb", "wncaab", "euroleague", "nbl",
})

# Odds API key → internal sport key aliases (DECISIONS §7.1 MVP)
_ALIASES: dict[str, str] = {
    # Basketball
    "basketball_nba": "nba",
    "basketball_wnba": "nba",
    "basketball_ncaab": "nba",
    "basketball_wncaab": "nba",
    "basketball_euroleague": "nba",
    "basketball_nbl": "nba",
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
    # Polymarket basketball alt etiketleri (wnba/ncaab/cbb/wncaab/euroleague/nbl)
    # NBA kuralının altında çalışır — spread_blocked vs flag'leri için tek-yer.
    if tag in BASKETBALL_TAGS:
        return "nba"
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


def is_bimodal_market(sport_tag: str, market_type: str) -> bool:
    """SPEC-W (2026-05-23): SL'in yakalayamadığı, anlık çakılan market mi?

    Empirical analiz (analysis/bimodal_classification_2026-05-23.md) ile
    sport-bazlı liste belirlendi. Default: non-bimodal ($50 sizing).

    Args:
        sport_tag: Internal sport key (örn "nhl", "mlb"). Boş/bilinmeyen
            → False (konservatif sport-yok varsayımı, default sizing).
        market_type: Polymarket sports_market_type (örn "moneyline", "totals",
            "spread"). Boş → False.

    Returns:
        True → bimodal_bet_usdc ($15 cap) uygulanır.
        False → fixed_bet_usdc ($50) uygulanır.
    """
    if not market_type:
        return False
    overrides = get_sport_rule(sport_tag, "bimodal_market_types", None)
    if not isinstance(overrides, (list, tuple, set, frozenset)):
        return False
    mt = market_type.lower()
    return mt in {str(m).lower() for m in overrides}
