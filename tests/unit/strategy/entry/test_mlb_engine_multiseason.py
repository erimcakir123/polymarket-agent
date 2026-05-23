from unittest.mock import MagicMock
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine
from src.config.settings import MlbSubmarketConfig


def _stub_engine(statcast):
    return MlbSubmarketEngine(
        statsapi=MagicMock(), statcast=statcast, weather=MagicMock(),
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
        team_id_to_park_id={143: "FAKE"},
    )


def test_engine_fetches_three_seasons_per_batter():
    statcast = MagicMock()
    statcast.get_batter_rates.return_value = {"hr_rate": 0.04, "pa": 600}
    engine = _stub_engine(statcast)
    engine._get_batter_rates(1, 2026)
    assert statcast.get_batter_rates.call_count == 3
    calls = [c.args[1] for c in statcast.get_batter_rates.call_args_list]
    assert sorted(calls) == [2024, 2025, 2026]


def test_engine_fetches_three_seasons_per_pitcher():
    statcast = MagicMock()
    statcast.get_pitcher_rates.return_value = {"hr_rate": 0.04, "pa": 600}
    engine = _stub_engine(statcast)
    engine._get_pitcher_rates(1, 2026)
    assert statcast.get_pitcher_rates.call_count == 3
