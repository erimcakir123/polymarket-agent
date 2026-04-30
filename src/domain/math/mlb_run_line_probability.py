"""MLB Run Line probability via Skellam-distribution margin.

Each team's runs per game ~ Poisson(lambda_team). The score margin
M = home_runs - away_runs ~ Skellam(lambda_home, lambda_away).

P(team covers -1.5 favorite) = P(M >= 2) = 1 - CDF(1)
P(team covers +1.5 underdog) = P(M >= -1) = 1 - CDF(-2)
                             = P(opponent loses by less than 2)

Inputs: per-game runs scored estimates (post pitcher adjustment).
Use mlb_pitcher_adjustment outputs to shift these before calling.
"""
from __future__ import annotations

from scipy.stats import skellam

AVG_RUNS_PER_GAME_TEAM: float = 4.50  # 2020-2024 MLB league avg per team
_LAMBDA_FLOOR: float = 0.5            # safety floor (very weak team)


def p_team_covers_runline(
    team_runs_per_game: float,
    opp_runs_per_game: float,
    line: float,
    is_favorite: bool,
) -> float:
    """Probability team covers the run line.

    Args:
        team_runs_per_game: this team's expected runs (lambda)
        opp_runs_per_game: opponent's expected runs (lambda)
        line: run line magnitude, e.g. 1.5
        is_favorite: True for -line side, False for +line side

    Returns:
        P(cover) in [0.0, 1.0].
    """
    lam_team = max(team_runs_per_game, _LAMBDA_FLOOR)
    lam_opp = max(opp_runs_per_game, _LAMBDA_FLOOR)

    if team_runs_per_game <= 0 and opp_runs_per_game <= 0:
        return 0.5

    if is_favorite:
        threshold = int(line + 0.5)  # 1.5 → 2
        return float(skellam.sf(threshold - 1, lam_team, lam_opp))
    else:
        threshold = -int(line + 0.5)  # +1.5 → -2
        return float(skellam.sf(threshold, lam_team, lam_opp))
