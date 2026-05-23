"""Tests for MlbSubmarketEngine — real orchestrator (SPEC-R Plan 4 T2).

10 test cases covering: happy path, lineup empty, StatsApiError, cache hit,
cache miss→statcast called, edge below threshold, slug parse failure,
tier A vs tier B, market_type dispatch (totals vs run_line), WeatherError.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import MlbSubmarketConfig
from src.infrastructure.mlb_data.statcast_client import StatcastError
from src.infrastructure.mlb_data.statsapi_client import StatsApiError
from src.infrastructure.mlb_data.weather_client import WeatherError
from src.models.enums import Direction
from src.models.market import MarketData
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_FAKE_RATES: dict[str, float] = {
    "K": 0.22, "BB": 0.08, "HBP": 0.01, "HR": 0.03,
    "1B": 0.14, "2B": 0.04, "3B": 0.004, "OUT_IN_PLAY": 0.456,
}

_FAKE_WEATHER: dict[str, float] = {
    "wind_mph": 5.0,
    "wind_dir_deg": 90.0,
    "temp_f": 72.0,
    "humidity_pct": 50.0,
}

_BALLPARK_META: dict[str, dict[str, Any]] = {
    "pnc": {"park_id": "pnc", "lat": 40.44, "lon": -80.00, "cf_orientation_deg": 0.0},
}

_NINE_BATTERS = list(range(1, 10))  # 9 distinct mlbam_ids


def _make_config(min_edge: float = 0.05) -> MlbSubmarketConfig:
    return MlbSubmarketConfig(enabled=True, min_edge=min_edge)


def _make_statsapi(*, schedule_ok: bool = True, lineup_ok: bool = True,
                   pitchers_ok: bool = True) -> MagicMock:
    m = MagicMock()
    if schedule_ok:
        # Default slug: mlb-pit-chc-2026-05-21 → away=pit(134), home=chc(112)
        m.get_schedule.return_value = [
            {"gamePk": 111, "home_team_id": 112, "away_team_id": 134}
        ]
    else:
        m.get_schedule.side_effect = StatsApiError("schedule fail")
    if lineup_ok:
        m.get_lineup.return_value = {"home": _NINE_BATTERS, "away": _NINE_BATTERS}
    else:
        m.get_lineup.return_value = {"home": [], "away": []}
    if pitchers_ok:
        m.get_probable_pitchers.return_value = {
            111: {"home_pitcher_id": 100, "away_pitcher_id": 200},
        }
    return m


def _make_statcast(rates: dict[str, float] | None = None) -> MagicMock:
    m = MagicMock()
    r = rates if rates is not None else _FAKE_RATES
    m.get_batter_rates.return_value = r
    m.get_pitcher_rates.return_value = r
    return m


def _make_rate_cache(hit: bool = False) -> MagicMock:
    m = MagicMock()
    m.get.return_value = _FAKE_RATES if hit else None
    return m


def _make_weather(ok: bool = True) -> MagicMock:
    m = MagicMock()
    if ok:
        m.get_conditions.return_value = _FAKE_WEATHER
    else:
        m.get_conditions.side_effect = WeatherError("no weather")
    return m


def _engine(
    statsapi: MagicMock | None = None,
    statcast: MagicMock | None = None,
    weather: MagicMock | None = None,
    rate_cache: MagicMock | None = None,
    config: MlbSubmarketConfig | None = None,
    fixed_bet: dict[str, float] | None = None,
) -> MlbSubmarketEngine:
    # Default slug: mlb-pit-chc → away=pit(134), home=chc(112)
    return MlbSubmarketEngine(
        statsapi=statsapi or _make_statsapi(),
        statcast=statcast or _make_statcast(),
        weather=weather or _make_weather(),
        rate_cache=rate_cache or _make_rate_cache(hit=False),
        config=config or _make_config(),
        ballpark_metadata=_BALLPARK_META,
        team_id_to_park_id={112: "pnc"},
        fixed_bet_usdc=fixed_bet or {"A": 15.0, "B": 10.0},  # 2026-05-23 bimodal (SPEC-S Faz D)
    )


def _market(slug: str = "mlb-pit-chc-2026-05-21-total-8pt5",
            yes_price: float = 0.50) -> MagicMock:
    m = MagicMock(spec=["condition_id", "event_id", "slug", "yes_price"])
    m.condition_id = "cid-001"
    m.event_id = "evt-001"
    m.slug = slug
    m.yes_price = yes_price
    return m


# ---------------------------------------------------------------------------
# Test 1: Successful process returns Signal with correct direction
# ---------------------------------------------------------------------------

def test_process_successful_returns_signal_with_direction() -> None:
    """Happy path: model_p > market_p → BUY_YES signal."""
    eng = _engine()
    # model will compute model_p from domain; we patch to control the edge
    # Instead of mocking domain functions, we patch the engine's internal
    # pricer to return a known model_p above market_p.
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        sig = eng.process(_market(yes_price=0.50))
    assert sig is not None
    assert sig.direction == Direction.BUY_YES


# ---------------------------------------------------------------------------
# Test 2: Lineup empty → None
# ---------------------------------------------------------------------------

def test_process_lineup_empty_returns_none() -> None:
    """When lineup not yet posted, engine returns None."""
    eng = _engine(statsapi=_make_statsapi(lineup_ok=False))
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        result = eng.process(_market())
    assert result is None


# ---------------------------------------------------------------------------
# Test 3: StatsApiError on schedule → None (no crash)
# ---------------------------------------------------------------------------

def test_process_statsapi_schedule_error_returns_none() -> None:
    """StatsApiError on schedule fetch → logged, returns None."""
    eng = _engine(statsapi=_make_statsapi(schedule_ok=False))
    result = eng.process(_market())
    assert result is None


# ---------------------------------------------------------------------------
# Test 4: Rate cache hit → statcast NOT called
# ---------------------------------------------------------------------------

def test_process_rate_cache_hit_skips_statcast() -> None:
    """When cache has rates, statcast.get_batter_rates must not be called."""
    cache = _make_rate_cache(hit=True)
    statcast = _make_statcast()
    eng = _engine(rate_cache=cache, statcast=statcast)
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        eng.process(_market())
    statcast.get_batter_rates.assert_not_called()
    statcast.get_pitcher_rates.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: Rate cache miss → statcast called + result cached
# ---------------------------------------------------------------------------

def test_process_rate_cache_miss_calls_statcast_and_caches() -> None:
    """On cache miss, statcast is fetched and rate_cache.put is called."""
    cache = _make_rate_cache(hit=False)
    statcast = _make_statcast()
    eng = _engine(rate_cache=cache, statcast=statcast)
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        eng.process(_market())
    assert statcast.get_batter_rates.called or statcast.get_pitcher_rates.called
    assert cache.put.called


# ---------------------------------------------------------------------------
# Test 6: Edge below threshold → None
# ---------------------------------------------------------------------------

def test_process_edge_below_threshold_returns_none() -> None:
    """Edge too small (< min_edge) → None."""
    eng = _engine(config=_make_config(min_edge=0.10))
    # model_p = 0.53, market_p = 0.50 → edge = 0.03 < 0.10
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.53, 0.47),
    ):
        result = eng.process(_market(yes_price=0.50))
    assert result is None


# ---------------------------------------------------------------------------
# Test 7: Slug parse failure → None
# ---------------------------------------------------------------------------

def test_process_invalid_slug_returns_none() -> None:
    """Unparseable slug → None immediately (no API calls)."""
    statsapi = _make_statsapi()
    eng = _engine(statsapi=statsapi)
    result = eng.process(_market(slug="not-an-mlb-slug"))
    assert result is None
    statsapi.get_schedule.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8a: Edge >= 0.07 → tier A
# ---------------------------------------------------------------------------

def test_process_large_edge_returns_tier_a() -> None:
    """Edge >= 0.07 → confidence tier A, size = 15.0."""
    eng = _engine(fixed_bet={"A": 15.0, "B": 10.0})
    # edge = 0.58 - 0.50 = 0.08 >= 0.07 → A
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        sig = eng.process(_market(yes_price=0.50))
    assert sig is not None
    assert sig.confidence == "A"
    assert sig.size_usdc == 15.0


# ---------------------------------------------------------------------------
# Test 8b: Edge between min_edge and 0.07 → tier B
# ---------------------------------------------------------------------------

def test_process_medium_edge_returns_tier_b() -> None:
    """Edge in [min_edge, 0.07) → confidence tier B, size = 10.0."""
    eng = _engine(config=_make_config(min_edge=0.05), fixed_bet={"A": 15.0, "B": 10.0})
    # edge = 0.56 - 0.50 = 0.06 → [0.05, 0.07) → B
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.56, 0.44),
    ):
        sig = eng.process(_market(yes_price=0.50))
    assert sig is not None
    assert sig.confidence == "B"
    assert sig.size_usdc == 10.0


# ---------------------------------------------------------------------------
# Test 9a: market_type totals → totals_pricer used
# ---------------------------------------------------------------------------

def test_process_totals_market_uses_totals_pricer() -> None:
    """Totals slug dispatches to totals_probability."""
    eng = _engine()
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ) as mock_totals, patch(
        "src.strategy.entry.mlb_submarket_engine.spread_probability",
    ) as mock_spread:
        eng.process(_market(slug="mlb-pit-chc-2026-05-21-total-8pt5"))
    mock_totals.assert_called_once()
    mock_spread.assert_not_called()


# ---------------------------------------------------------------------------
# Test 9b: market_type run_line → spread_pricer used
# ---------------------------------------------------------------------------

def test_process_run_line_market_uses_spread_pricer() -> None:
    """Run-line slug dispatches to spread_probability."""
    eng = _engine()
    with patch(
        "src.strategy.entry.mlb_submarket_engine.spread_probability",
        return_value=(0.58, 0.42),
    ) as mock_spread, patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
    ) as mock_totals:
        eng.process(_market(slug="mlb-pit-chc-2026-05-21-spread-pos1pt5"))
    mock_spread.assert_called_once()
    mock_totals.assert_not_called()


# ---------------------------------------------------------------------------
# Test 10: WeatherError → None (log + skip)
# ---------------------------------------------------------------------------

def test_process_weather_error_returns_none() -> None:
    """WeatherError from weather client → logged, returns None."""
    eng = _engine(weather=_make_weather(ok=False))
    result = eng.process(_market())
    assert result is None


# ---------------------------------------------------------------------------
# Test 11: Engine fetches handedness for every player (2 pitchers + 18 batters)
# ---------------------------------------------------------------------------

def test_process_calls_handedness_lookup() -> None:
    """Engine fetches handedness for every player: 2 pitchers + 18 batters = 20 calls."""
    statsapi = _make_statsapi()
    statsapi.get_player_handedness.return_value = {"bat_side": "R", "pitch_hand": "R"}
    eng = _engine(statsapi=statsapi)
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        eng.process(_market())
    assert statsapi.get_player_handedness.call_count == 20


# ---------------------------------------------------------------------------
# Test 12: Engine passes real batter_hand from Stats API into PA context
# ---------------------------------------------------------------------------

def test_process_uses_left_handed_batter_in_context() -> None:
    """If statsapi returns 'L' for a batter, engine passes 'L' to compute_pa_outcome."""
    statsapi = _make_statsapi()
    # All batters return 'L' bat_side; pitchers return 'R' pitch_hand
    def _handedness(person_id: int) -> dict[str, str]:
        # pitchers have ids 100, 200 → pitch_hand used; batters 1-9 → bat_side used
        if person_id in (100, 200):
            return {"bat_side": "R", "pitch_hand": "R"}
        return {"bat_side": "L", "pitch_hand": "R"}
    statsapi.get_player_handedness.side_effect = _handedness

    captured_contexts: list[dict] = []

    def _fake_pa_outcome(
        batter_rates: dict,
        pitcher_rates: dict,
        league_rates: dict,
        context: dict,
    ) -> dict:
        captured_contexts.append(dict(context))
        return {"run": 0.05, "out": 0.95}

    eng = _engine(statsapi=statsapi)
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ), patch(
        "src.strategy.entry.mlb_submarket_engine.compute_pa_outcome",
        side_effect=_fake_pa_outcome,
    ), patch(
        "src.strategy.entry.mlb_submarket_engine.simulate_game",
        return_value=({5: 1.0}, {4: 1.0}),
    ):
        eng.process(_market())

    # Every captured context should have batter_hand == 'L' (batters 1-9 returned L)
    assert len(captured_contexts) > 0
    for ctx in captured_contexts:
        assert ctx["batter_hand"] == "L", f"Expected 'L', got {ctx['batter_hand']!r}"


# ---------------------------------------------------------------------------
# Test 13: StatsApiError on handedness fetch → process returns None
# ---------------------------------------------------------------------------

def test_process_handedness_fetch_failure_returns_none() -> None:
    """If StatsApiError raised during handedness lookup, process returns None."""
    statsapi = _make_statsapi()
    statsapi.get_player_handedness.side_effect = StatsApiError("no handedness data")
    eng = _engine(statsapi=statsapi)
    with patch(
        "src.strategy.entry.mlb_submarket_engine.totals_probability",
        return_value=(0.58, 0.42),
    ):
        result = eng.process(_market())
    assert result is None
