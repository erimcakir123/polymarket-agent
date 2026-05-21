from src.domain.mlb_submarket.park_factor_adjust import PARK_FACTORS, park_multiplier


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


# --- Tests for newly added parks (5→30 expansion) ---

def test_comerica_hr_suppression() -> None:
    # Comerica Park has deep outfield — HR below league average
    assert park_multiplier("COMERICA", "HR") == 0.95
    assert park_multiplier("COMERICA", "HR") < 1.0


def test_great_american_hr_boost() -> None:
    # Great American Ball Park is one of the most hitter-friendly HR parks
    assert park_multiplier("GREAT_AMERICAN", "HR") == 1.12
    assert park_multiplier("GREAT_AMERICAN", "HR") > 1.0


def test_oracle_hr_suppression_and_triples_boost() -> None:
    # Oracle Park — marine layer heavily suppresses HR, but large OF allows triples
    assert park_multiplier("ORACLE", "HR") == 0.88
    assert park_multiplier("ORACLE", "3B") == 1.10
    assert park_multiplier("ORACLE", "HR") < park_multiplier("ORACLE", "3B")


def test_all_30_parks_present() -> None:
    expected_parks = {
        "COORS", "FENWAY", "YANKEE", "DODGER", "PETCO",
        "WRIGLEY", "BUSCH", "GLOBE_LIFE", "GREAT_AMERICAN", "CITIZENS_BANK",
        "AMERICAN_FAMILY", "TARGET", "KAUFFMAN", "PROGRESSIVE", "GUARANTEED_RATE",
        "ROGERS", "ORACLE", "CHASE", "T_MOBILE", "ANGEL",
        "MINUTE_MAID", "TROPICANA", "LOAN_DEPOT", "TRUIST", "ORIOLE_PARK",
        "NATIONALS", "CITI", "PNC", "COMERICA", "OAKLAND_COLISEUM",
    }
    assert set(PARK_FACTORS.keys()) == expected_parks
