"""tennis_anchor_enricher — tennis market'ler için model-anchored EnrichResult.

Mock ratings + pricer'lar kullanır (gerçek dosya yok).
"""
from src.domain.analysis.enrich_outcome import EnrichFailReason
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.strategy.enrichment.tennis_anchor_enricher import enrich_tennis_from_model


def _snap(mu: float, serve: float) -> PlayerSnapshot:
    return PlayerSnapshot(
        rating=Rating(mu=mu, phi=80),
        serve_by_surface={"Hard": PlayerServeStats(serve, 1.0 - serve + 0.05, 5000)},
    )


def test_h2h_returns_probability():
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_tennis_from_model(
        player_a="Alice",
        player_b="Bob",
        market_type="moneyline",
        surface="Hard",
        best_of=3,
        ratings=ratings,
    )
    assert result.probability is not None
    assert result.fail_reason is None
    assert result.probability.probability > 0.6
    # Kullanıcı kararı: Sackmann sharp-equivalent → A confidence (canlı trade aktif)
    assert result.probability.confidence == "A"


def test_missing_player_returns_fail():
    ratings = {"Alice": _snap(1700, 0.65)}
    result = enrich_tennis_from_model(
        player_a="Alice",
        player_b="Unknown",
        market_type="moneyline",
        surface="Hard",
        best_of=3,
        ratings=ratings,
    )
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS


def test_unsupported_market_returns_fail():
    ratings = {"Alice": _snap(1700, 0.65), "Bob": _snap(1500, 0.58)}
    result = enrich_tennis_from_model(
        player_a="Alice",
        player_b="Bob",
        market_type="weird_market",
        surface="Hard",
        best_of=3,
        ratings=ratings,
    )
    assert result.probability is None


def test_calibration_curve_corrects_probability():
    """Calibration curve uygulanırsa raw model çıktısı düzeltilir."""
    from src.domain.pricing.tennis.calibration import CalibrationCurve
    ratings = {"Alice": _snap(1900, 0.70), "Bob": _snap(1400, 0.55)}
    # Curve: 0.85 → 0.65 (overconfidence düzelt)
    flatten_curve = CalibrationCurve(
        bin_midpoints=tuple(0.05 + 0.1 * i for i in range(10)),
        bin_observed=(0.17, 0.23, 0.31, 0.40, 0.48, 0.55, 0.62, 0.68, 0.65, 0.70),
        n_bins=10,
    )
    raw = enrich_tennis_from_model(
        player_a="Alice", player_b="Bob", market_type="moneyline",
        surface="Hard", best_of=3, ratings=ratings,
    )
    calibrated = enrich_tennis_from_model(
        player_a="Alice", player_b="Bob", market_type="moneyline",
        surface="Hard", best_of=3, ratings=ratings,
        calibration_curves={"moneyline": flatten_curve},
    )
    # Strong fav raw > 0.70; calibrated daha düşük (curve overconfidence'i kırar)
    assert raw.probability is not None
    assert calibrated.probability is not None
    assert raw.probability.probability > 0.70
    assert calibrated.probability.probability < raw.probability.probability


def test_set_handicap_uses_pricer():
    ratings = {"Alice": _snap(1700, 0.65), "Bob": _snap(1500, 0.58)}
    result = enrich_tennis_from_model(
        player_a="Alice",
        player_b="Bob",
        market_type="tennis_set_handicap",
        surface="Hard",
        best_of=3,
        ratings=ratings,
        handicap=-1.5,
    )
    assert result.probability is not None
    assert 0 < result.probability.probability < 1
