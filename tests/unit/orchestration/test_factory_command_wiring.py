from unittest.mock import MagicMock

from src.infrastructure.telegram.command_poller import TelegramCommandPoller


def test_set_handlers_binds_callbacks():
    poller = TelegramCommandPoller(bot_token="t", chat_id="1", on_stop=lambda: None)
    agent = MagicMock()
    poller.set_handlers(agent.request_pause, agent.request_resume, agent.status_summary)
    poller._http_post = lambda *a, **k: None
    poller._handle({"update_id": 1, "message": {"text": "/pause", "chat": {"id": 1}}})
    agent.request_pause.assert_called_once()
