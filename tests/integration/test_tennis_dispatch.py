"""Tennis dispatch — sport_tag tennis ise model, değilse veya alt market fail ise fallback."""
from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import calculate_bookmaker_probability
from src.domain.pricing.tennis.glicko import Rating
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.domain.pricing.tennis.serve_metrics import PlayerServeStats
from src.models.market import MarketData
from src.strategy.enrichment.tennis_dispatch import enrich_with_tennis_dispatch


def _market(question: str, sport: str = "tennis", market_type: str = "moneyline") -> MarketData:
    return MarketData(
        condition_id="0xa", question=question, slug="x",
        yes_token_id="t1", no_token_id="t2",
        yes_price=0.5, no_price=0.5, liquidity=100, volume_24h=100,
        end_date_iso="2026-06-01T00:00:00Z",
        sport_tag=sport, sports_market_type=market_type,
    )


def _snap(mu: float, serve: float) -> PlayerSnapshot:
    return PlayerSnapshot(
        rating=Rating(mu=mu, phi=80),
        serve_by_surface={"Hard": PlayerServeStats(serve, 1.0 - serve + 0.05, 5000)},
    )


def _fake_bookmaker_enrich(market: MarketData) -> EnrichResult:
    """Simulates the existing odds-API enrich path."""
    return EnrichResult(
        probability=calculate_bookmaker_probability(
            bookmaker_prob=0.55, num_bookmakers=5.0, has_sharp=True,
        ),
        fail_reason=None,
    )


def test_non_tennis_uses_fallback():
    m = _market("NBA Lakers vs Celtics", sport="nba")
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich, ratings={})
    assert result.probability is not None
    # Came from fallback (bookmaker 0.55)
    assert abs(result.probability.bookmaker_prob - 0.55) < 1e-6


def test_tennis_moneyline_uses_model_when_available():
    m = _market("Alice vs Bob")
    ratings = {"Alice": _snap(1750, 0.66), "Bob": _snap(1500, 0.58)}
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich, ratings=ratings)
    assert result.probability is not None
    assert result.probability.confidence == "A"
    # Model output > bookmaker (Alice strong favorite)
    assert result.probability.probability > 0.6


def test_tennis_moneyline_falls_back_when_ratings_missing():
    m = _market("Unknown vs Player")
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich, ratings={})
    # Empty ratings → fall back to bookmaker
    assert result.probability is not None
    assert abs(result.probability.bookmaker_prob - 0.55) < 1e-6


def test_tennis_alt_market_no_fallback():
    """Alt market'te model fail ise BOOKMAKER FALLBACK YOK — cascade bug kapanır."""
    m = _market("Alice vs Bob", market_type="tennis_set_handicap")
    # Empty ratings → model None
    result = enrich_with_tennis_dispatch(m, _fake_bookmaker_enrich, ratings={})
    assert result.probability is None
    assert result.fail_reason is not None


def test_extract_market_params_handicap():
    """K1 regression: tennis_set_handicap question'dan handicap parse edilir."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params(
        "Alice -1.5 sets win", "tennis_set_handicap",
    )
    assert handicap == -1.5
    assert line is None


def test_extract_market_params_total():
    """K1 regression: tennis_match_totals question'dan line parse edilir."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params(
        "Over 22.5 games", "tennis_match_totals",
    )
    assert line == 22.5
    assert handicap is None


def test_extract_market_params_unknown_type_returns_none():
    """K1 regression: bilinmeyen market_type → None tuple, exception YOK."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params("anything", "unknown_market")
    assert line is None
    assert handicap is None


def test_extract_market_params_no_match_returns_none():
    """K1 regression: handicap market'te handicap value yok → None (not crash)."""
    from src.strategy.enrichment.tennis_dispatch import _extract_market_params
    line, handicap = _extract_market_params("Alice vs Bob", "tennis_set_handicap")
    assert handicap is None
    assert line is None


def test_surface_inferred_for_grand_slam():
    """K3 regression: question'da 'Wimbledon' geçerse Grass surface kullanılır.

    Eski sürümde her zaman Hard → Grass-spesifik serve stat'ları kullanılmazdı.
    """
    from src.strategy.enrichment.tennis_dispatch import _infer_surface
    assert _infer_surface("Wimbledon final: Alice vs Bob") == "Grass"
    assert _infer_surface("French Open R3: X vs Y") == "Clay"
    assert _infer_surface("Roland Garros QF") == "Clay"
    assert _infer_surface("US Open R1") == "Hard"
    assert _infer_surface("ATP 250 generic") == "Hard"
