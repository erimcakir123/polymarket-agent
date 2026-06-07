import signal

from src.orchestration.signal_handlers import build_shutdown_handler


def test_handler_invokes_stop_callback():
    calls = []
    handler = build_shutdown_handler(lambda: calls.append("stop"))
    handler(signal.SIGTERM, None)
    assert calls == ["stop"]


def test_handler_swallows_callback_errors():
    def boom():
        raise RuntimeError("x")
    handler = build_shutdown_handler(boom)
    handler(signal.SIGINT, None)  # exception bastırılmalı, raise etmemeli
