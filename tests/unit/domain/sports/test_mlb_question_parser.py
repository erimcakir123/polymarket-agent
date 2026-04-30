"""MLB question parser tests."""
from src.domain.sports.mlb_question_parser import (
    MLBMarketIntent,
    MLBMarketType,
    parse_mlb_question,
)


def test_parse_moneyline_will_form():
    intent = parse_mlb_question("Will the Braves beat the Tigers?", outcome="Braves")
    assert intent is not None
    assert intent.market_type == MLBMarketType.MONEYLINE
    assert intent.team_a == "ATL"
    assert intent.team_b == "DET"
    assert intent.side_team == "ATL"
    assert intent.line is None


def test_parse_moneyline_vs_form():
    intent = parse_mlb_question("Tigers vs. Braves", outcome="Braves")
    assert intent.market_type == MLBMarketType.MONEYLINE
    assert intent.side_team == "ATL"


def test_parse_moneyline_mlb_prefix():
    intent = parse_mlb_question("MLB: Yankees vs. Red Sox", outcome="Yankees")
    assert intent.market_type == MLBMarketType.MONEYLINE
    assert intent.side_team == "NYY"


def test_parse_run_line_favorite():
    intent = parse_mlb_question("Will Braves -1.5 cover?", outcome="Yes")
    assert intent.market_type == MLBMarketType.RUN_LINE
    assert intent.side_team == "ATL"
    assert intent.line == 1.5
    assert intent.is_favorite_side is True


def test_parse_run_line_underdog():
    intent = parse_mlb_question("Will Tigers +1.5 cover?", outcome="Yes")
    assert intent.market_type == MLBMarketType.RUN_LINE
    assert intent.side_team == "DET"
    assert intent.line == 1.5
    assert intent.is_favorite_side is False


def test_parse_totals_over():
    intent = parse_mlb_question("Tigers vs. Braves Over 8.5 runs?", outcome="Yes")
    assert intent.market_type == MLBMarketType.TOTALS
    assert intent.line == 8.5
    assert intent.totals_side == "OVER"


def test_parse_totals_under():
    intent = parse_mlb_question("Yankees vs. Red Sox Under 9.5 runs?", outcome="Yes")
    assert intent.market_type == MLBMarketType.TOTALS
    assert intent.line == 9.5
    assert intent.totals_side == "UNDER"


def test_unknown_question_returns_none():
    assert parse_mlb_question("Random nonsense text", outcome="Yes") is None
    assert parse_mlb_question("", outcome="") is None


def test_team_resolution_failure_returns_none():
    """If either team unresolvable → None."""
    assert parse_mlb_question("Braves vs. Bigfoot", outcome="Yes") is None
