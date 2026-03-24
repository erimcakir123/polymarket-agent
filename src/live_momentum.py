"""Live Momentum Trader — score-based probability re-estimation.

When a match is live and score changes, Polymarket prices lag 10-60 seconds.
This module re-estimates probability based on live score and detects
when market price hasn't caught up yet — creating a momentum edge.

Flow:
    1. PandaScore provides live match state (score, elapsed)
    2. Calculate score-adjusted probability from pre-match AI estimate
    3. Compare adjusted probability vs current market price
    4. If edge exists and market is lagging → signal MOMENTUM_ENTRY or MOMENTUM_EXIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Score impact tables — how much each scoring event shifts probability
# Values are ADDITIVE adjustments to pre-match probability

_SCORE_IMPACT: Dict[str, dict] = {
    # Basketball: point differential × weight, scaled by quarter
    "nba": {
        "per_point": 0.004,        # Each point difference = 0.4% shift
        "quarter_weights": {1: 0.5, 2: 0.7, 3: 1.0, 4: 1.5},  # Q4 matters most
        "blowout_threshold": 15,   # 15+ points = strong signal
        "blowout_multiplier": 1.3,
    },
    "basketball": {"per_point": 0.004, "quarter_weights": {1: 0.5, 2: 0.7, 3: 1.0, 4: 1.5},
                    "blowout_threshold": 15, "blowout_multiplier": 1.3},

    # Soccer: goals are rare and impactful
    "soccer": {"per_goal": 0.15, "minute_factor": True, "red_card_shift": 0.08},
    "epl": {"per_goal": 0.15, "minute_factor": True, "red_card_shift": 0.08},
    "ucl": {"per_goal": 0.15, "minute_factor": True, "red_card_shift": 0.08},
    "laliga": {"per_goal": 0.15, "minute_factor": True, "red_card_shift": 0.08},

    # Tennis: set-based
    "tennis": {"per_set": 0.12, "per_break": 0.06, "bo5_per_set": 0.08},
    "atp": {"per_set": 0.12, "per_break": 0.06, "bo5_per_set": 0.08},
    "wta": {"per_set": 0.12, "per_break": 0.06, "bo5_per_set": 0.08},

    # Esports: round/map based
    "cs2": {"per_round": 0.015, "per_map": 0.12, "economy_factor": True},
    "val": {"per_round": 0.015, "per_map": 0.12},
    "valorant": {"per_round": 0.015, "per_map": 0.12},
    "lol": {"per_map": 0.15, "per_tower": 0.02, "per_dragon": 0.03},
    "dota2": {"per_map": 0.15, "per_tower": 0.015, "per_roshan": 0.04},

    # American sports
    "nfl": {"per_point": 0.006, "quarter_weights": {1: 0.4, 2: 0.6, 3: 0.9, 4: 1.5}},
    "mlb": {"per_run": 0.05, "inning_weights": {i: 0.5 + i * 0.06 for i in range(1, 10)}},
    "nhl": {"per_goal": 0.10, "period_weights": {1: 0.6, 2: 0.8, 3: 1.2}},
}

# Minimum edge to consider a momentum trade
MIN_MOMENTUM_EDGE = 0.06

# Maximum hold time for momentum positions (minutes)
MAX_HOLD_MINUTES = 30

# Position sizing as percentage of bankroll
MOMENTUM_BET_PCT = 0.04  # 4% bankroll per momentum trade


@dataclass
class MomentumSignal:
    """A momentum trading signal from live score analysis."""
    condition_id: str
    direction: str                # "BUY_YES" | "BUY_NO"
    adjusted_prob: float          # Score-adjusted probability
    market_price: float           # Current market YES price
    edge: float                   # adjusted_prob - market_price
    score_diff: int               # Raw score difference (positive = team_a leading)
    elapsed_pct: float            # Match progress (0.0-1.0)
    sport: str
    reason: str


def calculate_score_adjusted_probability(
    pre_match_prob: float,
    match_state: dict,
    sport_tag: str,
    direction: str = "BUY_YES",
) -> Optional[float]:
    """Adjust pre-match AI probability based on live score.

    Args:
        pre_match_prob: Original AI probability estimate
        match_state: Live match state from PandaScore
        sport_tag: Sport identifier (nba, cs2, soccer, etc.)
        direction: Trade direction (affects sign of adjustment)

    Returns:
        Adjusted probability, or None if can't calculate
    """
    config = _SCORE_IMPACT.get(sport_tag)
    if not config:
        return None

    try:
        team_a_score = int(match_state.get("team_a_score", 0))
        team_b_score = int(match_state.get("team_b_score", 0))
    except (ValueError, TypeError):
        return None
    score_diff = team_a_score - team_b_score
    elapsed_pct = match_state.get("elapsed_pct", 0.5)

    # Direction-aware: BUY_NO profits when team_a loses
    if direction == "BUY_NO":
        score_diff = -score_diff

    adjustment = 0.0

    # Sport-specific adjustment calculation
    if "per_point" in config:
        # Basketball, NFL — point differential
        per_point = config["per_point"]
        quarter = _estimate_quarter(elapsed_pct, sport_tag)
        weight = config.get("quarter_weights", {}).get(quarter, 1.0)
        adjustment = score_diff * per_point * weight

        # Blowout bonus
        if abs(score_diff) >= config.get("blowout_threshold", 999):
            adjustment *= config.get("blowout_multiplier", 1.0)

    elif "per_goal" in config:
        # Soccer — goals rare but impactful
        per_goal = config["per_goal"]
        adjustment = score_diff * per_goal
        # Late goals matter more
        if config.get("minute_factor") and elapsed_pct > 0.75:
            adjustment *= 1.3

    elif "per_set" in config:
        # Tennis — set differential
        per_set = config["per_set"]
        adjustment = score_diff * per_set

    elif "per_map" in config:
        # Esports — map differential
        per_map = config["per_map"]
        map_score_a = match_state.get("map_score", {}).get("team_a", 0)
        map_score_b = match_state.get("map_score", {}).get("team_b", 0)
        map_diff = map_score_a - map_score_b
        if direction == "BUY_NO":
            map_diff = -map_diff
        adjustment = map_diff * per_map

        # Round-level adjustment if available
        per_round = config.get("per_round", 0)
        if per_round and score_diff != 0:
            adjustment += score_diff * per_round

    elif "per_run" in config:
        # Baseball
        per_run = config["per_run"]
        inning = _estimate_quarter(elapsed_pct, sport_tag)
        weight = config.get("inning_weights", {}).get(inning, 1.0)
        adjustment = score_diff * per_run * weight

    # Apply adjustment
    adjusted = pre_match_prob + adjustment

    # Clamp to valid range
    adjusted = max(0.05, min(0.95, adjusted))

    return round(adjusted, 4)


def detect_momentum_opportunity(
    condition_id: str,
    pre_match_prob: float,
    market_price: float,
    match_state: dict,
    sport_tag: str,
    direction: str = "BUY_YES",
    min_edge: float = MIN_MOMENTUM_EDGE,
) -> Optional[MomentumSignal]:
    """Detect if there's a momentum trading opportunity.

    Returns MomentumSignal if market price hasn't caught up to score, else None.
    """
    adjusted = calculate_score_adjusted_probability(
        pre_match_prob, match_state, sport_tag, direction,
    )
    if adjusted is None:
        return None

    # Calculate edge
    if direction == "BUY_YES":
        edge = adjusted - market_price
    else:
        edge = market_price - adjusted

    if edge < min_edge:
        return None

    score_diff = match_state.get("team_a_score", 0) - match_state.get("team_b_score", 0)
    elapsed_pct = match_state.get("elapsed_pct", 0.5)

    return MomentumSignal(
        condition_id=condition_id,
        direction=direction,
        adjusted_prob=adjusted,
        market_price=market_price,
        edge=round(edge, 4),
        score_diff=score_diff,
        elapsed_pct=elapsed_pct,
        sport=sport_tag,
        reason=(
            f"Score {match_state.get('team_a_score', '?')}-{match_state.get('team_b_score', '?')} "
            f"→ adjusted prob {adjusted:.1%} vs market {market_price:.1%} "
            f"(edge {edge:.1%}, {elapsed_pct:.0%} elapsed)"
        ),
    )


def _estimate_quarter(elapsed_pct: float, sport: str) -> int:
    """Estimate current quarter/period/inning from elapsed percentage."""
    if sport in ("nba", "basketball"):
        return min(4, max(1, int(elapsed_pct * 4) + 1))
    elif sport in ("nfl", "football"):
        return min(4, max(1, int(elapsed_pct * 4) + 1))
    elif sport in ("nhl", "hockey"):
        return min(3, max(1, int(elapsed_pct * 3) + 1))
    elif sport in ("mlb", "baseball"):
        return min(9, max(1, int(elapsed_pct * 9) + 1))
    else:
        return 1
