"""tennis_ratings.json read/write — round-trip ve missing file."""
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.infrastructure.data.tennis_ratings_store import (
    PlayerSnapshot,
    load_ratings,
    save_ratings,
)


def test_save_and_load_round_trip(tmp_path):
    snap = {
        "Alice": PlayerSnapshot(
            rating=Rating(mu=1700, phi=80, sigma=0.06),
            serve_by_surface={
                "Hard": PlayerServeStats(0.65, 0.40, 5000),
                "Clay": PlayerServeStats(0.60, 0.38, 3000),
            },
        ),
    }
    path = tmp_path / "tennis_ratings.json"
    save_ratings(snap, path)
    loaded = load_ratings(path)
    assert "Alice" in loaded
    assert abs(loaded["Alice"].rating.mu - 1700) < 1e-6
    assert "Hard" in loaded["Alice"].serve_by_surface


def test_load_missing_file_returns_empty(tmp_path):
    loaded = load_ratings(tmp_path / "nonexistent.json")
    assert loaded == {}
