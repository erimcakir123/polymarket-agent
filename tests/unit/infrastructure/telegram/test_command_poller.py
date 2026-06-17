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


def test_set_on_stop_replaces_callback() -> None:
    """set_on_stop sonrası /stop yeni callback'i tetikler."""
    initial_cb = MagicMock()
    new_cb = MagicMock()
    poller = TelegramCommandPoller(
        bot_token="tok", chat_id="123", on_stop=initial_cb,
    )
    poller.set_on_stop(new_cb)
    poller._handle({"update_id": 1, "message": {"text": "/stop", "chat": {"id": 123}}})
    initial_cb.assert_not_called()
    new_cb.assert_called_once()


def test_default_on_stop_is_replaceable_lambda() -> None:
    """Constructor'da no-op lambda → set_on_stop ile değiştirilebilir."""
    poller = TelegramCommandPoller(
        bot_token="tok", chat_id="123", on_stop=lambda: None,
    )
    real_cb = MagicMock()
    poller.set_on_stop(real_cb)
    poller._handle({"update_id": 1, "message": {"text": "/stop", "chat": {"id": 123}}})
    real_cb.assert_called_once()


def _poller_full(calls):
    return TelegramCommandPoller(
        bot_token="tok", chat_id="123",
        on_stop=lambda: calls.append("stop"),
        on_pause=lambda: calls.append("pause"),
        on_resume=lambda: calls.append("resume"),
        on_status=lambda: "STATUS-TEXT",
        http_post=lambda *a, **k: None,
    )


def test_pause_command_dispatches():
    calls = []
    _poller_full(calls)._handle(_make_update(1, "/pause", "123"))
    assert calls == ["pause"]


def test_resume_command_dispatches():
    calls = []
    _poller_full(calls)._handle(_make_update(1, "/resume", "123"))
    assert calls == ["resume"]


def test_status_command_replies_with_text():
    sent = {}
    p = _poller_full([])
    p._http_post = lambda url, json, timeout: sent.update(json)
    p._handle(_make_update(1, "/status", "123"))
    assert sent["text"] == "STATUS-TEXT"


def test_set_handlers_binds_pause_resume_status():
    calls = []
    poller = TelegramCommandPoller(bot_token="tok", chat_id="123", on_stop=lambda: None)
    poller.set_handlers(
        on_pause=lambda: calls.append("pause"),
        on_resume=lambda: calls.append("resume"),
        on_status=lambda: "S",
    )
    poller._http_post = lambda *a, **k: None
    poller._handle(_make_update(1, "/pause", "123"))
    assert calls == ["pause"]
