"""Serve metrics aggregator — MatchRecord listesi → per-player surface-spesifik servis %."""
from src.domain.pricing.tennis.serve_metrics import (
    PlayerServeStats,
    aggregate_serve_stats,
    point_win_on_serve,
)
from src.infrastructure.data.sackmann_csv_loader import MatchRecord


def _mk(
    winner: str,
    loser: str,
    surface: str,
    w_pts: int = 80,
    w_1in: int = 50,
    w_1won: int = 40,
    w_2won: int = 20,
    l_pts: int = 80,
    l_1in: int = 50,
    l_1won: int = 30,
    l_2won: int = 15,
) -> MatchRecord:
    return MatchRecord(
        tourney_id="x",
        tourney_date="20260101",
        surface=surface,
        winner_name=winner,
        loser_name=loser,
        w_svpt=w_pts,
        w_1st_in=w_1in,
        w_1st_won=w_1won,
        w_2nd_won=w_2won,
        w_sv_gms=10,
        l_svpt=l_pts,
        l_1st_in=l_1in,
        l_1st_won=l_1won,
        l_2nd_won=l_2won,
        l_sv_gms=10,
        best_of=3,
        score="6-4 6-4",
    )


def test_aggregate_single_match():
    matches = [_mk("Alice", "Bob", "Hard")]
    stats = aggregate_serve_stats(matches)
    alice = stats[("Alice", "Hard")]
    assert abs(alice.serve_pts_won_pct - 0.75) < 1e-6


def test_aggregate_separates_surface():
    matches = [
        _mk("Alice", "Bob", "Hard", w_1won=40, w_2won=20),
        _mk("Alice", "Carol", "Clay", w_1won=30, w_2won=10),
    ]
    stats = aggregate_serve_stats(matches)
    assert ("Alice", "Hard") in stats
    assert ("Alice", "Clay") in stats
    assert stats[("Alice", "Hard")].serve_pts_won_pct > stats[("Alice", "Clay")].serve_pts_won_pct


def test_aggregate_accumulates_multiple_matches():
    matches = [
        _mk("Alice", "Bob", "Hard", w_pts=100, w_1won=50, w_2won=25),
        _mk("Alice", "Carol", "Hard", w_pts=100, w_1won=50, w_2won=25),
    ]
    stats = aggregate_serve_stats(matches)
    assert abs(stats[("Alice", "Hard")].serve_pts_won_pct - 0.75) < 1e-6


def test_point_win_on_serve_combines_two_players():
    a = PlayerServeStats(serve_pts_won_pct=0.65, return_pts_won_pct=0.40, n_points=1000)
    b = PlayerServeStats(serve_pts_won_pct=0.60, return_pts_won_pct=0.35, n_points=1000)
    p = point_win_on_serve(a, b)
    assert 0.55 < p < 0.75
