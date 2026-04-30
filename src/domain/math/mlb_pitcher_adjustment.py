"""Adjust team winpct by today's starting pitcher's ERA.

Approach:
- Compute pitcher_factor = league_avg_era / pitcher_era (clamped 0.6-1.6)
- Shift base winpct by (pitcher_factor - 1.0) * weight
- Final winpct clamped to [0.05, 0.95]

Then matchup_winpct combines two pitcher-adjusted winpcts via log5.

Constants are config-driven defaults; production code passes config values.
"""
from __future__ import annotations

from src.domain.math.mlb_log5 import log5

LEAGUE_AVG_ERA: float = 4.20  # 2020-2024 MLB season average
PITCHER_WEIGHT: float = 0.35  # ~35% of game outcome attributed to starter
_ERA_FLOOR: float = 1.5
_FACTOR_MIN: float = 0.6
_FACTOR_MAX: float = 1.6
_WINPCT_MIN: float = 0.05
_WINPCT_MAX: float = 0.95


def pitcher_adjusted_winpct(
    base_winpct: float,
    pitcher_era: float,
    league_avg_era: float = LEAGUE_AVG_ERA,
    weight: float = PITCHER_WEIGHT,
) -> float:
    """Shift base winpct by today's pitcher's ERA delta from league avg."""
    safe_era = max(pitcher_era, _ERA_FLOOR)
    pitcher_factor = league_avg_era / safe_era
    pitcher_factor = max(_FACTOR_MIN, min(_FACTOR_MAX, pitcher_factor))
    delta = (pitcher_factor - 1.0) * weight
    adjusted = base_winpct + delta
    return max(_WINPCT_MIN, min(_WINPCT_MAX, adjusted))


def matchup_winpct(
    home_winpct: float,
    away_winpct: float,
    home_pitcher_era: float,
    away_pitcher_era: float,
    league_avg_era: float = LEAGUE_AVG_ERA,
    weight: float = PITCHER_WEIGHT,
) -> float:
    """Compute home team win probability for today's matchup.

    Pipeline:
    1. Adjust each team's winpct by today's pitcher
    2. Apply log5 to get head-to-head probability
    """
    home_adj = pitcher_adjusted_winpct(home_winpct, home_pitcher_era, league_avg_era, weight)
    away_adj = pitcher_adjusted_winpct(away_winpct, away_pitcher_era, league_avg_era, weight)
    return log5(home_adj, away_adj)
