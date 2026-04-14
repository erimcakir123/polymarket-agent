"""Portfolio circuit breaker — pure state machine (TDD §6.15).

Kurallar:
  - Günlük kayıp ≥ %8 → 120 dk cooldown
  - Saatlik kayıp ≥ %5 → 60 dk cooldown
  - 4 ardışık kayıp → 60 dk cooldown
  - Soft blok: günlük kayıp ≥ %3 → yeni giriş askıda

I/O YOK: to_dict() / from_dict() round-trip; persist orkestrasyonda yapılır.
Zaman dışarıdan verilir (now_fn) — test için deterministik.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CircuitBreakerConfig:
    """Eşikler (config.yaml'dan gelir, defaults TDD §6.15)."""
    daily_max_loss_pct: float = -0.08
    hourly_max_loss_pct: float = -0.05
    consecutive_loss_limit: int = 4
    cooldown_after_daily_min: int = 120
    cooldown_after_hourly_min: int = 60
    cooldown_after_consecutive_min: int = 60
    entry_block_threshold: float = -0.03  # Soft block


@dataclass
class CircuitBreakerState:
    """Pure state — persist için to_dict/from_dict."""
    daily_realized_pnl_pct: float = 0.0
    hourly_realized_pnl_pct: float = 0.0
    consecutive_losses: int = 0
    breaker_active_until: datetime | None = None
    last_daily_reset: datetime = field(default_factory=_default_now)
    last_hourly_reset: datetime = field(default_factory=_default_now)

    def to_dict(self) -> dict:
        return {
            "daily_realized_pnl_pct": self.daily_realized_pnl_pct,
            "hourly_realized_pnl_pct": self.hourly_realized_pnl_pct,
            "consecutive_losses": self.consecutive_losses,
            "breaker_active_until": self.breaker_active_until.isoformat() if self.breaker_active_until else None,
            "last_daily_reset": self.last_daily_reset.isoformat(),
            "last_hourly_reset": self.last_hourly_reset.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CircuitBreakerState":
        raw = d.get("breaker_active_until")
        return cls(
            daily_realized_pnl_pct=d.get("daily_realized_pnl_pct", 0.0),
            hourly_realized_pnl_pct=d.get("hourly_realized_pnl_pct", 0.0),
            consecutive_losses=d.get("consecutive_losses", 0),
            breaker_active_until=datetime.fromisoformat(raw) if raw else None,
            last_daily_reset=datetime.fromisoformat(d["last_daily_reset"]) if d.get("last_daily_reset") else _default_now(),
            last_hourly_reset=datetime.fromisoformat(d["last_hourly_reset"]) if d.get("last_hourly_reset") else _default_now(),
        )


class CircuitBreaker:
    """Pure circuit breaker logic. Zaman DI ile verilir (test için)."""

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        state: CircuitBreakerState | None = None,
        now_fn: Callable[[], datetime] = _default_now,
    ) -> None:
        self.config = config or CircuitBreakerConfig()
        self.state = state or CircuitBreakerState()
        self._now = now_fn

    def record_exit(self, pnl_usd: float, portfolio_value: float) -> None:
        pnl_pct = pnl_usd / portfolio_value if portfolio_value > 0 else 0.0
        self.state.daily_realized_pnl_pct += pnl_pct
        self.state.hourly_realized_pnl_pct += pnl_pct
        if pnl_usd < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

    def reset_if_needed(self) -> None:
        now = self._now()
        if (now - self.state.last_daily_reset).total_seconds() >= 86_400:
            self.state.daily_realized_pnl_pct = 0.0
            self.state.last_daily_reset = now
        if (now - self.state.last_hourly_reset).total_seconds() >= 3_600:
            self.state.hourly_realized_pnl_pct = 0.0
            self.state.last_hourly_reset = now

    def should_halt_entries(self) -> tuple[bool, str]:
        """Sadece entry halt — exit'leri ASLA durdurmaz."""
        self.reset_if_needed()
        now = self._now()
        cfg = self.config
        st = self.state

        if st.breaker_active_until and now < st.breaker_active_until:
            remaining = int((st.breaker_active_until - now).total_seconds() // 60)
            return True, f"Circuit breaker cooldown ({remaining}min remaining)"

        if st.daily_realized_pnl_pct <= cfg.daily_max_loss_pct:
            st.breaker_active_until = now + timedelta(minutes=cfg.cooldown_after_daily_min)
            return True, f"Daily loss {st.daily_realized_pnl_pct:.1%} hit {cfg.daily_max_loss_pct:.0%} limit"

        if st.hourly_realized_pnl_pct <= cfg.hourly_max_loss_pct:
            st.breaker_active_until = now + timedelta(minutes=cfg.cooldown_after_hourly_min)
            return True, f"Hourly loss {st.hourly_realized_pnl_pct:.1%} hit {cfg.hourly_max_loss_pct:.0%} limit"

        if st.consecutive_losses >= cfg.consecutive_loss_limit:
            st.breaker_active_until = now + timedelta(minutes=cfg.cooldown_after_consecutive_min)
            st.consecutive_losses = 0  # Çift cooldown önle
            return True, f"{cfg.consecutive_loss_limit} consecutive losses"

        if st.daily_realized_pnl_pct <= cfg.entry_block_threshold:
            return True, f"Daily loss {st.daily_realized_pnl_pct:.1%} exceeded soft limit {cfg.entry_block_threshold:.0%}"

        return False, ""
