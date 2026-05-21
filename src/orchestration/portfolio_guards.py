"""Sport-agnostic portfolio guard helpers (SPEC-R).

Hem bookmaker-anchor entry path'i (gate.py) hem de model-anchor entry path'i
(entry_processor.process_signals) tarafından ortak kullanılır. DRY refactor —
davranış değişmez, sadece extract.

Bookmaker-spesifik guard'lar (manipulation, enrichment, no_edge, entry_price_cap)
bu modülde değil — gate.py kendi başına yapar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GuardSkip:
    """Bir guard'ın market'i reddetme kararı. None döndürmek = guard geçildi."""
    reason: str
    detail: str = ""


class _BreakerLike(Protocol):
    def should_halt_entries(self) -> tuple[bool, str]: ...


class _CooldownStateLike(Protocol):
    cooldown_remaining: int


class _CooldownLike(Protocol):
    def is_active(self) -> bool: ...
    state: _CooldownStateLike


class _PortfolioLike(Protocol):
    def count(self) -> int: ...
    def count_event(self, event_id: str) -> int: ...


class _BlacklistLike(Protocol):
    def is_blacklisted(self, condition_id: str = "",
                       event_id: str = "") -> bool: ...


class _MarketLike(Protocol):
    condition_id: str
    event_id: str | None


def check_global_halts(
    *,
    breaker: _BreakerLike,
    cooldown: _CooldownLike,
    portfolio: _PortfolioLike,
    max_positions: int,
) -> GuardSkip | None:
    """Tüm market'ler için tek seferlik halt kontrolü.

    Returns:
        Skip ediliyorsa GuardSkip; geçildi ise None.
    """
    halt, reason = breaker.should_halt_entries()
    if halt:
        detail = reason[len("breaker: "):] if reason.startswith("breaker: ") else reason
        return GuardSkip(reason="circuit_breaker", detail=detail)

    # is_active() decrements cooldown_remaining as a side effect; read BEFORE call
    # to match historical gate.py behavior (test_run_cooldown_sets_skip_detail).
    remaining = cooldown.state.cooldown_remaining
    if cooldown.is_active():
        return GuardSkip(reason="cooldown_active", detail=f"cycles_remaining={remaining}")

    count = portfolio.count()
    if count >= max_positions:
        return GuardSkip(reason="max_positions_reached", detail=f"count={count}/{max_positions}")

    return None


def check_per_market_guards(
    *,
    market: _MarketLike,
    portfolio: _PortfolioLike,
    blacklist: _BlacklistLike,
    max_positions_per_event: int,
) -> GuardSkip | None:
    """Tek market için per-market guard kontrolleri (event_cap + blacklist)."""
    if market.event_id:
        event_count = portfolio.count_event(market.event_id)
        if event_count >= max_positions_per_event:
            return GuardSkip(
                reason="event_already_held",
                detail=(
                    f"event_id={market.event_id} "
                    f"count={event_count}/{max_positions_per_event}"
                ),
            )

    if blacklist.is_blacklisted(condition_id=market.condition_id):
        return GuardSkip(reason="blacklisted", detail="match=condition_id")
    if market.event_id and blacklist.is_blacklisted(event_id=market.event_id):
        return GuardSkip(reason="blacklisted", detail="match=event_id")

    return None
