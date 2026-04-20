"""EventGrouper unit tests (SPEC-015)."""
from __future__ import annotations

from src.models.market import MarketData
from src.orchestration.event_grouper import EventGroup, group_markets_by_event


def _market(cid: str, eid: str, yes: float, sport: str = "soccer", question: str = "") -> MarketData:
    return MarketData(
        condition_id=cid, question=question,
        slug=f"slug-{cid}", yes_token_id="y", no_token_id="n",
        yes_price=yes, no_price=1 - yes,
        liquidity=50000, volume_24h=10000, tags=[],
        end_date_iso="2026-04-25T00:00:00Z",
        sport_tag=sport, event_id=eid,
    )


def test_group_three_way_soccer_event() -> None:
    markets = [
        _market("c1", "evt1", 0.45, question="Will Arsenal win?"),
        _market("c2", "evt1", 0.27, question="Will the match end in a draw?"),
        _market("c3", "evt1", 0.28, question="Will Chelsea win?"),
    ]
    groups = group_markets_by_event(markets)
    assert len(groups) == 1
    g = groups[0]
    assert g.event_id == "evt1"
    assert g.market_type == "THREE_WAY"
    assert len(g.markets) == 3


def test_group_two_way_sport_passes_through() -> None:
    markets = [_market("c1", "evt1", 0.55, sport="mlb", question="Yankees vs Red Sox")]
    groups = group_markets_by_event(markets)
    assert len(groups) == 1
    assert groups[0].market_type == "BINARY"
    assert len(groups[0].markets) == 1


def test_group_multiple_events_separated() -> None:
    markets = [
        _market("c1", "evt1", 0.45),
        _market("c2", "evt1", 0.27),
        _market("c3", "evt1", 0.28),
        _market("c4", "evt2", 0.60),
        _market("c5", "evt2", 0.18),
        _market("c6", "evt2", 0.22),
    ]
    groups = group_markets_by_event(markets)
    assert len(groups) == 2
    assert {g.event_id for g in groups} == {"evt1", "evt2"}


def test_group_empty_event_id_skipped() -> None:
    """event_id boşsa o market grouping'e dahil olmaz."""
    markets = [
        _market("c1", "", 0.55, sport="mlb", question="No event"),
        _market("c2", "evt1", 0.50, sport="mlb", question="X vs Y"),
    ]
    groups = group_markets_by_event(markets)
    assert len(groups) == 1
    assert groups[0].event_id == "evt1"


def test_classify_outcomes_home_draw_away() -> None:
    """Question'da 'draw' içeren market draw, diğerleri home/away sırasıyla."""
    markets = [
        _market("c1", "evt1", 0.45, question="Will Arsenal win?"),
        _market("c2", "evt1", 0.27, question="Will the match end in a draw?"),
        _market("c3", "evt1", 0.28, question="Will Chelsea win?"),
    ]
    groups = group_markets_by_event(markets)
    g = groups[0]
    home, draw, away = g.classify_outcomes()
    assert home is not None and "Arsenal" in home.question
    assert draw is not None and "draw" in draw.question.lower()
    assert away is not None and "Chelsea" in away.question


def test_classify_outcomes_binary_returns_none_tuple() -> None:
    """BINARY group'ta classify_outcomes (None, None, None) döner."""
    markets = [_market("c1", "evt1", 0.55, sport="mlb", question="Yankees vs Red Sox")]
    groups = group_markets_by_event(markets)
    assert groups[0].classify_outcomes() == (None, None, None)


def test_group_rugby_three_way() -> None:
    """Rugby de 3-way sport, aynı mantık."""
    markets = [
        _market("c1", "evt1", 0.50, sport="rugby", question="Will England win?"),
        _market("c2", "evt1", 0.10, sport="rugby", question="Will match end in a draw?"),
        _market("c3", "evt1", 0.40, sport="rugby", question="Will France win?"),
    ]
    groups = group_markets_by_event(markets)
    assert len(groups) == 1
    assert groups[0].market_type == "THREE_WAY"
