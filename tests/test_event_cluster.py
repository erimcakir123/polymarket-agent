import pytest
from src.models import MarketData


def test_cluster_groups_by_event_id():
    from src.event_cluster import EventCluster
    markets = [
        MarketData(condition_id="m1", question="Trump wins?", yes_price=0.60, no_price=0.40,
                   yes_token_id="t1", no_token_id="t2", event_id="evt1", slug="m1"),
        MarketData(condition_id="m2", question="Republicans win House?", yes_price=0.55, no_price=0.45,
                   yes_token_id="t3", no_token_id="t4", event_id="evt1", slug="m2"),
        MarketData(condition_id="m3", question="Fed cuts rates?", yes_price=0.40, no_price=0.60,
                   yes_token_id="t5", no_token_id="t6", event_id="evt2", slug="m3"),
    ]
    ec = EventCluster()
    clusters = ec.group(markets)
    assert "evt1" in clusters
    assert len(clusters["evt1"]) == 2
    assert len(clusters["evt2"]) == 1


def test_arbitrage_detection():
    from src.event_cluster import EventCluster
    markets = [
        MarketData(condition_id="m1", question="A wins", yes_price=0.60, no_price=0.40,
                   yes_token_id="t1", no_token_id="t2", event_id="evt1", slug="m1"),
        MarketData(condition_id="m2", question="B wins", yes_price=0.50, no_price=0.50,
                   yes_token_id="t3", no_token_id="t4", event_id="evt1", slug="m2"),
    ]
    ec = EventCluster()
    arb = ec.check_arbitrage(markets)
    assert arb["sum_yes"] == pytest.approx(1.10)
    assert arb["is_arbitrage"] is True
