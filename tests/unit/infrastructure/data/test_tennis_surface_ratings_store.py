"""tennis_surface_ratings_store testleri — PLAN-DATA1 (save + round-trip)."""
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.infrastructure.data.tennis_surface_ratings_store import (
    load_all_surfaces,
    save_all_surfaces,
)


def test_save_all_surfaces_roundtrip_load(tmp_path):
    path = tmp_path / "surface.json"
    overall = {"Alice A": Rating(mu=1700.0, phi=60.0, sigma=0.06)}
    by_surface = {
        "Hard": {"Alice A": Rating(mu=1750.0, phi=90.0, sigma=0.06)},
        "Clay": {},
        "Grass": {"Alice A": Rating(mu=1600.0, phi=140.0, sigma=0.06)},
    }
    serve = {"Alice A": {"Hard": PlayerServeStats(
        serve_pts_won_pct=0.62, return_pts_won_pct=0.38, n_points=500,
    )}}
    save_all_surfaces(overall, by_surface, serve, path)

    loaded = load_all_surfaces(path)
    # Hard: yüzey phi 90 < 150 eşik → yüzey reytingi kullanılır
    assert loaded["Hard"]["Alice A"].rating.mu == 1750.0
    # Clay: yüzey kaydı yok → overall'a düşer
    assert loaded["Clay"]["Alice A"].rating.mu == 1700.0
    # Serve round-trip
    assert loaded["Hard"]["Alice A"].serve_by_surface["Hard"].n_points == 500


def test_save_all_surfaces_grass_phi_fallback_to_overall(tmp_path):
    path = tmp_path / "surface.json"
    overall = {"Bob B": Rating(mu=1500.0, phi=65.0, sigma=0.06)}
    by_surface = {
        "Hard": {},
        "Clay": {},
        "Grass": {"Bob B": Rating(mu=1400.0, phi=200.0, sigma=0.06)},  # eşik üstü
    }
    save_all_surfaces(overall, by_surface, {}, path)
    loaded = load_all_surfaces(path)
    # Grass phi 200 ≥ 150 → overall'a düşmeli (mevcut load davranışı)
    assert loaded["Grass"]["Bob B"].rating.mu == 1500.0
