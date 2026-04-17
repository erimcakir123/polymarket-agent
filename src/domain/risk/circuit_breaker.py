"""Portfolio circuit breaker — pure state machine (TDD §6.15).

Kurallar:
  - Günlük NET kayıp ≥ %8 → 120 dk cooldown
  - Saatlik NET kayıp ≥ %5 → 60 dk cooldown
  - 4 ardışık kayıp → 60 dk cooldown
  - Soft blok: günlük NET kayıp ≥ %3 → yeni giriş askıda

NET PnL takibi: kazanç ve kayıplar USD olarak biriktirilir, kontrol
anında güncel portfolio_value'ya bölünerek yüzdeye çevrilir.
Partial exit'ler de dahil — tüm realized PnL sayılır.

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
    """Pure state — persist için to_dict/from_dict.

    PnL USD cinsinden biriktirilir (pct değil). Yüzde kontrol anında hesaplanır.
    """
    daily_realized_pnl_usd: float = 0.0
    hourly_realized_pnl_usd: float = 0.0
    consecutive_losses: int = 0
    breaker_active_until: datetime | None = None
    last_daily_reset: datetime = field(default_factory=_default_now)
    last_hourly_reset: datetime = field(default_factory=_default_now)

    def to_dict(self) -> dict:
        return {
            "daily_realized_pnl_usd": self.daily_realized_pnl_usd,
            "hourly_realized_pnl_usd": self.hourly_realized_pnl_usd,
            "consecutive_losses": self.consecutive_losses,
            "breaker_active_until": self.breaker_active_until.isoformat() if self.breaker_active_until else None,
            "last_daily_reset": self.last_daily_reset.isoformat(),
            "last_hourly_reset": self.last_hourly_reset.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CircuitBreakerState":
        raw = d.get("breaker_active_until")
        # Backward compat: eski "pct" alanlarını yoksay, 0'dan başla
        return cls(
            daily_realized_pnl_usd=d.get("daily_realized_pnl_usd", 0.0),
            hourly_realized_pnl_usd=d.get("hourly_realized_pnl_usd", 0.0),
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

    def record_exit(self, pnl_usd: float) -> None:
        """Exit PnL'i USD olarak kaydet (full + partial)."""
        self.state.daily_realized_pnl_usd += pnl_usd
        self.state.hourly_realized_pnl_usd += pnl_usd
        if pnl_usd < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

    def reset_if_needed(self) -> None:
        now = self._now()
        if (now - self.state.last_daily_reset).total_seconds() >= 86_400:
            self.state.daily_realized_pnl_usd = 0.0
            self.state.last_daily_reset = now
        if (now - self.state.last_hourly_reset).total_seconds() >= 3_600:
            self.state.hourly_realized_pnl_usd = 0.0
            self.state.last_hourly_reset = now

    def should_halt_entries(self, portfolio_value: float) -> tuple[bool, str]:
        """Sadece entry halt — exit'leri ASLA durdurmaz.

        NET PnL: günlük/saatlik USD toplamı ÷ güncel portfolio_value.
        """
        self.reset_if_needed()
        now = self._now()
        cfg = self.config
        st = self.state

        if st.breaker_active_until and now < st.breaker_active_until:
            remaining = int((st.breaker_active_until - now).total_seconds() // 60)
            return True, f"Circuit breaker cooldown ({remaining}min remaining)"

        if portfolio_value <= 0:
            return False, ""

        daily_pct = st.daily_realized_pnl_usd / portfolio_value
        hourly_pct = st.hourly_realized_pnl_usd / portfolio_value

        if daily_pct <= cfg.daily_max_loss_pct:
            st.breaker_active_until = now + timedelta(minutes=cfg.cooldown_after_daily_min)
            return True, f"Daily net loss {daily_pct:.1%} hit {cfg.daily_max_loss_pct:.0%} limit"

        if hourly_pct <= cfg.hourly_max_loss_pct:
            st.breaker_active_until = now + timedelta(minutes=cfg.cooldown_after_hourly_min)
            return True, f"Hourly net loss {hourly_pct:.1%} hit {cfg.hourly_max_loss_pct:.0%} limit"

        if st.consecutive_losses >= cfg.consecutive_loss_limit:
            st.breaker_active_until = now + timedelta(minutes=cfg.cooldown_after_consecutive_min)
            st.consecutive_losses = 0  # Çift cooldown önle
            return True, f"{cfg.consecutive_loss_limit} consecutive losses"

        if daily_pct <= cfg.entry_block_threshold:
            return True, f"Daily net loss {daily_pct:.1%} exceeded soft limit {cfg.entry_block_threshold:.0%}"

        return False, ""
