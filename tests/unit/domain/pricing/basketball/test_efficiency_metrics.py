"""Efficiency metrics — GameRecord listesi → her takımın AdjO/AdjD/Pace."""
from __future__ import annotations
import pytest
from src.infrastructure.data.basketball.schemas import GameRecord
from src.domain.pricing.basketball.efficiency_metrics import (
    compute_team_efficiency, _raw_efficiency_per_game,
)
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency


def _game(home: str, away: str, hs: int, as_: int, hp: float, ap: float) -> GameRecord:
    return GameRecord(
        game_id=f"{home}-{away}", season="2024-25",
        game_date_utc="2024-11-01T00:00:00Z",
        home_team=home, away_team=away,
        home_score=hs, away_score=as_,
        home_possessions=hp, away_possessions=ap,
        is_final=True, league="nba",
    )


def test_raw_efficiency_per_game_correct():
    g = _game("LAL", "GSW", 110, 100, 100.0, 100.0)
    lal_o, lal_d, lal_pace = _raw_efficiency_per_game(g, team="LAL")
    assert lal_o == 110.0  # 110 / 100 * 100
    assert lal_d == 100.0  # 100 / 100 * 100 (opp scored)
    assert lal_pace == 100.0


def test_compute_team_efficiency_averages_multiple_games():
    games = [
        _game("LAL", "GSW", 110, 100, 100.0, 100.0),
        _game("LAL", "PHX", 120, 90, 100.0, 100.0),
    ]
    eff = compute_team_efficiency(games, team="LAL")
    assert isinstance(eff, TeamEfficiency)
    # AdjO: (110 + 120) / 2 = 115
    assert abs(eff.adj_o - 115.0) < 0.01
    # AdjD: (100 + 90) / 2 = 95
    assert abs(eff.adj_d - 95.0) < 0.01
    # Pace: 100
    assert abs(eff.adj_pace - 100.0) < 0.01


def test_compute_team_efficiency_team_not_in_games_returns_none():
    games = [_game("LAL", "GSW", 110, 100, 100.0, 100.0)]
    assert compute_team_efficiency(games, team="BOS") is None


def test_compute_team_efficiency_empty_games_returns_none():
    assert compute_team_efficiency([], team="LAL") is None


def test_outlier_low_pace_filtered_out():
    """Anormal düşük possessions (10) içeren maç AdjO hesabına dahil edilmez."""
    games = [
        _game("LAL", "GSW", 110, 100, 100.0, 100.0),  # normal
        _game("LAL", "PHX", 110, 100, 10.0, 10.0),    # outlier
    ]
    eff = compute_team_efficiency(games, team="LAL")
    assert eff is not None
    assert abs(eff.adj_pace - 100.0) < 0.01
    assert abs(eff.adj_o - 110.0) < 0.01


def test_outlier_high_pace_filtered_out():
    """200 possessions = tarihsel olarak imkansız, filtre."""
    games = [
        _game("LAL", "GSW", 110, 100, 100.0, 100.0),
        _game("LAL", "PHX", 250, 100, 200.0, 200.0),  # outlier
    ]
    eff = compute_team_efficiency(games, team="LAL")
    assert eff is not None
    assert abs(eff.adj_pace - 100.0) < 0.01
