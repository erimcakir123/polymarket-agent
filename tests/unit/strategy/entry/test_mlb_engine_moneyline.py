"""Tests for engine process() moneyline branch.

Verifies that moneyline slugs route through moneyline_probability (not
spread_probability with line=0.0) and produce correct signal direction/edge.
"""
from unittest.mock import MagicMock, patch

from src.config.settings import MlbSubmarketConfig
from src.models.enums import Direction, EntryReason
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine

_FULL_RATES = {
    "K": 0.22, "BB": 0.08, "HBP": 0.01, "HR": 0.03,
    "1B": 0.14, "2B": 0.04, "3B": 0.004, "OUT_IN_PLAY": 0.456,
}


def _make_market(slug: str, yes_price: float) -> MagicMock:
    m = MagicMock(spec=["condition_id", "event_id", "slug", "yes_price"])
    m.condition_id = "c1"
    m.event_id = "e1"
    m.slug = slug
    m.yes_price = yes_price
    return m


def _stub_engine() -> MlbSubmarketEngine:
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = [{
        "gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled",
        "game_type": "R", "scheduled_innings": 9, "double_header": "N",
    }]
    statsapi.get_lineup.return_value = {"home": [1] * 9, "away": [2] * 9}
    statsapi.get_probable_pitchers.return_value = {
        222: {"home_pitcher_id": 50, "away_pitcher_id": 60}
    }
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}

    statcast = MagicMock()
    statcast.get_batter_rates.return_value = _FULL_RATES
    statcast.get_pitcher_rates.return_value = _FULL_RATES

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
            }
        },
        team_id_to_park_id={143: "CITIZENS_BANK", 114: "CITIZENS_BANK"},
    )


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_moneyline_high_edge_returns_buy_yes_signal(mock_sim):
    # Home wins ~80% (4 vs 2); market 60c → edge = 0.20 ≥ 0.07 (tier A)
    mock_sim.return_value = ({4: 0.8, 1: 0.2}, {2: 1.0})
    engine = _stub_engine()
    market = _make_market(slug="mlb-cle-phi-2026-05-22", yes_price=0.60)
    signal = engine.process(market)
    assert signal is not None
    assert signal.direction == Direction.BUY_YES
    assert signal.entry_reason == EntryReason.MLB_SUBMARKET
    assert signal.edge >= 0.07  # tier A


@patch("src.strategy.entry.mlb_submarket_engine.moneyline_probability")
@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_moneyline_low_edge_returns_none(mock_sim, mock_ml):
    # Pricer returns 52% for home; market 50% → edge 0.02 < min_edge 0.05
    mock_sim.return_value = ({3: 1.0}, {3: 1.0})  # ignored: pricer is patched
    mock_ml.return_value = (0.52, 0.48)
    engine = _stub_engine()
    market = _make_market(slug="mlb-cle-phi-2026-05-22", yes_price=0.50)
    signal = engine.process(market)
    assert signal is None


@patch("src.strategy.entry.mlb_submarket_engine.simulate_game")
def test_moneyline_negative_edge_returns_buy_no(mock_sim):
    # Away dominant: home scores 2 (98%) or 5 (2%), away always scores 4
    # P(home wins) ≈ 0.02 (only when home=5 > away=4); edge = 0.02 - 0.65 = -0.63
    mock_sim.return_value = ({2: 0.98, 5: 0.02}, {4: 1.0})
    engine = _stub_engine()
    market = _make_market(slug="mlb-cle-phi-2026-05-22", yes_price=0.65)
    signal = engine.process(market)
    assert signal is not None
    assert signal.direction == Direction.BUY_NO
