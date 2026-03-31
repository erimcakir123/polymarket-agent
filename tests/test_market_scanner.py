import json, pytest
from unittest.mock import patch, MagicMock

def _future_date_iso(days: int = 5) -> str:
    """Return ISO date string N days from now."""
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


SAMPLE_MARKET = {
    "conditionId": "0xabc123",
    "question": "Will Trump win?",
    "slug": "will-trump-win",
    "outcomePrices": json.dumps(["0.62", "0.38"]),
    "outcomes": json.dumps(["Yes", "No"]),
    "clobTokenIds": json.dumps(["tok_yes_1", "tok_no_1"]),
    "volume24hr": "120000",
    "liquidity": "25000",
    "tags": json.dumps([{"label": "politics"}]),
    "endDate": _future_date_iso(5),
    "description": "Resolution based on...",
    "eventId": "evt_001",
}


@patch("src.market_scanner.requests.get")
def test_fetch_markets_parses_gamma_response(mock_get):
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    mock_resp = MagicMock()
    mock_resp.json.return_value = [SAMPLE_MARKET]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    scanner = MarketScanner(ScannerConfig())
    markets = scanner.fetch()
    assert len(markets) == 1
    assert markets[0].yes_price == pytest.approx(0.62)
    assert markets[0].no_price == pytest.approx(0.38)
    assert markets[0].condition_id == "0xabc123"


@patch("src.market_scanner.requests.get")
def test_fetch_markets_filters_low_volume(mock_get):
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    low_vol = {**SAMPLE_MARKET, "volume24hr": "1000", "liquidity": "50"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = [low_vol]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    scanner = MarketScanner(ScannerConfig())
    markets = scanner.fetch()
    assert len(markets) == 0


@patch("src.market_scanner.requests.get")
def test_fetch_markets_filters_by_tag(mock_get):
    from src.market_scanner import MarketScanner
    from src.config import ScannerConfig
    crypto = {**SAMPLE_MARKET, "tags": json.dumps([{"label": "crypto"}])}
    mock_resp = MagicMock()
    mock_resp.json.return_value = [crypto]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    scanner = MarketScanner(ScannerConfig(tags=["politics", "geopolitics"]))
    markets = scanner.fetch()
    assert len(markets) == 0


def test_parse_market_resolved_fields():
    """Verify closed/resolved/accepting_orders are parsed from raw Gamma data."""
    from src.market_scanner import MarketScanner
    scanner = MarketScanner.__new__(MarketScanner)
    raw = {
        "conditionId": "0xabc",
        "question": "Test?",
        "outcomePrices": '["0.6","0.4"]',
        "clobTokenIds": '["tok_yes","tok_no"]',
        "volume24hr": 1000,
        "liquidity": 500,
        "slug": "test-market",
        "tags": "[]",
        "endDate": "2026-04-01T00:00:00Z",
        "description": "Test market",
        "closed": True,
        "resolved": True,
        "acceptingOrders": False,
    }
    m = scanner._parse_market(raw)
    assert m is not None
    assert m.closed is True
    assert m.resolved is True
    assert m.accepting_orders is False


def test_parse_market_resolved_defaults():
    """Verify defaults when Gamma response omits closed/resolved/acceptingOrders."""
    from src.market_scanner import MarketScanner
    scanner = MarketScanner.__new__(MarketScanner)
    raw = {
        "conditionId": "0xdef",
        "question": "Test?",
        "outcomePrices": '["0.5","0.5"]',
        "clobTokenIds": '["tok_yes","tok_no"]',
        "volume24hr": 0,
        "liquidity": 0,
        "slug": "test-defaults",
        "tags": "[]",
        "endDate": "",
        "description": "",
    }
    m = scanner._parse_market(raw)
    assert m is not None
    assert m.closed is False
    assert m.resolved is False
    assert m.accepting_orders is True
