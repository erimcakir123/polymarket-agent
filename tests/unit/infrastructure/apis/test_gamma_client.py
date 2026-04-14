"""gamma_client.py için birim testler."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.infrastructure.apis.gamma_client import GammaClient


def _resp(status: int = 200, body: Any = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if status < 400:
        r.raise_for_status = MagicMock(return_value=None)
    else:
        r.raise_for_status = MagicMock(side_effect=RuntimeError("http"))
    r.json.return_value = body if body is not None else []
    return r


def _event(cid: str, **market_overrides) -> dict:
    market = {
        "conditionId": cid,
        "question": "Q?",
        "slug": "a-vs-b",
        "clobTokenIds": '["tokY", "tokN"]',
        "outcomePrices": '["0.60", "0.40"]',
        "liquidity": "5000",
        "volume24hr": "1000",
        "endDate": "2026-04-14T00:00:00Z",
        "closed": False,
        "acceptingOrders": True,
    }
    market.update(market_overrides)
    return {
        "id": "evt_1",
        "live": False,
        "ended": False,
        "startTime": "2026-04-13T20:00:00Z",
        "markets": [market],
        "tags": [{"slug": "basketball"}, {"slug": "nba"}],
    }


def test_parse_market_valid() -> None:
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xabc")["markets"][0]
    raw["_event_live"] = True
    raw["_sport_tag"] = "basketball_nba"
    raw["_event_id"] = "evt_1"
    m = client._parse_market(raw)
    assert m is not None
    assert m.condition_id == "0xabc"
    assert m.yes_price == 0.60
    assert m.no_price == 0.40
    assert m.yes_token_id == "tokY"
    assert m.no_token_id == "tokN"
    assert m.event_live is True
    assert m.event_id == "evt_1"
    assert m.sport_tag == "basketball_nba"


def test_parse_market_missing_tokens_returns_none() -> None:
    client = GammaClient(http_get=MagicMock())
    raw = {"conditionId": "0xabc", "question": "Q", "slug": "s"}
    assert client._parse_market(raw) is None


def test_parse_market_prefers_event_start_time_over_market_start_date() -> None:
    """Single-game event: event.startTime = maç saati, market.startDate = yaratılma.
    match_start_iso event.startTime'dan gelmeli, yoksa scanner bu maçı 'geçmişte başlamış'
    sanıp atar (bkz. docs/superpowers/plans/2026-04-14-gamma-match-start-fix.md).
    """
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xgame")["markets"][0]
    raw["_event_start_time"] = "2026-04-14T23:30:00Z"  # maç saati (gelecek)
    raw["startDate"] = "2025-12-08T05:12:40Z"          # market yaratılma (aylar önce)
    raw["_event_live"] = False
    raw["_sport_tag"] = "nba"
    raw["_event_id"] = "evt_game"
    m = client._parse_market(raw)
    assert m is not None
    assert m.match_start_iso == "2026-04-14T23:30:00Z"


def test_parse_market_falls_back_to_market_start_date_for_futures() -> None:
    """Futures event: event.startTime yok (None/""), market.startDate var.
    match_start_iso fallback olarak market.startDate kullanmalı.
    """
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xfutures")["markets"][0]
    raw["_event_start_time"] = ""                       # futures: event startTime yok
    raw["startDate"] = "2025-06-23T16:00:27Z"          # market yaratılma
    raw["_event_live"] = False
    raw["_sport_tag"] = "nhl"
    raw["_event_id"] = "evt_futures"
    m = client._parse_market(raw)
    assert m is not None
    assert m.match_start_iso == "2025-06-23T16:00:27Z"


def test_parse_market_match_start_empty_when_both_missing() -> None:
    """Ne event.startTime ne market.startDate varsa match_start_iso = ""."""
    client = GammaClient(http_get=MagicMock())
    raw = _event("0xnone")["markets"][0]
    raw["_event_start_time"] = ""
    raw["startDate"] = ""
    raw["_event_live"] = False
    raw["_sport_tag"] = "tennis"
    raw["_event_id"] = "evt_none"
    m = client._parse_market(raw)
    assert m is not None
    assert m.match_start_iso == ""


def test_fetch_events_happy_path() -> None:
    http = MagicMock()
    # /sports boş → fallback parent tags. Sonra parent tag sports + esports iter.
    http.side_effect = [
        _resp(200, []),  # /sports empty → fallback
        _resp(200, [_event("0x1")]),  # parent sports page 1
        _resp(200, []),  # parent esports page 1 empty
        _resp(200, []),  # PARENT_TAGS scan 2nd pass: sports
        _resp(200, []),  # PARENT_TAGS scan 2nd pass: esports
    ]
    client = GammaClient(http_get=http)
    markets = client.fetch_events()
    assert len(markets) == 1
    assert markets[0].condition_id == "0x1"


def test_fetch_events_http_error_returns_empty() -> None:
    http = MagicMock(side_effect=RuntimeError("boom"))
    client = GammaClient(http_get=http)
    assert client.fetch_events() == []


def test_sports_endpoint_caches() -> None:
    http = MagicMock()
    http.side_effect = [
        _resp(200, [{"sport": "nba", "tags": "100,200"}]),  # /sports
        _resp(200, []),  # tag=100
        _resp(200, []),  # tag=200
        _resp(200, []),  # parent sports
        _resp(200, []),  # parent esports
    ]
    client = GammaClient(http_get=http)
    client.fetch_events()
    sports_calls = [c for c in http.call_args_list if "/sports" in str(c)]
    assert len(sports_calls) == 1
    # İkinci çağrı — cache kullanılmalı, /sports tekrar çağrılmamalı
    http.reset_mock()
    http.side_effect = [_resp(200, []), _resp(200, []), _resp(200, []), _resp(200, [])]
    client.fetch_events()
    sports_calls2 = [c for c in http.call_args_list if "/sports" in str(c)]
    assert len(sports_calls2) == 0
