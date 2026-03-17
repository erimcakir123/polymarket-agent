import pytest
from unittest.mock import patch, MagicMock


@patch("src.whale_tracker.requests.get")
def test_detect_whale_positions(mock_get):
    from src.whale_tracker import WhaleTracker
    from src.config import WhaleConfig
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"proxyWallet": "0xwhale1", "conditionId": "0xabc",
         "size": "60000", "outcome": "Yes", "currentValue": "65000"},
    ]
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    tracker = WhaleTracker(WhaleConfig(min_position_usd=50000))
    whales = tracker.check_market("0xabc")
    assert len(whales) == 1
    assert whales[0]["direction"] == "YES"


def test_whale_signal_computation():
    from src.whale_tracker import WhaleTracker
    from src.config import WhaleConfig
    tracker = WhaleTracker(WhaleConfig())
    signal = tracker.compute_signal([
        {"direction": "YES", "size_usd": 80000},
        {"direction": "YES", "size_usd": 60000},
    ])
    assert signal > 0.5
