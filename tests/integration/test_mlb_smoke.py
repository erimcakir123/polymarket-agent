# tests/integration/test_mlb_smoke.py
"""MLB end-to-end smoke tests (dormant Sprint 1 — modules wire correctly without trading)."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from src.strategy.entry._mlb_edge import (
    MLBEntryConfig, apply_mlb_entry_filters,
)
from src.strategy.exit.mlb_score_exit import (
    MLBExitConfig, decide_mlb_score_exit, ExitAction,
)
from src.domain.sports.mlb_question_parser import (
    MLBMarketIntent, MLBMarketType, parse_mlb_question,
)
from src.orchestration.mlb_edge_enricher import MLBEnrichedData
from src.infrastructure.data.mlb_park_factors import ParkFactor


@pytest.fixture
def cfg_entry():
    return MLBEntryConfig(
        rain_skip_threshold=0.60, rain_partial_threshold=0.30,
        pre_game_window_min_hours=2.0, pre_game_window_max_hours=12.0,
        min_volume_usdc=3000.0, min_liquidity_usdc=3000.0,
        min_polymarket_price=0.20, max_polymarket_price=0.75,
        gap_threshold=0.05, position_cap_pct=0.03, max_position_usdc=75.0,
        forbid_runline_minus_15_favorite=True,
    )


@pytest.fixture
def cfg_exit():
    return MLBExitConfig(
        near_resolve_threshold=0.95, scale_out_threshold=0.85,
        structural_damage_ratio=0.30, predictive_safety_margin=0.04,
    )


def test_smoke_question_to_intent_to_decision(cfg_entry):
    """Full chain: parse question → intent → fake enriched → entry decision."""
    intent = parse_mlb_question("Atlanta Braves vs. Detroit Tigers", outcome="Braves")
    assert intent.market_type == MLBMarketType.MONEYLINE

    enriched = MLBEnrichedData(
        pitcher_confirmed_home=True, pitcher_confirmed_away=True,
        home_pitcher_era=2.50, away_pitcher_era=4.50,
        home_season_winpct=0.65, away_season_winpct=0.40,
        home_runs_per_game=5.0, home_runs_allowed_per_game=3.5,
        away_runs_per_game=4.0, away_runs_allowed_per_game=4.5,
        rain_chance=0.10, wind_speed_mph=8.0, wind_direction_deg=180,
        temperature_f=70.0, weather_run_bias=0.0,
        park_factor=ParkFactor(1.0, 1.0), seconds_to_game_start=6 * 3600,
    )

    market = SimpleNamespace(
        question="Atlanta Braves vs. Detroit Tigers",
        outcome="Braves", polymarket_price=0.55,
        volume_24h=5000, liquidity=5000, intent=intent,
    )

    result = apply_mlb_entry_filters(market, enriched, cfg_entry, bankroll=10000)
    assert result is not None
    assert result.action == "BUY"


def test_smoke_m3_exit_late_game_deficit(cfg_exit):
    """In-game state: 9th inning, down by 1 → M3 exit."""
    decision = decide_mlb_score_exit(
        cfg=cfg_exit,
        entry_price=0.6, current_bid=0.10, current_price=0.10,
        scaled_out_50=False,
        inning=9, outs=2, base_state=0,
        run_diff=+1,
        is_home_position=False,
        win_probability_fn=lambda i, v, o: (0.05, "table"),
    )
    assert decision.action == ExitAction.SELL_ALL


def test_smoke_pitcher_unconfirmed_skip(cfg_entry):
    """No probable pitcher → no entry decision."""
    enriched = MLBEnrichedData(
        pitcher_confirmed_home=False, pitcher_confirmed_away=True,
        home_pitcher_era=4.20, away_pitcher_era=4.20,
        home_season_winpct=0.5, away_season_winpct=0.5,
        home_runs_per_game=4.5, home_runs_allowed_per_game=4.5,
        away_runs_per_game=4.5, away_runs_allowed_per_game=4.5,
        rain_chance=0.0, wind_speed_mph=0.0, wind_direction_deg=0,
        temperature_f=70.0, weather_run_bias=0.0,
        park_factor=ParkFactor(1.0, 1.0), seconds_to_game_start=6 * 3600,
    )
    intent = MLBMarketIntent(
        market_type=MLBMarketType.MONEYLINE, team_a="ATL", team_b="DET",
        side_team="ATL", line=None, is_favorite_side=None, totals_side=None,
    )
    market = SimpleNamespace(
        question="", outcome="", polymarket_price=0.55,
        volume_24h=5000, liquidity=5000, intent=intent,
    )
    result = apply_mlb_entry_filters(market, enriched, cfg_entry, 10000)
    assert result is None


def test_smoke_runline_minus_15_favorite_skip(cfg_entry):
    """RL -1.5 favorite forbidden by spec → SKIP."""
    enriched = MLBEnrichedData(
        pitcher_confirmed_home=True, pitcher_confirmed_away=True,
        home_pitcher_era=2.50, away_pitcher_era=4.50,
        home_season_winpct=0.65, away_season_winpct=0.40,
        home_runs_per_game=5.0, home_runs_allowed_per_game=3.5,
        away_runs_per_game=4.0, away_runs_allowed_per_game=4.5,
        rain_chance=0.10, wind_speed_mph=8.0, wind_direction_deg=180,
        temperature_f=70.0, weather_run_bias=0.0,
        park_factor=ParkFactor(1.0, 1.0), seconds_to_game_start=6 * 3600,
    )
    intent = MLBMarketIntent(
        market_type=MLBMarketType.RUN_LINE, team_a="ATL", team_b="DET",
        side_team="ATL", line=1.5, is_favorite_side=True, totals_side=None,
    )
    market = SimpleNamespace(
        question="Will Braves -1.5 cover?", outcome="Yes",
        polymarket_price=0.55, volume_24h=5000, liquidity=5000, intent=intent,
    )
    result = apply_mlb_entry_filters(market, enriched, cfg_entry, 10000)
    assert result is None


def test_smoke_rain_above_threshold_skip(cfg_entry):
    """Rain >= 0.60 → SKIP per spec."""
    enriched = MLBEnrichedData(
        pitcher_confirmed_home=True, pitcher_confirmed_away=True,
        home_pitcher_era=2.50, away_pitcher_era=4.50,
        home_season_winpct=0.65, away_season_winpct=0.40,
        home_runs_per_game=5.0, home_runs_allowed_per_game=3.5,
        away_runs_per_game=4.0, away_runs_allowed_per_game=4.5,
        rain_chance=0.65, wind_speed_mph=8.0, wind_direction_deg=180,
        temperature_f=70.0, weather_run_bias=0.0,
        park_factor=ParkFactor(1.0, 1.0), seconds_to_game_start=6 * 3600,
    )
    intent = MLBMarketIntent(
        market_type=MLBMarketType.MONEYLINE, team_a="ATL", team_b="DET",
        side_team="ATL", line=None, is_favorite_side=None, totals_side=None,
    )
    market = SimpleNamespace(
        question="ATL vs DET", outcome="Braves",
        polymarket_price=0.55, volume_24h=5000, liquidity=5000, intent=intent,
    )
    result = apply_mlb_entry_filters(market, enriched, cfg_entry, 10000)
    assert result is None
