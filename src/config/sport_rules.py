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
        "score_source": "espn",
        "espn_sport": "basketball",
        "espn_league": "nba",
    },
    "nfl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.25,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
        "score_source": "espn",
        "espn_sport": "football",
        "espn_league": "nfl",
    },
    "nhl": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 2.5,
        "period_exit": True,
        "period_exit_deficit": 3,
        "late_deficit": 2,
        "late_elapsed_gate": 0.67,
        "score_price_confirm": 0.35,
        "final_elapsed_gate": 0.92,
        "score_source": "espn",
        "espn_sport": "hockey",
        "espn_league": "nhl",
    },
    "mlb": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 3.0,
        "inning_exit": True,
        "inning_exit_deficit": 5,
        "inning_exit_after": 6,
        # SPEC-010: M1/M2/M3 forced exit (tennis T1/T2, hockey K1-K4 simetrik)
        "score_exit_m1_inning": 7,     # M1 tetik inning (blowout)
        "score_exit_m1_deficit": 5,    # M1 run deficit threshold
        "score_exit_m2_inning": 8,     # M2 tetik inning (late big deficit)
        "score_exit_m2_deficit": 3,    # M2 run deficit threshold
        "score_exit_m3_inning": 9,     # M3 tetik inning (final inning)
        "score_exit_m3_deficit": 1,    # M3 run deficit threshold
        "score_source": "espn",
        "espn_sport": "baseball",
        "espn_league": "mlb",
    },
    "tennis": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 2.5,
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "set_exit": True,
        "score_source": "espn",
        "espn_sport": "tennis",
        "espn_league": "atp",
        "set_exit_deficit": 3,
        "set_exit_games_total": 7,
        "set_exit_blowout_deficit": 4,
        "set_exit_close_set_threshold": 5,
        "set_exit_close_set_buffer": 1,
        "set_exit_serve_for_match_games": 5,
    },
    "mma": {
        "stop_loss_pct": 0.35,
        "match_duration_hours": 0.5,
        "elapsed_exit_disabled": True,
        "score_source": "espn",
        "espn_sport": "mma",
        "espn_league": "ufc",
    },
    "golf": {
        "stop_loss_pct": 0.30,
        "match_duration_hours": 4.0,
        "playoff_aware": True,
        # score_source intentionally absent — ESPN golf scores not available
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
    # Combat sports
    "mma_ufc": "mma",
    "ufc": "mma",
    "boxing": "mma",
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
