"""Basketball dispatch — model/bookmaker yönlendirmesi."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import BasketballConfig
from src.domain.analysis.enrich_outcome import EnrichResult
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.models.market import MarketData
from src.strategy.enrichment.basketball_dispatch import (
    enrich_with_basketball_dispatch,
)


def _market(sport_tag="nba", slug="nba-lal-gsw-2024-11-01",
            market_type="moneyline", question="Will Lakers beat Warriors?"):
    return MarketData(
        condition_id="cid1",
        question=question,
        slug=slug,
        yes_token_id="tok_yes",
        no_token_id="tok_no",
        yes_price=0.5,
        no_price=0.5,
        liquidity=10000.0,
        volume_24h=10000.0,
        tags=[sport_tag],
        end_date_iso="2024-11-02T00:00:00Z",
        sport_tag=sport_tag,
        sports_market_type=market_type,
        event_id="ev1",
    )


def test_non_basketball_falls_to_bookmaker():
    bm = MagicMock(return_value=EnrichResult(probability=None, fail_reason=None))
    market = _market(sport_tag="mlb")
    enrich_with_basketball_dispatch(
        market, bm, ratings={}, efficiencies={},
        basketball_cfg=BasketballConfig(),
    )
    bm.assert_called_once_with(market)


def test_moneyline_no_ratings_falls_to_bookmaker():
    bm = MagicMock(return_value=EnrichResult(probability=None, fail_reason=None))
    market = _market(sport_tag="nba", market_type="moneyline")
    enrich_with_basketball_dispatch(
        market, bm, ratings={}, efficiencies={},
        basketball_cfg=BasketballConfig(),
    )
    bm.assert_called_once()


def test_basketball_with_ratings_returns_model():
    bm = MagicMock()
    market = _market(sport_tag="nba", market_type="moneyline")
    ratings = {"nba": {"LAL": EloRating(rating=1600.0), "GSW": EloRating(rating=1400.0)}}
    eff = {"nba": {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }}
    res = enrich_with_basketball_dispatch(
        market, bm, ratings=ratings, efficiencies=eff,
        basketball_cfg=BasketballConfig(),
    )
    assert res.probability is not None
    bm.assert_not_called()


def test_cbb_alias_routes_to_ncaab():
    """Polymarket 'cbb' sport_tag NCAAB ile aynı lig."""
    bm = MagicMock(return_value=EnrichResult(probability=None, fail_reason=None))
    market = _market(sport_tag="cbb", slug="cbb-duke-unc-2024-12-01")
    ratings = {"ncaab": {"DUKE": EloRating(rating=1600.0), "UNC": EloRating(rating=1500.0)}}
    eff = {"ncaab": {
        "DUKE": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=72.0),
        "UNC": TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=72.0),
    }}
    res = enrich_with_basketball_dispatch(
        market, bm, ratings=ratings, efficiencies=eff,
        basketball_cfg=BasketballConfig(),
    )
    assert res.probability is not None


def test_extract_line_from_polymarket_slug_total_pt_format():
    """Polymarket slug pattern: '...-total-171pt5' → line=171.5 (Bug fix 2026-06-01)."""
    from src.strategy.enrichment.basketball_dispatch import _extract_line
    line = _extract_line(
        question="Will Storm vs Wings total points be over 171.5?",
        market_type="totals",
        slug="wnba-sea-dal-2026-06-01-total-171pt5",
    )
    assert line == 171.5


def test_extract_line_from_slug_only_no_question_decimal():
    """Polymarket question yoksa bile slug'dan parse edebilmeli."""
    from src.strategy.enrichment.basketball_dispatch import _extract_line
    line = _extract_line(
        question="",  # Polymarket bazen boş bırakır
        market_type="totals",
        slug="wnba-min-phx-2026-06-01-total-168pt5",
    )
    assert line == 168.5


def test_extract_line_spread_from_slug():
    """Spread slug pattern: '...-spread-7pt5' → 7.5."""
    from src.strategy.enrichment.basketball_dispatch import _extract_line
    line = _extract_line(
        question="",
        market_type="spreads",
        slug="nba-lal-gsw-2024-11-01-spread-7pt5",
    )
    assert line == 7.5


def test_extract_line_integer_total_no_decimal():
    """'total-168' (decimal yok) → 168.0."""
    from src.strategy.enrichment.basketball_dispatch import _extract_line
    line = _extract_line(
        question="",
        market_type="totals",
        slug="wnba-sea-dal-2026-06-01-total-168",
    )
    assert line == 168.0


def test_extract_line_returns_none_when_no_pattern():
    from src.strategy.enrichment.basketball_dispatch import _extract_line
    line = _extract_line(question="", market_type="totals", slug="random-slug")
    assert line is None


def test_alt_market_unknown_team_no_bookmaker_fallback():
    """Totals market'te bilinmeyen takım → trade YASAK (cascade bug önleme)."""
    bm = MagicMock()
    market = _market(
        sport_tag="nba", market_type="totals",
        slug="nba-xxx-yyy-2024-11-01",
        question="Will Lakers vs Warriors total be over 220.5?",
    )
    ratings = {"nba": {"LAL": EloRating(), "GSW": EloRating()}}
    eff = {"nba": {"LAL": TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0),
                   "GSW": TeamEfficiency(adj_o=110.0, adj_d=110.0, adj_pace=100.0)}}
    res = enrich_with_basketball_dispatch(
        market, bm, ratings=ratings, efficiencies=eff,
        basketball_cfg=BasketballConfig(),
    )
    assert res.probability is None
    assert res.fail_reason is not None
    bm.assert_not_called()
