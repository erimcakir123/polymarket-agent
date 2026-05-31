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
    assert result.fail_reason == EnrichFailReason.EVENT_NO_MATCH


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
