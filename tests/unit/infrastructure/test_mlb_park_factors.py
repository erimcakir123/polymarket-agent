from src.infrastructure.data.mlb_park_factors import (
    PARK_FACTORS,
    get_park_factor,
    ParkFactor,
)


def test_park_factors_count_30():
    assert len(PARK_FACTORS) == 30


def test_coors_field_extreme_hitter_park():
    pf = get_park_factor("COL")
    assert pf.runs > 1.20


def test_petco_pitcher_park():
    pf = get_park_factor("SD")
    assert pf.runs < 1.0


def test_unknown_team_returns_neutral():
    pf = get_park_factor("XXX")
    assert pf.runs == 1.0
    assert pf.hr == 1.0
