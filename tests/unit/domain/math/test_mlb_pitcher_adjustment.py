import pytest
from src.domain.math.mlb_pitcher_adjustment import (
    LEAGUE_AVG_ERA,
    PITCHER_WEIGHT,
    pitcher_adjusted_winpct,
    matchup_winpct,
)


def test_neutral_era_no_adjustment():
    """Pitcher ERA == league avg → winpct unchanged."""
    base = 0.500
    assert pitcher_adjusted_winpct(base, LEAGUE_AVG_ERA) == pytest.approx(base, abs=0.001)


def test_ace_pitcher_boosts_winpct():
    """ERA 2.50 (way better than 4.20) → winpct rises."""
    base = 0.500
    adjusted = pitcher_adjusted_winpct(base, 2.50)
    assert adjusted > base


def test_bad_pitcher_drops_winpct():
    """ERA 6.00 → winpct drops."""
    base = 0.500
    adjusted = pitcher_adjusted_winpct(base, 6.00)
    assert adjusted < base


def test_winpct_clamped_to_safe_range():
    """Adjustment can't push winpct outside [0.05, 0.95]."""
    assert 0.05 <= pitcher_adjusted_winpct(0.99, 0.5) <= 0.95
    assert 0.05 <= pitcher_adjusted_winpct(0.01, 9.99) <= 0.95


def test_matchup_winpct_uses_log5():
    """Combined matchup with two ERA=4.20 pitchers and equal team winpcts → ~0.5."""
    p = matchup_winpct(0.500, 0.500, LEAGUE_AVG_ERA, LEAGUE_AVG_ERA)
    assert p == pytest.approx(0.5, abs=0.001)
