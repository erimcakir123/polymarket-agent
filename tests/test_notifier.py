import pytest
from unittest.mock import patch, MagicMock


@patch("src.notifier.requests.post")
def test_send_notification(mock_post):
    from src.notifier import TelegramNotifier
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123")
    result = notifier.send("Test message")
    assert result is True
    mock_post.assert_called_once()


def test_notifier_disabled():
    from src.notifier import TelegramNotifier
    notifier = TelegramNotifier(bot_token="", chat_id="")
    result = notifier.send("Test message")
    assert result is False


def test_format_trade_message():
    from src.notifier import TelegramNotifier
    notifier = TelegramNotifier(bot_token="test", chat_id="123")
    msg = notifier.format_trade("Will X?", "BUY_YES", 15.0, 0.55, 0.10)
    assert "Will X?" in msg
    assert "BUY_YES" in msg
    assert "$15.00" in msg
