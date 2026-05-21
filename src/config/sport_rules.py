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
    },
    "nfl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.25,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
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
            "totals": "model",
            "run_line": "model",
        },
    },
    # Tennis kaldırıldı 2026-05-05 — geri açmak için entry geri ekle
    "golf": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 4.0,
        "playoff_aware": True,
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
    # Tennis kaldırıldı 2026-05-05
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
