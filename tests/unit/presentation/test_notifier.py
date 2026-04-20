"""notifier.py için birim testler."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.presentation.notifier import TelegramNotifier


def _resp(status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    return r


def test_disabled_notifier_noop() -> None:
    n = TelegramNotifier(enabled=False)
    assert n.send("test") is True  # no-op True


def test_enabled_requires_token_and_chat_id() -> None:
    # enabled=True ama token/chat_id boş → effective disabled
    n = TelegramNotifier(enabled=True, bot_token="", chat_id="")
    assert n.enabled is False


def test_send_calls_api() -> None:
    http = MagicMock(return_value=_resp(200))
    n = TelegramNotifier(enabled=True, bot_token="tok", chat_id="123", http_post=http)
    assert n.send("hello") is True
    assert http.called
    url = http.call_args.args[0]
    assert "tok" in url
    payload = http.call_args.kwargs.get("json")
    assert payload["chat_id"] == "123"
    assert payload["text"] == "hello"


def test_send_api_error_returns_false() -> None:
    http = MagicMock(side_effect=RuntimeError("boom"))
    n = TelegramNotifier(enabled=True, bot_token="tok", chat_id="123", http_post=http)
    assert n.send("x") is False


def test_send_non_200_returns_false() -> None:
    http = MagicMock(return_value=_resp(403))
    n = TelegramNotifier(enabled=True, bot_token="tok", chat_id="123", http_post=http)
    assert n.send("x") is False


def test_notify_entry_formats_message() -> None:
    http = MagicMock(return_value=_resp(200))
    n = TelegramNotifier(enabled=True, bot_token="t", chat_id="c", http_post=http)
    n.notify_entry("lakers-celtics", "BUY_YES", 0.45, 40.0, "A", "directional", bookmaker_prob=0.62)
    text = http.call_args.kwargs["json"]["text"]
    assert "ENTRY" in text
    assert "lakers-celtics" in text
    assert "BUY_YES" in text
    assert "$0.450" in text
    assert "P(book) 62.0%" in text


def test_notify_exit_uses_win_emoji_on_profit() -> None:
    http = MagicMock(return_value=_resp(200))
    n = TelegramNotifier(enabled=True, bot_token="t", chat_id="c", http_post=http)
    n.notify_exit("slug", 0.60, realized_pnl=5.50, reason="scale_out")
    text = http.call_args.kwargs["json"]["text"]
    assert "✅" in text
    assert "+5.50" in text


def test_notify_exit_uses_loss_emoji_on_negative() -> None:
    http = MagicMock(return_value=_resp(200))
    n = TelegramNotifier(enabled=True, bot_token="t", chat_id="c", http_post=http)
    n.notify_exit("slug", 0.30, realized_pnl=-10.0, reason="never_in_profit")
    text = http.call_args.kwargs["json"]["text"]
    assert "🔴" in text


def test_notify_circuit_breaker() -> None:
    http = MagicMock(return_value=_resp(200))
    n = TelegramNotifier(enabled=True, bot_token="t", chat_id="c", http_post=http)
    n.notify_circuit_breaker("Daily loss hit", active_until="2026-04-13T14:00Z")
    text = http.call_args.kwargs["json"]["text"]
    assert "CIRCUIT BREAKER" in text
    assert "Daily loss hit" in text
