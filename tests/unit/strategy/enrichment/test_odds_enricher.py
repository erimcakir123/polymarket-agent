"""odds_enricher.py için birim testler — mock odds_client ile."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.strategy.enrichment.odds_enricher import _weighted_average, enrich_market


def _market(**over) -> MarketData:
    base = dict(
        condition_id="0x1",
        question="Will Lakers beat Celtics?",
        slug="nba-lal-bos-2026-04-13",
        yes_token_id="y", no_token_id="n",
        yes_price=0.55, no_price=0.45,
        liquidity=50000, volume_24h=10000,
        tags=[],
        end_date_iso="2026-04-14T00:00:00Z",
    )
    base.update(over)
    return MarketData(**base)


def _client_returning(odds_events: list, sports: list | None = None) -> MagicMock:
    c = MagicMock()
    c.get_sports.return_value = sports or []
    c.get_events.return_value = []
    c.get_odds.return_value = odds_events
    return c


def _event_with_bookmakers(home: str, away: str, bookmakers: list) -> dict:
    return {"home_team": home, "away_team": away, "bookmakers": bookmakers}


def _bookie(key: str, home_odds: float, away_odds: float, home: str, away: str) -> dict:
    return {
        "key": key,
        "title": key.title(),
        "markets": [{
            "key": "h2h",
            "outcomes": [
                {"name": home, "price": home_odds},
                {"name": away, "price": away_odds},
            ],
        }],
    }


def _bookie_totals(key: str, over_odds: float, under_odds: float, line: float) -> dict:
    return {
        "key": key, "title": key.title(),
        "markets": [{
            "key": "totals",
            "outcomes": [
                {"name": "Over", "price": over_odds, "point": line},
                {"name": "Under", "price": under_odds, "point": line},
            ],
        }],
    }


def test_enrich_totals_returns_over_probability() -> None:
    """SPEC-Z21: totals market → bahisçi konsensüsü Over olasılığı (P(YES)=Over)."""
    event = _event_with_bookmakers(
        "Los Angeles Lakers", "Boston Celtics",
        [
            _bookie_totals("pinnacle", 1.91, 1.91, 215.5),
            _bookie_totals("bet365", 1.95, 1.87, 215.5),
            _bookie_totals("draftkings", 1.90, 1.92, 215.5),
            _bookie_totals("fanduel", 1.93, 1.89, 215.5),
        ],
    )
    client = _client_returning([event])
    m = _market(
        question="Los Angeles Lakers vs Boston Celtics: O/U 215.5",
        slug="nba-lal-bos-2026-04-13-total-215pt5",
        sports_market_type="totals",
    )
    r = enrich_market(m, client)
    assert r.probability is not None
    # Over @ ~1.91 → ~0.50 implied (vig-normalize sonrası)
    assert 0.45 < r.probability.probability < 0.55
    assert r.probability.has_sharp is True  # pinnacle


def test_enrich_single_sharp_below_weight_threshold() -> None:
    # Pinnacle tek başına → weight 3.0 < 5 → C conf (yetersiz veri)
    # Probability hala döner ama confidence C (entry bloklanır)
    event = _event_with_bookmakers(
        "Los Angeles Lakers", "Boston Celtics",
        [_bookie("pinnacle", 1.67, 2.40, "Los Angeles Lakers", "Boston Celtics")],
    )
    client = _client_returning([event])
    r = enrich_market(_market(), client)
    assert r.probability is not None
    assert r.probability.has_sharp is True
    assert r.probability.confidence == "C"  # weight 3.0 < 5 threshold
    assert r.probability.probability > 0.5


def test_enrich_multiple_books_reaches_A_conf() -> None:
    # Pinnacle(3.0) + bet365(1.5) + 2× standard(1.0) = 6.5 → ≥5, has_sharp → A
    event = _event_with_bookmakers(
        "Los Angeles Lakers", "Boston Celtics",
        [
            _bookie("pinnacle", 1.67, 2.40, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("bet365", 1.70, 2.30, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("draftkings", 1.65, 2.45, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("fanduel", 1.68, 2.35, "Los Angeles Lakers", "Boston Celtics"),
        ],
    )
    client = _client_returning([event])
    r = enrich_market(_market(), client)
    assert r.probability is not None
    assert r.probability.confidence == "A"
    assert r.probability.has_sharp is True
    assert 0.55 < r.probability.probability < 0.65  # Weighted ~60%


def test_enrich_filters_polymarket_bookie() -> None:
    # Polymarket bookmaker circular data → filtrelenir
    event = _event_with_bookmakers(
        "Los Angeles Lakers", "Boston Celtics",
        [
            _bookie("polymarket", 1.50, 3.00, "Los Angeles Lakers", "Boston Celtics"),  # skip
            _bookie("bet365", 1.70, 2.30, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("draftkings", 1.65, 2.45, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("fanduel", 1.68, 2.35, "Los Angeles Lakers", "Boston Celtics"),
        ],
    )
    client = _client_returning([event])
    r = enrich_market(_market(), client)
    assert r.probability is not None
    # Polymarket atlandığı için probability 1.50 odds'u içermemeli
    # Sadece bet365/dk/fanduel → ~60%
    assert 0.55 < r.probability.probability < 0.65


def test_enrich_buy_no_direction_swapped() -> None:
    # Market team_a=Celtics (slug'a göre değil — odds API home_team check)
    # Question 'Will Celtics beat Lakers' → team_a=Celtics
    # Eğer Odds API home=Lakers away=Celtics → home_is_a=False, prob swap
    event = _event_with_bookmakers(
        "Los Angeles Lakers", "Boston Celtics",
        [
            _bookie("bet365", 1.70, 2.30, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("dk", 1.65, 2.45, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("fd", 1.68, 2.35, "Los Angeles Lakers", "Boston Celtics"),
            _bookie("mgm", 1.67, 2.40, "Los Angeles Lakers", "Boston Celtics"),
        ],
    )
    client = _client_returning([event])
    m = _market(question="Will Celtics beat Lakers?")
    r = enrich_market(m, client)
    assert r.probability is not None
    # Celtics (team_a) away position'da → prob_a = away_prob ~40%
    assert 0.35 < r.probability.probability < 0.45


def test_enrich_no_sport_key_returns_none() -> None:
    client = _client_returning([])
    m = _market(question="Random non-sports question", slug="xyz-unknown", tags=[])
    # Slug unknown, tags empty, no tennis hint, discovery fallback → no events → None
    r = enrich_market(m, client)
    assert r.probability is None


def test_enrich_no_team_match_returns_none() -> None:
    event = _event_with_bookmakers(
        "Other Team A", "Other Team B",
        [_bookie("bet365", 2.0, 2.0, "Other Team A", "Other Team B")],
    )
    client = _client_returning([event])
    r = enrich_market(_market(), client)
    assert r.probability is None


# --- SPEC-001: EnrichResult + fail_reason taxonomy tests ---

from src.domain.analysis.enrich_outcome import EnrichFailReason


def test_enrich_market_no_sport_key_returns_sport_key_unresolved() -> None:
    market = _market(slug="unknown-foo-bar-2026-01-01", question="X vs Y", tags=[])
    client = _client_returning(odds_events=[], sports=[])
    result = enrich_market(market, client)
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.SPORT_KEY_UNRESOLVED


def test_enrich_market_team_extract_fail_returns_team_extract_failed() -> None:
    market = _market(question="")
    client = _client_returning(odds_events=[], sports=[{"key":"basketball_nba","active":True}])
    result = enrich_market(market, client)
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.TEAM_EXTRACT_FAILED


def test_enrich_market_empty_events_returns_empty_events() -> None:
    market = _market()
    client = _client_returning(odds_events=[])
    result = enrich_market(market, client)
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.EMPTY_EVENTS


def test_enrich_market_no_event_match_returns_event_no_match() -> None:
    market = _market(question="Will Lakers beat Celtics?")
    events = [{"home_team":"Warriors","away_team":"Nuggets","bookmakers":[]}]
    client = _client_returning(odds_events=events)
    result = enrich_market(market, client)
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.EVENT_NO_MATCH


def test_enrich_market_empty_bookmakers_returns_empty_bookmakers() -> None:
    market = _market(question="Will Lakers beat Celtics?")
    events = [{"home_team":"Lakers","away_team":"Celtics","bookmakers":[]}]
    client = _client_returning(odds_events=events)
    result = enrich_market(market, client)
    assert result.probability is None
    assert result.fail_reason == EnrichFailReason.EMPTY_BOOKMAKERS


def test_enrich_market_ok_returns_probability_and_no_fail_reason() -> None:
    market = _market(question="Will Lakers beat Celtics?")
    events = [{
        "home_team":"Lakers","away_team":"Celtics",
        "bookmakers":[{"key":"fanduel","markets":[{"key":"h2h","outcomes":[
            {"name":"Lakers","price":1.80},{"name":"Celtics","price":2.20}]}]}],
    }]
    client = _client_returning(odds_events=events)
    result = enrich_market(market, client)
    assert result.probability is not None
    assert result.fail_reason is None
    assert 0.0 < result.probability.probability < 1.0


# --- SPEC-C: 2-Way Bookmaker Sanity ---


def test_h2h_2way_vig_outlier_skipped(caplog) -> None:
    """2-way vig outlier (sum > 1.20) → skip + INFO log."""
    caplog.set_level(logging.INFO)
    # Odds 1.5/1.5 → her implied 0.667 → total = 1.333 (outlier, > 1.20)
    bookmakers = [
        {
            "key": "shady_bm",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "Team A", "price": 1.5},
                    {"name": "Team B", "price": 1.5},
                ],
            }],
        },
    ]
    result = _weighted_average(
        bookmakers, "Team A", "Team B", home_is_a=True,
    )
    assert result is None
    assert any("Bookmaker drop" in rec.message for rec in caplog.records)


def test_h2h_2way_normal_passes() -> None:
    """2-way (NHL/MLB) bookmaker normal odds → kabul (regression)."""
    # 1.95/1.95 → total ~1.026 (normal vig)
    bookmakers = [
        {
            "key": "good_bm",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "Team A", "price": 1.95},
                    {"name": "Team B", "price": 1.95},
                ],
            }],
        },
    ]
    result = _weighted_average(
        bookmakers, "Team A", "Team B", home_is_a=True,
    )
    assert result is not None
    assert 0.4 < result.probability < 0.6  # normalized ~0.5


