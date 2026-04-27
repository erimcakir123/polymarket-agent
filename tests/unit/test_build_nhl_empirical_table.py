"""build_nhl_empirical_table.py fonksiyonları için unit testler.

Ağ çağrısı yok — sadece mock DataFrame ile saf hesaplama test edilir.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

# Script henüz yazılmadıysa import hataları testte yakalanır
from scripts.build_nhl_empirical_table import (
    reconstruct_game_states,
    aggregate_win_frequencies,
    compute_avg_goals_per_game,
)


def _make_shots(rows: list[dict]) -> pd.DataFrame:
    """Test helper: shot satırları → tam şema DataFrame."""
    df = pd.DataFrame(rows)
    for col in ["homeTeamGoals", "awayTeamGoals", "homeTeamWon", "goal", "isPlayoffGame"]:
        if col not in df.columns:
            df[col] = 0
    df["game_id"] = df["game_id"].astype(str)
    df["period"] = df["period"].astype(int)
    df["time"] = df["time"].astype(float)
    return df


# ── reconstruct_game_states ──────────────────────────────────────────────────

def test_reconstruct_tied_state_leading_team_won_none():
    """Berabere tick'lerde leading_team_won NaN olmalı."""
    df = _make_shots([
        {"game_id": "g1", "period": 1, "time": 0.0,
         "homeTeamGoals": 0, "awayTeamGoals": 0, "homeTeamWon": 1, "goal": 0},
    ])
    states = reconstruct_game_states(df)
    # İlk tick (seconds_remaining=3600) skor 0-0 → tied
    first = states[states["seconds_remaining"] == 3600].iloc[0]
    assert pd.isna(first["leading_team_won"])


def test_reconstruct_home_leading_home_wins():
    """Ev sahibi önde → leading_team_won = homeTeamWon = 1."""
    df = _make_shots([
        {"game_id": "g1", "period": 2, "time": 600.0,
         "homeTeamGoals": 1, "awayTeamGoals": 0, "homeTeamWon": 1, "goal": 1},
    ])
    states = reconstruct_game_states(df)
    # P2, 10 dk sonra (game_seconds=1800) → sonraki tick'ler home=1, away=0
    leading_ticks = states[states["abs_score_diff"] == 1].dropna(subset=["leading_team_won"])
    assert len(leading_ticks) > 0
    assert (leading_ticks["leading_team_won"] == 1.0).all()


def test_reconstruct_away_leading_home_loses():
    """Deplasman önde → leading_team_won = 1 - homeTeamWon = 1."""
    df = _make_shots([
        {"game_id": "g1", "period": 3, "time": 0.0,
         "homeTeamGoals": 0, "awayTeamGoals": 2, "homeTeamWon": 0, "goal": 0},
    ])
    states = reconstruct_game_states(df)
    leading_ticks = states[states["abs_score_diff"] == 2].dropna(subset=["leading_team_won"])
    assert len(leading_ticks) > 0
    assert (leading_ticks["leading_team_won"] == 1.0).all()


def test_reconstruct_ot_periods_excluded():
    """Period 4 (OT) satırları output'a dahil edilmemeli."""
    df = _make_shots([
        {"game_id": "g1", "period": 1, "time": 0.0,
         "homeTeamGoals": 0, "awayTeamGoals": 0, "homeTeamWon": 1, "goal": 0},
        {"game_id": "g1", "period": 4, "time": 100.0,
         "homeTeamGoals": 1, "awayTeamGoals": 0, "homeTeamWon": 1, "goal": 1},
    ])
    states = reconstruct_game_states(df)
    # Period 4 tick'i output'ta olmamalı (sadece 1-2-3)
    assert (states["period"].isin([1, 2, 3])).all()


def test_reconstruct_seconds_remaining_range():
    """seconds_remaining 0-3600 aralığında olmalı."""
    df = _make_shots([
        {"game_id": "g1", "period": 1, "time": 0.0,
         "homeTeamGoals": 0, "awayTeamGoals": 0, "homeTeamWon": 1, "goal": 0},
    ])
    states = reconstruct_game_states(df)
    assert states["seconds_remaining"].min() >= 0
    assert states["seconds_remaining"].max() <= 3600


# ── aggregate_win_frequencies ────────────────────────────────────────────────

def _make_states(n_wins: int, n_total: int,
                 period: int = 3, deficit: int = 1, seconds: int = 60) -> pd.DataFrame:
    """Test helper: n_total satır, n_wins tanesi win."""
    leading_won = [1.0] * n_wins + [0.0] * (n_total - n_wins)
    return pd.DataFrame({
        "game_id": [f"g{i}" for i in range(n_total)],
        "period": period,
        "seconds_remaining": seconds,
        "abs_score_diff": deficit,
        "leading_team_won": leading_won,
    })


def test_aggregate_win_freq_high_sample_returns_entry():
    """Yeterli sample → win_prob dolu."""
    states = _make_states(n_wins=40, n_total=50, period=3, deficit=1, seconds=60)
    table = aggregate_win_frequencies(states)
    key = "3_1_60"
    assert key in table
    assert table[key] is not None
    assert 0.0 < table[key]["win_prob"] < 1.0
    assert table[key]["n"] == 50


def test_aggregate_win_freq_low_sample_returns_none():
    """MIN_N altı sample → None."""
    states = _make_states(n_wins=10, n_total=15, period=3, deficit=1, seconds=60)
    table = aggregate_win_frequencies(states)
    key = "3_1_60"
    assert key in table
    assert table[key] is None


def test_aggregate_win_freq_deficit_clamped():
    """deficit=5 → DEFICIT_CAP=4 ile klample, key='3_4_60'."""
    states = _make_states(n_wins=40, n_total=50, period=3, deficit=5, seconds=60)
    table = aggregate_win_frequencies(states)
    assert "3_4_60" in table
    assert "3_5_60" not in table


def test_aggregate_win_freq_tied_rows_excluded():
    """leading_team_won=NaN satırları hesaplamaya dahil edilmemeli."""
    rows_tied = pd.DataFrame({
        "game_id": [f"t{i}" for i in range(100)],
        "period": 3,
        "seconds_remaining": 60,
        "abs_score_diff": 0,
        "leading_team_won": np.nan,
    })
    table = aggregate_win_frequencies(rows_tied)
    # Tied rows (deficit=0) — NaN filtresi sonrası n=0 → None veya key yok
    key = "3_0_60"
    assert table.get(key) is None


def test_aggregate_time_bucket_snaps_down():
    """seconds_remaining=75 → bucket=60 (30s snap-down)."""
    states = _make_states(n_wins=40, n_total=50, period=3, deficit=1, seconds=75)
    table = aggregate_win_frequencies(states)
    assert "3_1_60" in table
    assert "3_1_75" not in table


# ── compute_avg_goals_per_game ───────────────────────────────────────────────

def test_avg_goals_simple():
    """2 maç, 6 gol → 3.0 gol/maç."""
    df = _make_shots([
        {"game_id": "g1", "period": 1, "time": 300.0, "goal": 1,
         "homeTeamGoals": 1, "awayTeamGoals": 0, "homeTeamWon": 1},
        {"game_id": "g1", "period": 2, "time": 600.0, "goal": 1,
         "homeTeamGoals": 2, "awayTeamGoals": 0, "homeTeamWon": 1},
        {"game_id": "g1", "period": 3, "time": 900.0, "goal": 1,
         "homeTeamGoals": 3, "awayTeamGoals": 0, "homeTeamWon": 1},
        {"game_id": "g2", "period": 1, "time": 400.0, "goal": 1,
         "homeTeamGoals": 0, "awayTeamGoals": 1, "homeTeamWon": 0},
        {"game_id": "g2", "period": 2, "time": 800.0, "goal": 1,
         "homeTeamGoals": 0, "awayTeamGoals": 2, "homeTeamWon": 0},
        {"game_id": "g2", "period": 3, "time": 1000.0, "goal": 1,
         "homeTeamGoals": 0, "awayTeamGoals": 3, "homeTeamWon": 0},
    ])
    states_dummy = pd.DataFrame()  # not used in function
    result = compute_avg_goals_per_game(states_dummy, [df])
    assert abs(result - 3.0) < 0.01


def test_avg_goals_no_shots_returns_zero():
    """Gol yok → 0.0."""
    df = _make_shots([
        {"game_id": "g1", "period": 1, "time": 0.0, "goal": 0,
         "homeTeamGoals": 0, "awayTeamGoals": 0, "homeTeamWon": 1},
    ])
    result = compute_avg_goals_per_game(pd.DataFrame(), [df])
    assert result == 0.0
