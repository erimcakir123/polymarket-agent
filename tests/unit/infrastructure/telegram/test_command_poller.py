"""TelegramCommandPoller unit tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.infrastructure.telegram.command_poller import TelegramCommandPoller


def _make_update(update_id: int, text: str, chat_id: str = "123") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "text": text,
            "chat": {"id": int(chat_id)},
        },
    }


class TestHandleUpdate:
    def test_stop_command_calls_callback(self) -> None:
        on_stop = MagicMock()
        http_post = MagicMock()
        poller = TelegramCommandPoller(
            bot_token="tok", chat_id="123", on_stop=on_stop,
            http_post=http_post,
        )

        poller._handle(_make_update(1, "/stop", "123"))

        on_stop.assert_called_once()
        http_post.assert_called_once()  # reply sent

    def test_stop_from_wrong_chat_ignored(self) -> None:
        on_stop = MagicMock()
        poller = TelegramCommandPoller(
            bot_token="tok", chat_id="123", on_stop=on_stop,
        )

        poller._handle(_make_update(1, "/stop", "999"))

        on_stop.assert_not_called()

    def test_non_stop_command_ignored(self) -> None:
        on_stop = MagicMock()
        poller = TelegramCommandPoller(
            bot_token="tok", chat_id="123", on_stop=on_stop,
        )

        poller._handle(_make_update(1, "/status", "123"))

        on_stop.assert_not_called()

    def test_offset_advances(self) -> None:
        poller = TelegramCommandPoller(
            bot_token="tok", chat_id="123", on_stop=MagicMock(),
        )
        assert poller._offset == 0

        poller._handle(_make_update(42, "hello", "123"))

        assert poller._offset == 43

    def test_stop_case_insensitive(self) -> None:
        on_stop = MagicMock()
        http_post = MagicMock()
        poller = TelegramCommandPoller(
            bot_token="tok", chat_id="123", on_stop=on_stop,
            http_post=http_post,
        )

        poller._handle(_make_update(1, "/STOP", "123"))

        on_stop.assert_called_once()
