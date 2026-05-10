"""NBA score mapper — direction + spread_side ile our/opp skorları map'le."""
from __future__ import annotations

import pytest

from src.strategy.exit._nba_score_mapper import map_our_opp_scores


def test_map_buy_yes_home_returns_home_as_our() -> None:
    # BUY_YES on home spread → "biz" home.
    our, opp = map_our_opp_scores(
        home_score=98, away_score=92, direction="BUY_YES", spread_side="home"
    )
    assert (our, opp) == (98, 92)


def test_map_buy_no_home_returns_away_as_our() -> None:
    # BUY_NO on home spread → home cover'a karşı bahis → "biz" away.
    our, opp = map_our_opp_scores(
        home_score=98, away_score=92, direction="BUY_NO", spread_side="home"
    )
    assert (our, opp) == (92, 98)


def test_map_buy_yes_away_returns_away_as_our() -> None:
    # BUY_YES on away spread → "biz" away.
    our, opp = map_our_opp_scores(
        home_score=80, away_score=88, direction="BUY_YES", spread_side="away"
    )
    assert (our, opp) == (88, 80)


def test_map_buy_no_away_returns_home_as_our() -> None:
    # BUY_NO on away spread → away cover'a karşı bahis → "biz" home.
    our, opp = map_our_opp_scores(
        home_score=80, away_score=88, direction="BUY_NO", spread_side="away"
    )
    assert (our, opp) == (80, 88)


def test_map_invalid_direction_raises() -> None:
    with pytest.raises(ValueError):
        map_our_opp_scores(
            home_score=100, away_score=95, direction="HOLD", spread_side="home"
        )


def test_map_invalid_spread_side_raises() -> None:
    with pytest.raises(ValueError):
        map_our_opp_scores(
            home_score=100, away_score=95, direction="BUY_YES", spread_side="middle"
        )
