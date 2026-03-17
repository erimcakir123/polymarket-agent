import pytest


def test_estimate_slippage():
    from src.orderbook_analyzer import OrderBookAnalyzer
    book = {
        "bids": [
            {"price": "0.55", "size": "5454.5"},
            {"price": "0.54", "size": "3703.7"},
        ],
        "asks": [
            {"price": "0.56", "size": "3571.4"},
            {"price": "0.57", "size": "5263.2"},
        ],
    }
    analyzer = OrderBookAnalyzer(wall_threshold_usd=5000)
    result = analyzer.analyze(book, side="BUY", size_usdc=20.0)
    assert result["estimated_avg_price"] > 0
    assert "slippage_pct" in result


def test_detect_walls():
    from src.orderbook_analyzer import OrderBookAnalyzer
    book = {
        "bids": [{"price": "0.50", "size": "20000"}],
        "asks": [{"price": "0.55", "size": "100"}],
    }
    analyzer = OrderBookAnalyzer(wall_threshold_usd=5000)
    walls = analyzer.detect_walls(book)
    assert len(walls["bid_walls"]) == 1
    assert walls["bid_walls"][0]["price"] == 0.50
