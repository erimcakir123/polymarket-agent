import pytest
from unittest.mock import patch, MagicMock


def _mock_getme_and_flush():
    """Helper: returns side_effect list for successful getMe + flush."""
    mock_resp_getme = MagicMock()
    mock_resp_getme.status_code = 200
    mock_resp_getme.json.return_value = {
        "ok": True,
        "result": {"username": "TestBot", "id": 12345},
    }
    mock_resp_flush = MagicMock()
    mock_resp_flush.status_code = 200
    mock_resp_flush.json.return_value = {"result": []}
    return [mock_resp_getme, mock_resp_flush]


@patch("src.notifier.requests.get")
@patch("src.notifier.requests.post")
def test_send_notification(mock_post, mock_get):
    from src.notifier import TelegramNotifier
    mock_get.side_effect = _mock_getme_and_flush()
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


@patch("src.notifier.requests.get")
def test_format_trade_message(mock_get):
    from src.notifier import TelegramNotifier
    mock_get.side_effect = _mock_getme_and_flush()
    notifier = TelegramNotifier(bot_token="test", chat_id="123")
    msg = notifier.format_trade("Will X?", "BUY_YES", 15.0, 0.55, 0.10)
    assert "Will X?" in msg
    assert "BUY_YES" in msg
    assert "$15.00" in msg


def test_validate_token_success():
    """Valid token should log bot name and keep enabled=True."""
    from src.notifier import TelegramNotifier

    with patch("src.notifier.requests.get") as mock_get:
        mock_get.side_effect = _mock_getme_and_flush()

        notifier = TelegramNotifier("test-token", "12345", enabled=True)
        assert notifier.enabled is True


def test_validate_token_failure_disables():
    """Invalid token should set enabled=False."""
    from src.notifier import TelegramNotifier

    with patch("src.notifier.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_get.return_value = mock_resp

        notifier = TelegramNotifier("bad-token", "12345", enabled=True)
        assert notifier.enabled is False


def test_send_logs_non_200():
    """send() should log response body on non-200 status."""
    from src.notifier import TelegramNotifier

    notifier = TelegramNotifier.__new__(TelegramNotifier)
    notifier.bot_token = "test-token"
    notifier.chat_id = "12345"
    notifier.enabled = True
    notifier._last_update_id = 0

    with patch("src.notifier.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = '{"ok":false,"description":"Bad Request"}'
        mock_post.return_value = mock_resp

        result = notifier.send("test message")
        assert result is False
