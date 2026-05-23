"""Tests for MlbSubmarketEngine DH detection logic (A6).

Verifies that process() passes dh_game=True to simulate_game when the
schedule game has gameType='D' AND scheduledInnings < 9, and dh_game=False
otherwise.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.config.settings import MlbSubmarketConfig
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def _make_market(slug: str, yes_price: float = 0.5) -> MagicMock:
    m = MagicMock(spec=["condition_id", "event_id", "slug", "yes_price"])
    m.condition_id = "cid-dh-test"
    m.event_id = "evt-dh-test"
    m.slug = slug
    m.yes_price = yes_price
    return m


def _stub_engine_full(schedule_game: dict) -> MlbSubmarketEngine:
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [schedule_game]
    statsapi.get_lineup.return_value = {"home": [1] * 9, "away": [2] * 9}
    statsapi.get_probable_pitchers.return_value = {
        schedule_game["gamePk"]: {"home_pitcher_id": 50, "away_pitcher_id": 60}
    }
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04}

    weather = MagicMock()
    weather.get_conditions.return_value = {
        "wind_dir_deg": 0, "wind_mph": 0, "temp_f": 70, "humidity_pct": 50,
    }

    return MlbSubmarketEngine(
        statsapi=statsapi,
        statcast=statcast,
        weather=weather,
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={
            "CITIZENS_BANK": {
                "lat": 39.9, "lon": -75.1,
                "cf_orientation_deg": 0.0,
                "park_id": "CITIZENS_BANK",
            },
        },
        team_id_to_park_id={143: "CITIZENS_BANK", 114: "CITIZENS_BANK"},
    )


@patch("src.strategy.entry.mlb_submarket_engine.totals_probability", return_value=(0.58, 0.42))
@patch("src.strategy.entry.mlb_submarket_engine.compute_pa_outcome", return_value={"run": 0.05, "out": 0.95})
@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_dh_7_inning_sets_dh_game_true(mock_sim, _mock_pa, _mock_totals):
    mock_sim.return_value = ({0: 1.0}, {0: 1.0})
    game = {
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "D", "scheduled_innings": 7, "double_header": "S",
    }
    engine = _stub_engine_full(game)
    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    engine.process(market)
    _, kwargs = mock_sim.call_args
    assert kwargs.get("dh_game") is True


@patch("src.strategy.entry.mlb_submarket_engine.totals_probability", return_value=(0.58, 0.42))
@patch("src.strategy.entry.mlb_submarket_engine.compute_pa_outcome", return_value={"run": 0.05, "out": 0.95})
@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_regular_9_inning_sets_dh_game_false(mock_sim, _mock_pa, _mock_totals):
    mock_sim.return_value = ({0: 1.0}, {0: 1.0})
    game = {
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "R", "scheduled_innings": 9, "double_header": "N",
    }
    engine = _stub_engine_full(game)
    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    engine.process(market)
    _, kwargs = mock_sim.call_args
    assert kwargs.get("dh_game") is False


@patch("src.strategy.entry.mlb_submarket_engine.totals_probability", return_value=(0.58, 0.42))
@patch("src.strategy.entry.mlb_submarket_engine.compute_pa_outcome", return_value={"run": 0.05, "out": 0.95})
@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_dh_game1_9_inning_sets_dh_game_false(mock_sim, _mock_pa, _mock_totals):
    """DH'in 1'inci maçı normalde 9 inning → dh_game=False."""
    mock_sim.return_value = ({0: 1.0}, {0: 1.0})
    game = {
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "R", "scheduled_innings": 9, "double_header": "S",  # split DH ama game 1
    }
    engine = _stub_engine_full(game)
    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    engine.process(market)
    _, kwargs = mock_sim.call_args
    assert kwargs.get("dh_game") is False
