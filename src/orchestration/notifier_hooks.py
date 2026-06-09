"""SPEC-TG-001 2026-06-02: Telegram bildirim hook'lari (safe wrapper).

entry/exit/exit_alert hook'larini tek yerden yonetir. getattr ile guard
edilir — test SimpleNamespace deps'lerde `notifier` field olmayabilir.
"""
from __future__ import annotations

from typing import Any


def _entry_exit_enabled(deps: Any) -> bool:
    """telegram.alert.entry_exit config'ini guvenli oku (yoksa True — varsayilan).

    PLAN-Z30 g6: False ise per-trade entry/exit mesajlari susturulur (kritik
    alert'ler HealthMonitor'dan ayri akar).
    """
    try:
        return bool(deps.state.config.telegram.alert.entry_exit)
    except AttributeError:
        return True


def notify_entry_safe(deps: Any, position: Any, trade_record: Any) -> None:
    """Pozisyon acilinca telegram bildirimi (notifier yoksa veya disabled ise no-op)."""
    notifier = getattr(deps, "notifier", None)
    if notifier is None:
        return
    if not _entry_exit_enabled(deps):
        return
    notifier.notify_entry(
        slug=position.slug,
        direction=position.direction,
        entry_price=position.entry_price,
        size_usdc=position.size_usdc,
        confidence=position.confidence,
        edge=trade_record.anchor_probability - position.entry_price,
        entry_reason=position.entry_reason or "normal",
    )


def notify_exit_safe(
    deps: Any, slug: str, exit_price: float, realized_pnl: float, reason: str,
) -> None:
    """Pozisyon kapaninca telegram bildirimi (notifier yoksa veya disabled ise no-op)."""
    notifier = getattr(deps, "notifier", None)
    if notifier is None:
        return
    if not _entry_exit_enabled(deps):
        return
    notifier.notify_exit(
        slug=slug,
        exit_price=exit_price,
        realized_pnl=realized_pnl,
        reason=reason,
    )
