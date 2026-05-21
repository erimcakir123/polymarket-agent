from src.domain.mlb_submarket.park_factor_adjust import park_multiplier


def test_coors_hr_boost() -> None:
    assert park_multiplier("COORS", "HR") > 1.0
    assert park_multiplier("COORS", "HR") == 1.18


def test_petco_hr_suppression() -> None:
    assert park_multiplier("PETCO", "HR") < 1.0


def test_unknown_park_returns_one() -> None:
    assert park_multiplier("UNKNOWN_PARK", "HR") == 1.0


def test_unknown_outcome_returns_one() -> None:
    assert park_multiplier("COORS", "UNKNOWN_OUTCOME") == 1.0


def test_neutral_park_returns_one() -> None:
    # Most parks should be near-neutral; verify lookup mechanism
    assert park_multiplier("YANKEE", "K") == 1.0  # K is rarely park-adjusted
