"""tennis_model_anchor — market_type dispatch."""
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.infrastructure.data.tennis_ratings_store import PlayerSnapshot
from src.strategy.enrichment.tennis_model_anchor import compute_model_anchor


def _mk_snapshot(mu: float, serve: float) -> PlayerSnapshot:
    return PlayerSnapshot(
        rating=Rating(mu=mu, phi=80),
        serve_by_surface={"Hard": PlayerServeStats(serve, 1.0 - serve + 0.05, 5000)},
    )


def test_h2h_uses_model():
    a = _mk_snapshot(1750, 0.66)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="moneyline",
        a_snapshot=a, b_snapshot=b,
        surface="Hard", best_of=3,
    )
    assert p is not None and p > 0.6


def test_set_handicap_minus_15():
    a = _mk_snapshot(1700, 0.65)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="tennis_set_handicap",
        a_snapshot=a, b_snapshot=b,
        surface="Hard", best_of=3,
        handicap=-1.5,
    )
    assert p is not None and 0 < p < 1


def test_unknown_market_returns_none():
    a = _mk_snapshot(1700, 0.65)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="unknown_market",
        a_snapshot=a, b_snapshot=b,
        surface="Hard", best_of=3,
    )
    assert p is None


def test_missing_surface_uses_cross_surface_fallback():
    """2026-06-02: Hedef surface yoksa diger surface'lerden n_points-agirlikli
    ortalama kullanilir (Sackmann Grass %89, Clay %34, Hard %20 eksik — fallback
    yoksa alt market'lerin yarisi fail oluyordu).
    """
    a = _mk_snapshot(1700, 0.65)
    b = _mk_snapshot(1500, 0.58)
    p = compute_model_anchor(
        market_type="moneyline",
        a_snapshot=a, b_snapshot=b,
        surface="Clay", best_of=3,  # Hard data var, Clay yok → Hard fallback
    )
    # Fallback aktif: Hard verisinden cross-surface ortalama dönmeli (None değil)
    assert p is not None
    assert 0.0 < p < 1.0


def test_no_surface_data_returns_none():
    """Hicbir surface'de serve verisi yoksa None dönmeli (gerçek veri eksikligi)."""
    from src.domain.pricing.tennis.glicko import Rating
    from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
    empty_a = PlayerSnapshot(rating=Rating(mu=1700, phi=80), serve_by_surface={})
    empty_b = PlayerSnapshot(rating=Rating(mu=1500, phi=80), serve_by_surface={})
    p = compute_model_anchor(
        market_type="moneyline",
        a_snapshot=empty_a, b_snapshot=empty_b,
        surface="Hard", best_of=3,
    )
    assert p is None
