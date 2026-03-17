import json, pytest
from unittest.mock import patch, MagicMock

SAMPLE_MARKET = {
    "conditionId": "0xabc123",
    "question": "Will Trump win 2028?",
    "slug": "will-trump-win-2028",
    "outcomePrices": json.dumps(["0.62", "0.38"]),
    "outcomes": json.dumps(["Yes", "No"]),
    "clobTokenIds": json.dumps(["tok_yes_1", "tok_no_1"]),
    "volume24hr": "120000",
    "liquidity": "25000",
    "tags": json.dumps([{"label": "politics"}]),
    "endDate": "2028-11-15T00:00:00Z",
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
    low_vol = {**SAMPLE_MARKET, "volume24hr": "1000", "liquidity": "500"}
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
