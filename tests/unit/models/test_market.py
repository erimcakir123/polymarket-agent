"""MarketData için birim testler."""
from __future__ import annotations

import json

from src.models.market import MarketData


def _valid_market(**overrides) -> MarketData:
    base = {
        "condition_id": "0xabc",
        "question": "Will Lakers beat Celtics?",
        "slug": "lakers-vs-celtics",
        "yes_token_id": "tok1",
        "no_token_id": "tok2",
        "yes_price": 0.55,
        "no_price": 0.45,
        "liquidity": 12_000.0,
        "volume_24h": 5_000.0,
        "tags": ["basketball", "nba"],
        "end_date_iso": "2026-04-14T23:00:00Z",
    }
    base.update(overrides)
    return MarketData(**base)


def test_market_data_required_fields() -> None:
    m = _valid_market()
    assert m.condition_id == "0xabc"
    assert m.yes_price == 0.55
    assert "basketball" in m.tags


def test_market_data_defaults() -> None:
    m = _valid_market()
    assert m.event_id is None
    assert m.event_live is False
    assert m.event_ended is False
    assert m.match_start_iso == ""
    assert m.sport_tag == ""
    assert m.sports_market_type == ""
    assert m.closed is False
    assert m.resolved is False
    assert m.accepting_orders is True
    assert m.odds_api_implied_prob is None


def test_market_data_json_roundtrip() -> None:
    m = _valid_market(event_id="evt_1", sport_tag="basketball_nba")
    data = m.model_dump()
    reparsed = MarketData(**data)
    assert reparsed.event_id == "evt_1"
    assert reparsed.sport_tag == "basketball_nba"
    blob = json.dumps(m.model_dump(mode="json"))
    assert "evt_1" in blob
