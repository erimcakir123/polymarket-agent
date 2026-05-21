"""Tests for pa_outcome Layer 1 dispatcher.

SPEC-R Plan 2 T9.
"""
import pytest
from src.domain.mlb_submarket.league_constants import LEAGUE_PA_RATES
from src.domain.mlb_submarket.pa_outcome import PAContext, compute_pa_outcome


def _equal_rates() -> dict[str, float]:
    return dict(LEAGUE_PA_RATES)


def _neutral_context() -> PAContext:
    return {
        "park_id": "UNKNOWN_NEUTRAL",
        "batter_hand": "R",
        "pitcher_hand": "R",
        "times_through": 1,
        "wind_mph_to_cf": 0.0,
        "temp_f": 60.0,
        "humidity_pct": 50.0,
    }


def test_all_neutral_returns_league() -> None:
    """Batter = pitcher = league, neutral context → output ≈ league."""
    out = compute_pa_outcome(
        batter_rates=_equal_rates(),
        pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(),
        context=_neutral_context(),
    )
    for outcome, val in out.items():
        assert abs(val - LEAGUE_PA_RATES[outcome]) < 1e-6


def test_output_sums_to_one() -> None:
    out = compute_pa_outcome(
        batter_rates=_equal_rates(),
        pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(),
        context=_neutral_context(),
    )
    assert abs(sum(out.values()) - 1.0) < 1e-9


def test_coors_increases_hr() -> None:
    ctx: PAContext = {**_neutral_context(), "park_id": "COORS"}
    out_neutral = compute_pa_outcome(
        batter_rates=_equal_rates(), pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(), context=_neutral_context(),
    )
    out_coors = compute_pa_outcome(
        batter_rates=_equal_rates(), pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(), context=ctx,
    )
    assert out_coors["HR"] > out_neutral["HR"]


def test_strong_wind_increases_hr() -> None:
    ctx: PAContext = {**_neutral_context(), "wind_mph_to_cf": 15.0, "temp_f": 80.0}
    out = compute_pa_outcome(
        batter_rates=_equal_rates(), pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(), context=ctx,
    )
    assert out["HR"] > LEAGUE_PA_RATES["HR"]


def test_high_tto_increases_hr_decreases_k() -> None:
    ctx: PAContext = {**_neutral_context(), "times_through": 3}
    out = compute_pa_outcome(
        batter_rates=_equal_rates(), pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(), context=ctx,
    )
    assert out["HR"] > LEAGUE_PA_RATES["HR"]
    assert out["K"] < LEAGUE_PA_RATES["K"]


def test_left_batter_vs_right_pitcher_platoon() -> None:
    ctx: PAContext = {**_neutral_context(), "batter_hand": "L", "pitcher_hand": "R"}
    out = compute_pa_outcome(
        batter_rates=_equal_rates(), pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(), context=ctx,
    )
    # LvR favors batter — HR should be slightly elevated
    assert out["HR"] > LEAGUE_PA_RATES["HR"]


def test_power_batter_more_hr() -> None:
    batter = _equal_rates()
    batter["HR"] = 0.06  # power hitter
    # Renormalize
    total = sum(batter.values())
    batter = {k: v / total for k, v in batter.items()}
    out = compute_pa_outcome(
        batter_rates=batter, pitcher_rates=_equal_rates(),
        league_rates=_equal_rates(), context=_neutral_context(),
    )
    assert out["HR"] > LEAGUE_PA_RATES["HR"]


def test_park_factor_applied_to_matchup_not_batter() -> None:
    """Sanity: Coors HR boost should multiply the FINAL matchup HR rate,
    not get applied to batter rates (which would then compound with pitcher
    via Log5 — double count).

    Verifiable: with both rates = league, the HR rate after Coors should be
    (matchup_HR * park_HR_factor) / normalizer ≈ league_HR * 1.18 / norm.
    We don't compute the exact value here — just assert it's monotonic
    with the park factor magnitude.
    """
    league = _equal_rates()
    ctx_neutral: PAContext = {**_neutral_context(), "park_id": "DODGER"}  # near-neutral
    ctx_coors: PAContext = {**_neutral_context(), "park_id": "COORS"}
    out_dodger = compute_pa_outcome(
        batter_rates=league, pitcher_rates=league, league_rates=league, context=ctx_neutral
    )
    out_coors = compute_pa_outcome(
        batter_rates=league, pitcher_rates=league, league_rates=league, context=ctx_coors
    )
    # Coors HR factor 1.18 vs Dodger ~0.98 → Coors HR clearly larger
    assert out_coors["HR"] > out_dodger["HR"] * 1.15
