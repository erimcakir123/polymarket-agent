"""WTA slug filter — predictor uses ATP-only Sackmann data (2026-05-20).

Any market whose slug indicates WTA must be rejected at parse time:
- (a) prevents silent skips from missing ratings
- (b) prevents coincidental ATP name collisions yielding garbage predictions
"""
from __future__ import annotations

from src.strategy.enrichment.tennis_question_parser import parse_tennis_question


def test_parser_skips_wta_slug() -> None:
    """WTA slug → None even when question + sports_market_type are valid."""
    result = parse_tennis_question(
        question="Set 1 Winner: Swiatek vs Rybakina",
        sports_market_type="tennis_first_set_winner",
        slug="wta-swiatek-rybakina-2026-05-20-first-set-winner",
    )
    assert result is None


def test_parser_accepts_atp_slug() -> None:
    """ATP slug → parsed dict (control case for WTA filter)."""
    result = parse_tennis_question(
        question="Set 1 Winner: Tsitsipas vs Tien",
        sports_market_type="tennis_first_set_winner",
        slug="atp-tsitsipas-tien-2026-05-20-first-set-winner",
    )
    assert result is not None
    assert result["market_type"] == "first_set_winner"
    assert "Tsitsipas" in result["p1_name"]
    assert "Tien" in result["p2_name"]


def test_parser_skips_wta_slug_case_insensitive() -> None:
    """Uppercase WTA- prefix should also be rejected."""
    result = parse_tennis_question(
        question="Set 1 Winner: Swiatek vs Rybakina",
        sports_market_type="tennis_first_set_winner",
        slug="WTA-swiatek-rybakina-2026-05-20",
    )
    assert result is None


def test_parser_no_slug_does_not_filter() -> None:
    """Empty slug → parser proceeds (filter only fires on explicit wta- prefix)."""
    result = parse_tennis_question(
        question="Set 1 Winner: Tsitsipas vs Tien",
        sports_market_type="tennis_first_set_winner",
        slug="",
    )
    assert result is not None
