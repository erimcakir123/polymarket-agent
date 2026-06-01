"""Basketball low-tier + min-games yetki filtresi (tennis ITF paralel)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import BasketballConfig
from src.domain.analysis.enrich_outcome import EnrichResult
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.models.market import MarketData
from src.strategy.enrichment.basketball_dispatch import (
    _is_low_tier_basket,
    enrich_with_basketball_dispatch,
)


def _market(slug: str, sport_tag: str = "nba",
            question: str = "Will A beat B?") -> MarketData:
    return MarketData(
        condition_id="c", question=question, slug=slug,
        yes_token_id="y", no_token_id="n",
        yes_price=0.5, no_price=0.5,
        liquidity=10000.0, volume_24h=10000.0,
        tags=[sport_tag], end_date_iso="2026-01-01T00:00:00Z",
        sport_tag=sport_tag, sports_market_type="moneyline",
        event_id="ev",
    )


def test_nba_preseason_slug_blocked():
    assert _is_low_tier_basket("nba-preseason-lal-gsw-2026-10-01", "") is True


def test_wnba_preseason_blocked():
    assert _is_low_tier_basket("wnba-preseason-sea-dal-2026-04-15", "") is True


def test_ncaab_exhibition_blocked():
    assert _is_low_tier_basket("ncaab-exhibition-duke-2026-11-01", "") is True


def test_play_in_tournament_blocked():
    assert _is_low_tier_basket("nba-play-in-tournament-2026-04-15", "") is True


def test_regular_season_passes():
    assert _is_low_tier_basket("nba-lal-gsw-2026-11-15", "") is False


def test_dispatch_blocks_preseason_market():
    bm = MagicMock(return_value=EnrichResult(probability=None, fail_reason=None))
    market = _market(slug="nba-preseason-lal-gsw-2026-10-01")
    ratings = {"nba": {
        "LAL": EloRating(rating=1600.0, games=20),
        "GSW": EloRating(rating=1400.0, games=20),
    }}
    eff = {"nba": {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }}
    res = enrich_with_basketball_dispatch(
        market, bm, ratings=ratings, efficiencies=eff,
        basketball_cfg=BasketballConfig(),
    )
    assert res.probability is None  # Preseason → model konuşmaz
    bm.assert_not_called()


def test_min_games_filter_blocks_undertrained_team():
    """Sezon başı az maç oynamış takım — rating güvenilmez, model SUS."""
    bm = MagicMock(return_value=EnrichResult(probability=None, fail_reason=None))
    market = _market(slug="nba-lal-gsw-2026-11-15")
    ratings = {"nba": {
        "LAL": EloRating(rating=1600.0, games=3),   # Az maç
        "GSW": EloRating(rating=1400.0, games=20),
    }}
    eff = {"nba": {
        "LAL": TeamEfficiency(adj_o=115.0, adj_d=108.0, adj_pace=100.0),
        "GSW": TeamEfficiency(adj_o=108.0, adj_d=115.0, adj_pace=100.0),
    }}
    res = enrich_with_basketball_dispatch(
        market, bm, ratings=ratings, efficiencies=eff,
        basketball_cfg=BasketballConfig(),
    )
    # moneyline → bookmaker fallback (model konuşmaz ama h2h fallback OK)
    bm.assert_called_once()
    assert res is bm.return_value


def test_new_leagues_in_whitelist():
    """g_league, summer_league, eurocup whitelist'te (2026-06-01 genişletme)."""
    from src.strategy.enrichment.basketball_dispatch import _BASKETBALL_LEAGUES
    assert "g_league" in _BASKETBALL_LEAGUES
    assert "summer_league" in _BASKETBALL_LEAGUES
    assert "eurocup" in _BASKETBALL_LEAGUES


def test_bsl_acb_lega_not_in_whitelist():
    """BRScraper placeholder — bu ligler dispatch'e dahil DEĞİL (Adım 5'te temizlenecek)."""
    from src.strategy.enrichment.basketball_dispatch import _BASKETBALL_LEAGUES
    assert "bsl" not in _BASKETBALL_LEAGUES
    assert "acb" not in _BASKETBALL_LEAGUES
    assert "lega" not in _BASKETBALL_LEAGUES
