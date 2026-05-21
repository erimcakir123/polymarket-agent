from src.config.sport_rules import anchor_source


def test_mlb_moneyline_uses_bookmaker() -> None:
    assert anchor_source("baseball_mlb", "moneyline") == "bookmaker"


def test_mlb_totals_uses_model() -> None:
    assert anchor_source("baseball_mlb", "totals") == "model"


def test_mlb_run_line_uses_model() -> None:
    assert anchor_source("baseball_mlb", "run_line") == "model"


def test_nba_totals_uses_bookmaker_default() -> None:
    assert anchor_source("basketball_nba", "totals") == "bookmaker"


def test_unknown_sport_defaults_to_bookmaker() -> None:
    assert anchor_source("foosball_xyz", "moneyline") == "bookmaker"


def test_alias_normalization() -> None:
    assert anchor_source("mlb", "totals") == anchor_source("baseball_npb", "totals")
