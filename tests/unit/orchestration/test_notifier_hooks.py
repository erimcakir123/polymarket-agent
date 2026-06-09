"""notifier_hooks: entry_exit config gate (PLAN-Z30 g6).

entry_exit=False → per-trade telegram mesajı atılmaz (gürültü susturma).
entry_exit=True / config yok → eski davranış (mesaj atılır).
"""
from __future__ import annotations

from types import SimpleNamespace

from src.orchestration.notifier_hooks import notify_entry_safe, notify_exit_safe


class _Notifier:
    def __init__(self) -> None:
        self.entry_calls = 0
        self.exit_calls = 0

    def notify_entry(self, **kwargs) -> None:
        self.entry_calls += 1

    def notify_exit(self, **kwargs) -> None:
        self.exit_calls += 1


def _deps(notifier, entry_exit: bool | None) -> SimpleNamespace:
    if entry_exit is None:
        return SimpleNamespace(notifier=notifier)  # config path yok → varsayilan
    alert = SimpleNamespace(entry_exit=entry_exit)
    telegram = SimpleNamespace(alert=alert)
    config = SimpleNamespace(telegram=telegram)
    state = SimpleNamespace(config=config)
    return SimpleNamespace(notifier=notifier, state=state)


def _position() -> SimpleNamespace:
    return SimpleNamespace(
        slug="x", direction="BUY_YES", entry_price=0.4, size_usdc=15.0,
        confidence="A", entry_reason="normal",
    )


def test_entry_exit_disabled_no_notify() -> None:
    notifier = _Notifier()
    deps = _deps(notifier, entry_exit=False)
    notify_entry_safe(deps, _position(), SimpleNamespace(anchor_probability=0.5))
    notify_exit_safe(deps, "x", 0.6, 3.0, "tp")
    assert notifier.entry_calls == 0
    assert notifier.exit_calls == 0


def test_entry_exit_enabled_notifies() -> None:
    notifier = _Notifier()
    deps = _deps(notifier, entry_exit=True)
    notify_entry_safe(deps, _position(), SimpleNamespace(anchor_probability=0.5))
    notify_exit_safe(deps, "x", 0.6, 3.0, "tp")
    assert notifier.entry_calls == 1
    assert notifier.exit_calls == 1


def test_entry_exit_missing_config_defaults_true() -> None:
    """Config path yoksa (eski/test deps) varsayilan True — bozulmaz."""
    notifier = _Notifier()
    deps = _deps(notifier, entry_exit=None)
    notify_entry_safe(deps, _position(), SimpleNamespace(anchor_probability=0.5))
    assert notifier.entry_calls == 1
