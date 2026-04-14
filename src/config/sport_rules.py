"""Sport-specific trading rules (TDD §7.2). MVP 2-way sports only.

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
    },
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
    },
    "tennis": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "set_exit": True,
    },
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

# Odds API key → internal sport key aliases (TDD §7.1 MVP)
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
    # Tennis
    "tennis_atp": "tennis",
    "tennis_wta": "tennis",
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
    # tennis_* prefix match (dinamik turnuvalar)
    if tag.startswith("tennis_"):
        return "tennis"
    return ""


def get_sport_rule(sport_tag: str, key: str, default: Any = None) -> Any:
    tag = _normalize(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    return rules.get(key, DEFAULT_RULES.get(key, default))


def get_stop_loss(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "stop_loss_pct", 0.30))


def get_match_duration_hours(sport_tag: str) -> float:
    return float(get_sport_rule(sport_tag, "match_duration_hours", 2.0))
