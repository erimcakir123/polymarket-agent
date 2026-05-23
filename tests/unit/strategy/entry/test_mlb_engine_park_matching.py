"""Tests for MlbSubmarketEngine home-team-bound park lookup (A5).

Verifies that process() selects the ballpark for the home team
via team_id_to_park_id mapping, not the first ballpark in metadata.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.config.settings import MlbSubmarketConfig
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def _make_market(slug: str, yes_price: float = 0.5) -> MagicMock:
    m = MagicMock(spec=["condition_id", "event_id", "slug", "yes_price"])
    m.condition_id = "cid-park-test"
    m.event_id = "evt-park-test"
    m.slug = slug
    m.yes_price = yes_price
    return m


@patch("src.strategy.entry.mlb_submarket_engine.totals_probability", return_value=(0.58, 0.42))
@patch("src.strategy.entry.mlb_submarket_engine.compute_pa_outcome", return_value={"run": 0.05, "out": 0.95})
@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_engine_uses_home_team_park_meta(mock_sim, _mock_pa, _mock_totals):
    mock_sim.return_value = ({0: 1.0}, {0: 1.0})

    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [
        {"gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled"},
    ]
    statsapi.get_lineup.return_value = {"home": [1]*9, "away": [2]*9}
    statsapi.get_probable_pitchers.return_value = {
        222: {"home_pitcher_id": 50, "away_pitcher_id": 60}
    }
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04}

    rate_cache = MagicMock()
    rate_cache.get.return_value = None
    weather = MagicMock()
    weather.get_conditions.return_value = {
        "wind_dir_deg": 0, "wind_mph": 0, "temp_f": 70, "humidity_pct": 50,
    }

    ballpark_metadata = {
        "CITIZENS_BANK": {"lat": 39.9, "lon": -75.1, "cf_orientation_deg": 0.0, "park_id": "CITIZENS_BANK"},
        "PROGRESSIVE":   {"lat": 41.4, "lon": -81.6, "cf_orientation_deg": 0.0, "park_id": "PROGRESSIVE"},
    }
    team_id_to_park_id = {143: "CITIZENS_BANK", 114: "PROGRESSIVE"}

    engine = MlbSubmarketEngine(
        statsapi=statsapi, statcast=statcast, weather=weather,
        rate_cache=rate_cache,
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata=ballpark_metadata,
        team_id_to_park_id=team_id_to_park_id,
    )

    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    engine.process(market)

    args = weather.get_conditions.call_args[0]
    # PHI home (143) → CITIZENS_BANK park; lat/lon must match
    assert args[0] == 39.9 and args[1] == -75.1


def test_engine_returns_none_when_home_team_has_no_park_mapping():
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [
        {"gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled"},
    ]
    statsapi.get_lineup.return_value = {"home": [1]*9, "away": [2]*9}
    statsapi.get_probable_pitchers.return_value = {
        222: {"home_pitcher_id": 50, "away_pitcher_id": 60}
    }
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04}
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04}

    engine = MlbSubmarketEngine(
        statsapi=statsapi, statcast=statcast, weather=MagicMock(),
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
        team_id_to_park_id={},  # boş — eşleme yok
    )

    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    result = engine.process(market)
    assert result is None
