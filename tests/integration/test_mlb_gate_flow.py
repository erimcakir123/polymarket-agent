"""End-to-end MLB market flow through Gate (Sprint 1.5 smoke tests)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.strategy.entry.gate import EntryGate, GateConfig
from src.orchestration.mlb_edge_enricher import MLBEnrichedData
from src.infrastructure.data.mlb_park_factors import ParkFactor


def _enriched_factory(rain: float = 0.10, pitcher_confirmed: bool = True) -> MLBEnrichedData:
    return MLBEnrichedData(
        pitcher_confirmed_home=pitcher_confirmed,
        pitcher_confirmed_away=pitcher_confirmed,
        home_pitcher_era=2.5,
        away_pitcher_era=4.5,
        home_season_winpct=0.65,
        away_season_winpct=0.40,
        home_runs_per_game=5.0,
        home_runs_allowed_per_game=3.5,
        away_runs_per_game=4.0,
        away_runs_allowed_per_game=4.5,
        rain_chance=rain,
        wind_speed_mph=8.0,
        wind_direction_deg=180,
        temperature_f=70.0,
        weather_run_bias=0.0,
        park_factor=ParkFactor(1.0, 1.0),
        seconds_to_game_start=6 * 3600,
    )


def _make_market(
    sport: str = "baseball_mlb",
    question: str = "Atlanta Braves vs. Detroit Tigers",
    outcome: str = "Braves",
    price: float = 0.45,
    volume: float = 5000.0,
) -> SimpleNamespace:
    game_time = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    return SimpleNamespace(
        condition_id="cid_mlb_test",
        sport_tag=sport,
        question=question,
        outcome=outcome,
        polymarket_price=price,
        yes_price=price,
        volume_24h=volume,
        liquidity=volume,
        match_start_iso=game_time,
        game_pk=778899,
        event_id="evt_mlb_test",
        slug="braves-tigers",
        sports_market_type="moneyline",
    )


def _make_gate(enricher: object) -> EntryGate:
    cfg = GateConfig(
        min_favorite_probability=0.55,
        max_entry_price=0.80,
        max_positions=20,
        max_exposure_pct=0.50,
        confidence_bet_pct={"A": 0.05, "B": 0.03},
        max_single_bet_usdc=75.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=15,
        min_sharps=3,
        active_sports=["baseball_mlb"],
    )
    portfolio = MagicMock()
    portfolio.bankroll = 1000.0
    portfolio.total_invested.return_value = 0.0
    portfolio.positions = {}
    return EntryGate(
        config=cfg,
        portfolio=portfolio,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=None,
        manipulation_checker=None,
        mlb_edge_enricher=enricher,
    )


def test_mlb_with_edge_returns_buy():
    """MLB market with sufficient edge → GateResult with Signal (BUY_YES)."""
    enricher = MagicMock()
    enricher.enrich.return_value = _enriched_factory()
    gate = _make_gate(enricher)
    results = gate.run([_make_market()])
    assert len(results) == 1
    r = results[0]
    assert r.signal is not None, f"Expected signal, got skip: {r.skipped_reason}"
    assert r.signal.direction.value == "BUY_YES"


def test_mlb_pitcher_unconfirmed_skip():
    """MLB market with unconfirmed pitcher → SKIP with pitcher-related reason."""
    enricher = MagicMock()
    enricher.enrich.return_value = _enriched_factory(pitcher_confirmed=False)
    gate = _make_gate(enricher)
    results = gate.run([_make_market()])
    assert len(results) == 1
    r = results[0]
    assert r.signal is None
    # apply_mlb_entry_filters returns None for unconfirmed pitcher → MLB_GATE_REJECT
    assert r.skipped_reason is not None
    assert "MLB" in r.skipped_reason


def test_mlb_rain_above_threshold_skip():
    """MLB market with rain >= 0.60 → SKIP."""
    enricher = MagicMock()
    enricher.enrich.return_value = _enriched_factory(rain=0.65)
    gate = _make_gate(enricher)
    results = gate.run([_make_market()])
    assert len(results) == 1
    r = results[0]
    assert r.signal is None
    assert r.skipped_reason is not None


def test_mlb_question_parse_fail_skip():
    """Unparseable question → SKIP with MLB_QUESTION_PARSE_FAIL."""
    enricher = MagicMock()
    gate = _make_gate(enricher)
    market = _make_market(question="Random nonsense text that cannot be parsed")
    results = gate.run([market])
    assert len(results) == 1
    r = results[0]
    assert r.signal is None
    assert r.skipped_reason == "MLB_QUESTION_PARSE_FAIL"


def test_mlb_enricher_none_skip():
    """Gate with no enricher → SKIP with MLB_ENRICHER_UNAVAILABLE."""
    gate = _make_gate(enricher=None)
    results = gate.run([_make_market()])
    assert len(results) == 1
    r = results[0]
    assert r.signal is None
    assert r.skipped_reason == "MLB_ENRICHER_UNAVAILABLE"
