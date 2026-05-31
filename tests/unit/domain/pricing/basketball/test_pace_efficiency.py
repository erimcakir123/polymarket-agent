"""Pace × efficiency projeksiyon formülü."""
from __future__ import annotations
import pytest
from src.domain.pricing.basketball.pace_efficiency import (
    TeamEfficiency, project_game,
)


def test_project_game_average_teams_yields_league_average_total():
    """İki ortalama takım (AdjO=AdjD=110, Pace=100) → toplam ≈ 220 (NBA average)."""
    avg = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    proj = project_game(avg, avg)
    assert abs(proj.total - 220.0) < 0.5
    assert abs(proj.margin) < 0.5  # eşit takımlar → 0 margin


def test_project_game_offense_strong_home_outscores():
    home = TeamEfficiency(adj_o=120.0, adj_d=110.0, adj_pace=100.0)
    away = TeamEfficiency(adj_o=100.0, adj_d=110.0, adj_pace=100.0)
    proj = project_game(home, away)
    assert proj.home_score > proj.away_score
    assert proj.margin > 5.0  # home offense 10 puan üstün


def test_project_game_high_pace_inflates_total():
    """Pace 100 → 110 (%10 daha hızlı) → toplam +%10."""
    slow = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    fast = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=110.0)
    proj_slow = project_game(slow, slow)
    proj_fast = project_game(fast, fast)
    assert proj_fast.total > proj_slow.total
    # Yaklaşık %10 fark beklenir (yumuşak eşik)
    assert (proj_fast.total - proj_slow.total) / proj_slow.total > 0.08


def test_project_game_defense_strong_lowers_opponent_score():
    weak_def = TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)
    strong_def = TeamEfficiency(adj_o=110.0, adj_d=100.0, adj_pace=100.0)
    proj_weak = project_game(weak_def, weak_def)
    proj_strong = project_game(strong_def, weak_def)
    # strong_def evde → weak_def deplasmanda → strong_def düşman skoru düşürür
    assert proj_strong.away_score < proj_weak.away_score
