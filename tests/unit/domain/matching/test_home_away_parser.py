"""parse_home_away_side slug parser testleri."""
from __future__ import annotations

import pytest

from src.domain.matching.market_line_parser import parse_home_away_side


@pytest.mark.parametrize("slug, expected", [
    ("spread-away-4pt5",           "away"),
    ("spread-home-3pt0",           "home"),
    ("moneyline-winner-away",      "away"),
    ("moneyline-winner-home",      "home"),
    ("nba-celtics-away-spread",    "away"),
    ("celtics-home-minus-3-5",     "home"),
    ("away-winner",                "away"),
    ("home-winner",                "home"),
    # Edge: home/away sözcüğü yok → None
    ("nba-winner-celtics-pacers",  None),
    ("moneyline-winner",           None),
    ("",                           None),
])
def test_parse_home_away_side(slug: str, expected: str | None) -> None:
    assert parse_home_away_side(slug) == expected
