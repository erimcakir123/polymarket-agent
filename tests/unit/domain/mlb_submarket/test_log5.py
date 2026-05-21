import pytest
from src.domain.mlb_submarket.log5 import log5_multiclass


def _league_rates() -> dict[str, float]:
    return {
        "K": 0.225, "BB": 0.085, "HBP": 0.011, "HR": 0.030,
        "1B": 0.140, "2B": 0.045, "3B": 0.004, "OUT_IN_PLAY": 0.460,
    }


def test_batter_equals_league_returns_pitcher() -> None:
    """When batter_rates == league_rates, output should equal pitcher_rates."""
    league = _league_rates()
    pitcher = dict(league)
    pitcher["K"] = 0.30   # better K pitcher
    pitcher["HR"] = 0.025  # slightly suppresses HR
    # Renormalize pitcher rates to sum to 1
    total = sum(pitcher.values())
    pitcher = {k: v / total for k, v in pitcher.items()}
    out = log5_multiclass(batter_rates=league, pitcher_rates=pitcher, league_rates=league)
    for outcome, val in out.items():
        assert abs(val - pitcher[outcome]) < 1e-9, f"{outcome}: {val} vs {pitcher[outcome]}"


def test_pitcher_equals_league_returns_batter() -> None:
    """When pitcher_rates == league_rates, output should equal batter_rates."""
    league = _league_rates()
    batter = dict(league)
    batter["HR"] = 0.045  # power hitter
    batter["K"] = 0.18    # contact hitter
    total = sum(batter.values())
    batter = {k: v / total for k, v in batter.items()}
    out = log5_multiclass(batter_rates=batter, pitcher_rates=league, league_rates=league)
    for outcome, val in out.items():
        assert abs(val - batter[outcome]) < 1e-9


def test_both_equal_league_returns_league() -> None:
    league = _league_rates()
    out = log5_multiclass(batter_rates=league, pitcher_rates=league, league_rates=league)
    for outcome, val in out.items():
        assert abs(val - league[outcome]) < 1e-9


def test_output_sums_to_one() -> None:
    league = _league_rates()
    batter = dict(league)
    batter["HR"] = 0.06
    pitcher = dict(league)
    pitcher["K"] = 0.30
    out = log5_multiclass(batter_rates=batter, pitcher_rates=pitcher, league_rates=league)
    assert abs(sum(out.values()) - 1.0) < 1e-9


def test_zero_rate_returns_zero() -> None:
    """If batter has 0 rate for an outcome, output has 0 for that outcome."""
    league = _league_rates()
    batter = dict(league)
    batter["HR"] = 0.0  # batter never homers
    # Renormalize batter to sum=1
    total = sum(batter.values())
    batter = {k: v / total for k, v in batter.items()}
    pitcher = dict(league)
    out = log5_multiclass(batter_rates=batter, pitcher_rates=pitcher, league_rates=league)
    assert out["HR"] == 0.0


def test_missing_key_raises() -> None:
    league = _league_rates()
    batter = dict(league)
    del batter["3B"]
    with pytest.raises(ValueError):
        log5_multiclass(batter_rates=batter, pitcher_rates=league, league_rates=league)


def test_league_zero_rate_avoids_division_error() -> None:
    """If a league rate is 0, the corresponding output is 0 (skip outcome safely)."""
    league = _league_rates()
    league["3B"] = 0.0
    # Renormalize league
    total = sum(league.values())
    league = {k: v / total for k, v in league.items()}
    batter = dict(league)
    pitcher = dict(league)
    out = log5_multiclass(batter_rates=batter, pitcher_rates=pitcher, league_rates=league)
    assert out["3B"] == 0.0


def test_unnormalized_input_still_normalizes_output() -> None:
    """Function should normalize even if inputs don't sum to exactly 1."""
    league = _league_rates()
    batter = {k: v * 1.05 for k, v in league.items()}  # 5% over-scaled
    pitcher = dict(league)
    out = log5_multiclass(batter_rates=batter, pitcher_rates=pitcher, league_rates=league)
    assert abs(sum(out.values()) - 1.0) < 1e-9
