"""
sport_rules.py — Sport-specific trading rules.

Tek kaynak: Her sporun SL, TP, re-entry, exit kuralları burada.
main.py, portfolio.py, match_exit.py, reentry_farming.py buradan okur.

Kullanım:
    from src.sport_rules import get_sport_rule, get_stop_loss, get_max_reentries
"""

from __future__ import annotations
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# MASTER RULES TABLE
# ═══════════════════════════════════════════════════════

SPORT_RULES: dict[str, dict] = {
    # ── NBA ──
    "nba": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.75,
        "halftime_exit": True,
        "halftime_exit_deficit": 15,  # points behind at halftime
        "hold_to_resolve_margin": 5,  # within X points = hold
        "pre_match_mandatory_exit_min": 8,
        "match_duration_hours": 2.5,
        "score_volatility_per_event": 0.004,
        "comeback_probability": "high",
        "losing_badly_deficit": 20,  # points behind = losing badly
        "losing_badly_quarters": ["Q3", "Q4"],
    },
    # ── NFL ──
    "nfl": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 14,
        "hold_to_resolve_margin": 7,
        "pre_match_mandatory_exit_min": 15,
        "match_duration_hours": 3.25,
        "score_volatility_per_event": 0.006,
        "comeback_probability": "medium",
        "losing_badly_deficit": 17,
        "losing_badly_quarters": ["Q3", "Q4"],
    },
    # ── NHL ──
    "nhl": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": False,
        "period_exit": True,
        "period_exit_deficit": 3,  # goals behind after P2
        "hold_to_resolve_margin": 1,  # within 1 goal
        "pre_match_mandatory_exit_min": 10,
        "match_duration_hours": 2.5,
        "score_volatility_per_event": 0.10,
        "comeback_probability": "medium-low",
        "losing_badly_deficit": 3,
        "overtime_rule": "sudden_death",
    },
    # ── MLB ──
    "mlb": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.78,
        "halftime_exit": False,
        "inning_exit": True,
        "inning_exit_deficit": 5,  # runs behind after 6th
        "inning_exit_after": 6,
        "hold_to_resolve_margin": 2,  # within 2 runs after 6th
        "pre_match_mandatory_exit_min": 20,
        "match_duration_hours": 3.0,
        "score_volatility_per_event": 0.05,
        "comeback_probability": "medium",
        "losing_badly_deficit": 5,
    },
    # ── Soccer ──
    "soccer": {
        "stop_loss_pct": 0.25,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.75,
        "halftime_exit": True,
        "halftime_exit_deficit": 2,  # goals behind
        "hold_to_resolve_margin": 1,  # drawing or losing by 1 in H1
        "pre_match_mandatory_exit_min": 15,
        "match_duration_hours": 2.0,
        "score_volatility_per_event": 0.15,
        "comeback_probability": "low",
        "losing_badly_deficit": 2,
        "red_card_swing_pct": 0.08,
    },
    # ── Tennis ──
    "tennis": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.15,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": False,
        "set_exit": True,
        "set_exit_condition_bo3": "lost 1st set 6-1 or worse",
        "set_exit_condition_bo5": "lost 2 sets",
        "hold_to_resolve_margin": 1,  # within 1 set
        "pre_match_mandatory_exit_min": 0,  # not time-based
        "match_duration_hours_bo3": 1.75,
        "match_duration_hours_bo5": 3.5,
        "match_duration_hours": 2.5,  # default
        "score_volatility_per_set": 0.12,
        "score_volatility_per_break": 0.06,
        "comeback_probability": "high",
        "losing_badly_bo3": "lost 1st set + down break in 2nd",
        "losing_badly_bo5": "lost 2 sets + down break in 3rd",
        "retirement_risk": True,
    },
    # ── MMA/UFC ──
    "mma": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.25,
        "trailing_tp_trail": 0.12,
        "max_reentries": 1,
        "reentry_max_elapsed_pct": 0.60,
        "halftime_exit": False,
        "round_exit": True,
        "round_exit_condition_3r": "lost 2 rounds dominantly",
        "round_exit_condition_5r": "lost 3 rounds or near-finish",
        "hold_to_resolve_margin": 0,  # winning on cards
        "pre_match_mandatory_exit_min": 5,
        "match_duration_hours_3r": 0.5,
        "match_duration_hours_5r": 0.75,
        "match_duration_hours": 0.5,
        "score_volatility_per_event": 0.15,
        "comeback_probability": "medium-high",
        "finish_probability": 0.55,
    },
    # ── Boxing ──
    "boxing": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.65,
        "halftime_exit": False,
        "round_exit": True,
        "round_exit_condition": "lost 4+ rounds + knockdown",
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 10,
        "match_duration_hours": 1.0,
        "score_volatility_per_round": 0.03,
        "score_volatility_knockdown": 0.12,
        "comeback_probability": "low-medium",
    },
    # ── Cricket T20/IPL ──
    "cricket": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.10,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 0,  # below par score
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 15,
        "match_duration_hours": 3.5,
        "score_volatility_per_wicket": 0.06,
        "comeback_probability": "medium",
        "losing_badly_deficit": 0,  # RRR > 12 after 15 overs
    },
    # ── Rugby NRL ──
    "rugby": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 18,  # points behind
        "hold_to_resolve_margin": 7,
        "pre_match_mandatory_exit_min": 10,
        "match_duration_hours": 2.0,
        "score_volatility_per_try": 0.07,
        "comeback_probability": "medium-low",
        "losing_badly_deficit": 18,
    },
    # ── CS2 ──
    "cs2": {
        "stop_loss_pct": 0.40,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": True,
        "halftime_exit_deficit": 7,  # rounds behind (4-11)
        "hold_to_resolve_margin": 3,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 2.0,
        "score_volatility_per_round": 0.015,
        "score_volatility_per_map": 0.12,
        "comeback_probability": "medium-high",
        "economy_factor": True,
    },
    # ── Valorant ──
    "valorant": {
        "stop_loss_pct": 0.40,
        "trailing_tp_activation": 0.20,
        "trailing_tp_trail": 0.08,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.70,
        "halftime_exit": False,
        "map_exit": True,
        "map_exit_deficit": 6,  # rounds behind in map 2
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 2.0,
        "score_volatility_per_round": 0.015,
        "score_volatility_per_map": 0.12,
        "comeback_probability": "medium-high",
    },
    # ── League of Legends ──
    "lol": {
        "stop_loss_pct": 0.30,
        "trailing_tp_activation": 0.15,
        "trailing_tp_trail": 0.08,
        "max_reentries": 2,
        "reentry_max_elapsed_pct": 0.55,
        "halftime_exit": False,
        "objective_exit": True,
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 1.5,
        "score_volatility_per_tower": 0.02,
        "score_volatility_per_dragon": 0.03,
        "score_volatility_per_baron": 0.08,
        "score_volatility_per_map": 0.15,
        "comeback_probability": "low",
        "snowball_ban_elapsed_pct": 0.30,
    },
    # ── Dota 2 ──
    "dota2": {
        "stop_loss_pct": 0.35,
        "trailing_tp_activation": 0.15,
        "trailing_tp_trail": 0.10,
        "max_reentries": 3,
        "reentry_max_elapsed_pct": 0.60,
        "halftime_exit": False,
        "objective_exit": True,
        "hold_to_resolve_margin": 0,
        "pre_match_mandatory_exit_min": 0,
        "match_duration_hours": 2.5,
        "score_volatility_per_tower": 0.015,
        "score_volatility_per_roshan": 0.04,
        "score_volatility_per_map": 0.15,
        "comeback_probability": "medium",
        "snowball_ban_elapsed_pct": 0.30,
        "buyback_factor": True,
    },
}

# ═══════════════════════════════════════════════════════
# DEFAULT — bilinmeyen sporlar için
# ═══════════════════════════════════════════════════════

DEFAULT_RULES: dict = {
    "stop_loss_pct": 0.30,
    "trailing_tp_activation": 0.20,
    "trailing_tp_trail": 0.08,
    "max_reentries": 2,
    "reentry_max_elapsed_pct": 0.65,
    "halftime_exit": False,
    "hold_to_resolve_margin": 0,
    "pre_match_mandatory_exit_min": 15,
    "match_duration_hours": 2.0,
    "score_volatility_per_event": 0.05,
    "comeback_probability": "medium",
    "losing_badly_deficit": 0,
}

# ═══════════════════════════════════════════════════════
# PUBLIC API — diğer modüller bunları çağırır
# ═══════════════════════════════════════════════════════

def get_sport_rule(sport_tag: str, key: str, default=None):
    """Tek bir kural değerini getir."""
    tag = _normalize_tag(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    return rules.get(key, DEFAULT_RULES.get(key, default))


def get_sport_rules(sport_tag: str) -> dict:
    """Bir sporun tüm kurallarını getir (default ile merge)."""
    tag = _normalize_tag(sport_tag)
    merged = dict(DEFAULT_RULES)
    merged.update(SPORT_RULES.get(tag, {}))
    return merged


def get_stop_loss(sport_tag: str, is_esports: bool = False) -> float:
    """Sport-aware stop-loss oranı."""
    return get_sport_rule(sport_tag, "stop_loss_pct", 0.30)


def get_max_reentries(sport_tag: str, number_of_games: int = 0) -> int:
    """Sport-aware max re-entry limiti."""
    return get_sport_rule(sport_tag, "max_reentries", 2)


def get_reentry_max_elapsed(sport_tag: str) -> float:
    """Sport-aware max elapsed % for re-entry."""
    return get_sport_rule(sport_tag, "reentry_max_elapsed_pct", 0.65)


def get_trailing_tp_params(sport_tag: str) -> tuple[float, float]:
    """Sport-aware trailing TP parameters (activation, trail_distance)."""
    activation = get_sport_rule(sport_tag, "trailing_tp_activation", 0.20)
    trail = get_sport_rule(sport_tag, "trailing_tp_trail", 0.08)
    return activation, trail


def get_match_duration(sport_tag: str) -> float:
    """Sport-aware match duration in hours."""
    return get_sport_rule(sport_tag, "match_duration_hours", 2.0)


def is_losing_badly(sport_tag: str, deficit: float, elapsed_pct: float = 0.0) -> bool:
    """Sport-aware 'losing badly' check.

    Args:
        sport_tag: Sport identifier
        deficit: Score deficit (positive = behind). Points for NBA/NFL,
                 goals for soccer/NHL, runs for MLB, etc.
        elapsed_pct: Match elapsed percentage (0.0-1.0)
    """
    tag = _normalize_tag(sport_tag)
    rules = SPORT_RULES.get(tag, DEFAULT_RULES)
    threshold = rules.get("losing_badly_deficit", 0)

    if threshold <= 0:
        return False  # No losing badly rule for this sport

    return deficit >= threshold


def _normalize_tag(sport_tag: str) -> str:
    """Normalize sport tag to match SPORT_RULES keys."""
    if not sport_tag:
        return ""
    tag = sport_tag.lower().strip()
    # Common aliases
    aliases = {
        "basketball": "nba", "americanfootball": "nfl",
        "icehockey": "nhl", "baseball": "mlb",
        "football": "soccer", "mls": "soccer",
        "ufc": "mma", "csgo": "cs2", "counter-strike": "cs2",
        "val": "valorant", "league_of_legends": "lol",
        "dota": "dota2", "cricket_t20": "cricket", "ipl": "cricket",
        "nrl": "rugby",
    }
    return aliases.get(tag, tag)
