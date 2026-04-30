import pytest
from src.domain.math.mlb_run_line_probability import (
    p_team_covers_runline,
    AVG_RUNS_PER_GAME_TEAM,
)


def test_balanced_teams_neg_15_runline_below_50():
    """Equal teams (4.5 RS each), -1.5 line favorite → P < 0.5 (need 2+ run win)."""
    p = p_team_covers_runline(
        team_runs_per_game=AVG_RUNS_PER_GAME_TEAM,
        opp_runs_per_game=AVG_RUNS_PER_GAME_TEAM,
        line=1.5,
        is_favorite=True,
    )
    assert 0.30 < p < 0.45


def test_balanced_teams_plus_15_runline_above_50():
    """Equal teams, +1.5 line underdog → P > 0.5 (lose by 1 still covers)."""
    p = p_team_covers_runline(
        team_runs_per_game=AVG_RUNS_PER_GAME_TEAM,
        opp_runs_per_game=AVG_RUNS_PER_GAME_TEAM,
        line=1.5,
        is_favorite=False,
    )
    assert 0.55 < p < 0.70


def test_strong_team_neg_15_higher_p():
    """Strong offense team -1.5 → higher P than balanced."""
    p_strong = p_team_covers_runline(5.5, 4.0, 1.5, is_favorite=True)
    p_balanced = p_team_covers_runline(4.5, 4.5, 1.5, is_favorite=True)
    assert p_strong > p_balanced


def test_weak_team_plus_15_higher_p():
    """Weak underdog +1.5 → non-trivial P (might lose by 1), but low vs strong opp."""
    p = p_team_covers_runline(3.0, 5.5, 1.5, is_favorite=False)
    assert p > 0.30


def test_zero_lambda_safe_fallback():
    """Both teams 0 RS/G → fallback 0.5."""
    p = p_team_covers_runline(0.0, 0.0, 1.5, is_favorite=True)
    assert p == pytest.approx(0.5, abs=0.01)


def test_complement_property():
    """P(team covers -1.5) + P(opp covers +1.5) = 1.0 (modulo Skellam atomic mass)."""
    p_fav = p_team_covers_runline(5.0, 4.0, 1.5, is_favorite=True)
    p_dog = p_team_covers_runline(4.0, 5.0, 1.5, is_favorite=False)
    assert p_fav + p_dog == pytest.approx(1.0, abs=0.05)
