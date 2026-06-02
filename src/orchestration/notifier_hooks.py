"""SPEC-TG-001 2026-06-02: Telegram bildirim hook'lari (safe wrapper).

entry/exit/exit_alert hook'larini tek yerden yonetir. getattr ile guard
edilir — test SimpleNamespace deps'lerde `notifier` field olmayabilir.
"""
from __future__ import annotations

from typing import Any


def notify_entry_safe(deps: Any, position: Any, trade_record: Any) -> None:
    """Pozisyon acilinca telegram bildirimi (notifier yoksa veya disabled ise no-op)."""
    notifier = getattr(deps, "notifier", None)
    if notifier is None:
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
    notifier.notify_exit(
        slug=slug,
        exit_price=exit_price,
        realized_pnl=realized_pnl,
        reason=reason,
    )
