"""SPEC-K: bookmaker spread/totals market parser unit tests."""
from __future__ import annotations

from src.strategy.enrichment._spread_totals_parser import (
    parse_bookmaker_spread,
    parse_bookmaker_totals,
)


# --- Spread parser ---


def _spread_market(home: str, away: str, home_point: float, away_point: float,
                    home_price: float = 1.91, away_price: float = 1.91) -> dict:
    return {
        "key": "spreads",
        "outcomes": [
            {"name": home, "price": home_price, "point": home_point},
            {"name": away, "price": away_price, "point": away_point},
        ],
    }


def test_spread_happy_path_returns_line_and_probs() -> None:
    """NBA -7.5/+7.5 with 1.91/1.91 → (7.5, ~0.5, ~0.5) after vig normalize."""
    market = _spread_market("Lakers", "Celtics", -7.5, 7.5)
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is not None
    line, home_prob, away_prob = result
    assert line == 7.5
    assert abs(home_prob - 0.5) < 0.01
    assert abs(away_prob - 0.5) < 0.01


def test_spread_within_tolerance_returns_bookmaker_line() -> None:
    """target=7.5, bookmaker=8.0, tolerance=0.5 → accept, return bookmaker line."""
    market = _spread_market("Lakers", "Celtics", -8.0, 8.0)
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is not None
    line, _, _ = result
    assert line == 8.0  # bookmaker's actual line


def test_spread_beyond_tolerance_returns_none() -> None:
    """target=7.5, bookmaker=10.0, tolerance=0.5 → None (line mismatch)."""
    market = _spread_market("Lakers", "Celtics", -10.0, 10.0)
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is None


def test_spread_vig_outlier_returns_none() -> None:
    """1.40/1.40 odds → 1/1.4 + 1/1.4 ≈ 1.428 > 1.20 → outlier rejected."""
    market = _spread_market("Lakers", "Celtics", -7.5, 7.5,
                              home_price=1.40, away_price=1.40)
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is None


def test_spread_missing_home_team_returns_none() -> None:
    """Outcomes don't contain home team name → None."""
    market = _spread_market("Other Team", "Celtics", -7.5, 7.5)
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is None


def test_spread_missing_outcomes_returns_none() -> None:
    """Empty outcomes → None."""
    market = {"key": "spreads", "outcomes": []}
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is None


def test_spread_favorite_higher_implied_prob() -> None:
    """Favorite (lower odds) should have higher implied prob after normalize."""
    # Lakers -7.5 with 1.50 (favorite), Celtics +7.5 with 2.50 (underdog)
    market = _spread_market("Lakers", "Celtics", -7.5, 7.5,
                              home_price=1.50, away_price=2.50)
    result = parse_bookmaker_spread(market, "Lakers", "Celtics", target_line=7.5,
                                      line_tolerance=0.5)
    assert result is not None
    _, home_prob, away_prob = result
    assert home_prob > away_prob
    assert abs(home_prob + away_prob - 1.0) < 0.001  # vig-normalized


# --- Totals parser ---


def _totals_market(over_point: float, under_point: float | None = None,
                    over_price: float = 1.91, under_price: float = 1.91,
                    over_name: str = "Over", under_name: str = "Under") -> dict:
    if under_point is None:
        under_point = over_point
    return {
        "key": "totals",
        "outcomes": [
            {"name": over_name, "price": over_price, "point": over_point},
            {"name": under_name, "price": under_price, "point": under_point},
        ],
    }


def test_totals_happy_path_returns_line_and_probs() -> None:
    """215.5 line, 1.91/1.91 → (215.5, ~0.5, ~0.5)."""
    market = _totals_market(215.5)
    result = parse_bookmaker_totals(market, target_line=215.5, line_tolerance=0.5)
    assert result is not None
    line, over_prob, under_prob = result
    assert line == 215.5
    assert abs(over_prob - 0.5) < 0.01
    assert abs(under_prob - 0.5) < 0.01


def test_totals_within_tolerance_returns_bookmaker_line() -> None:
    market = _totals_market(216.0)
    result = parse_bookmaker_totals(market, target_line=215.5, line_tolerance=0.5)
    assert result is not None
    line, _, _ = result
    assert line == 216.0


def test_totals_beyond_tolerance_returns_none() -> None:
    market = _totals_market(220.0)
    result = parse_bookmaker_totals(market, target_line=215.5, line_tolerance=0.5)
    assert result is None


def test_totals_vig_outlier_returns_none() -> None:
    """1.40/1.40 → ~1.428 total → outlier."""
    market = _totals_market(215.5, over_price=1.40, under_price=1.40)
    result = parse_bookmaker_totals(market, target_line=215.5, line_tolerance=0.5)
    assert result is None


def test_totals_case_insensitive_over_under() -> None:
    """over/Over/OVER all accepted."""
    for over_name, under_name in [("over", "under"), ("Over", "Under"),
                                    ("OVER", "UNDER")]:
        market = _totals_market(215.5, over_name=over_name, under_name=under_name)
        result = parse_bookmaker_totals(market, target_line=215.5, line_tolerance=0.5)
        assert result is not None, f"failed for {over_name}/{under_name}"


def test_totals_missing_over_outcome_returns_none() -> None:
    """Only under outcome present → None."""
    market = {
        "key": "totals",
        "outcomes": [
            {"name": "Under", "price": 1.91, "point": 215.5},
        ],
    }
    result = parse_bookmaker_totals(market, target_line=215.5, line_tolerance=0.5)
    assert result is None
