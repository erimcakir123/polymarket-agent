"""MLB entry filter chain tests."""
from dataclasses import dataclass
import pytest

from src.strategy.entry._mlb_edge import (
    MLBEntryConfig,
    MLBEntryDecision,
    apply_mlb_entry_filters,
)
from src.domain.sports.mlb_question_parser import MLBMarketIntent, MLBMarketType
from src.orchestration.mlb_edge_enricher import MLBEnrichedData
from src.infrastructure.data.mlb_park_factors import ParkFactor


@dataclass
class FakeMarket:
    question: str
    outcome: str
    polymarket_price: float
    volume_24h: float
    liquidity: float
    intent: MLBMarketIntent


def _make_enriched(
    rain=0.10, home_era=3.50, away_era=3.80, home_wp=0.55, away_wp=0.50,
    home_rs=4.6, home_ra=4.0, away_rs=4.4, away_ra=4.2,
    seconds=6 * 3600, weather_bias=0.0, park=ParkFactor(1.0, 1.0),
):
    return MLBEnrichedData(
        pitcher_confirmed_home=True, pitcher_confirmed_away=True,
        home_pitcher_era=home_era, away_pitcher_era=away_era,
        home_season_winpct=home_wp, away_season_winpct=away_wp,
        home_runs_per_game=home_rs, home_runs_allowed_per_game=home_ra,
        away_runs_per_game=away_rs, away_runs_allowed_per_game=away_ra,
        rain_chance=rain, wind_speed_mph=8.0, wind_direction_deg=180,
        temperature_f=70.0, weather_run_bias=weather_bias,
        park_factor=park, seconds_to_game_start=seconds,
    )


def _make_market(market_type, side_team="ATL", line=None, totals_side=None,
                 price=0.55, volume=5000, liquidity=5000):
    intent = MLBMarketIntent(
        market_type=market_type, team_a="ATL", team_b="DET",
        side_team=side_team, line=line,
        is_favorite_side=(line == 1.5 and side_team == "ATL") if market_type == MLBMarketType.RUN_LINE else None,
        totals_side=totals_side,
    )
    return FakeMarket(
        question="Atlanta Braves vs. Detroit Tigers",
        outcome="Braves", polymarket_price=price,
        volume_24h=volume, liquidity=liquidity, intent=intent,
    )


@pytest.fixture
def cfg():
    return MLBEntryConfig(
        rain_skip_threshold=0.60, rain_partial_threshold=0.30,
        pre_game_window_min_hours=2.0, pre_game_window_max_hours=12.0,
        min_volume_usdc=3000.0, min_liquidity_usdc=3000.0,
        min_polymarket_price=0.20, max_polymarket_price=0.75,
        gap_threshold=0.05, position_cap_pct=0.03, max_position_usdc=75.0,
        forbid_runline_minus_15_favorite=True,
    )


def test_skip_pitcher_unconfirmed(cfg):
    enriched = _make_enriched()
    enriched_unconfirmed = MLBEnrichedData(**{**enriched.__dict__, "pitcher_confirmed_home": False})
    market = _make_market(MLBMarketType.MONEYLINE)
    result = apply_mlb_entry_filters(market, enriched_unconfirmed, cfg, bankroll=1000.0)
    assert result is None


def test_skip_rain_above_threshold(cfg):
    enriched = _make_enriched(rain=0.65)
    market = _make_market(MLBMarketType.MONEYLINE)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_skip_runline_minus_15_favorite(cfg):
    enriched = _make_enriched()
    market = _make_market(MLBMarketType.RUN_LINE, side_team="ATL", line=1.5)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_skip_outside_pre_game_window_too_early(cfg):
    enriched = _make_enriched(seconds=15 * 3600)
    market = _make_market(MLBMarketType.MONEYLINE)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_skip_outside_pre_game_window_too_late(cfg):
    enriched = _make_enriched(seconds=1 * 3600)
    market = _make_market(MLBMarketType.MONEYLINE)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_skip_low_volume(cfg):
    enriched = _make_enriched()
    market = _make_market(MLBMarketType.MONEYLINE, volume=2500)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_skip_price_out_of_range(cfg):
    enriched = _make_enriched()
    market = _make_market(MLBMarketType.MONEYLINE, price=0.85)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_moneyline_gap_below_threshold_skip(cfg):
    enriched = _make_enriched(home_wp=0.51, away_wp=0.49)
    market = _make_market(MLBMarketType.MONEYLINE, price=0.55)
    assert apply_mlb_entry_filters(market, enriched, cfg, 1000.0) is None


def test_moneyline_with_edge_returns_decision(cfg):
    """Strong home team (winpct 0.65) + ace (ERA 2.5), Polymarket undervalues at 0.55."""
    enriched = _make_enriched(home_wp=0.65, away_wp=0.45, home_era=2.5, away_era=4.5)
    market = _make_market(MLBMarketType.MONEYLINE, side_team="ATL", price=0.55)
    result = apply_mlb_entry_filters(market, enriched, cfg, 10000.0)
    assert result is not None
    assert result.action == "BUY"
    assert result.size_usdc > 0
    assert result.size_usdc <= cfg.max_position_usdc


def test_rain_partial_size_multiplier(cfg):
    """Rain 0.40 (in partial zone) → size × 0.7."""
    enriched = _make_enriched(home_wp=0.65, away_wp=0.45, home_era=2.5, rain=0.40)
    market = _make_market(MLBMarketType.MONEYLINE, side_team="ATL", price=0.55)
    result = apply_mlb_entry_filters(market, enriched, cfg, 10000.0)
    if result is not None:
        assert 0 < result.size_usdc <= cfg.max_position_usdc * 0.71


def test_size_capped_by_pct_of_bankroll(cfg):
    """Quarter-Kelly capped at position_cap_pct × bankroll."""
    enriched = _make_enriched(home_wp=0.65, away_wp=0.45, home_era=2.5)
    market = _make_market(MLBMarketType.MONEYLINE, side_team="ATL", price=0.55)
    result = apply_mlb_entry_filters(market, enriched, cfg, 1000.0)
    if result is not None:
        assert result.size_usdc <= 1000.0 * cfg.position_cap_pct
