"""Portfolio-level circuit breaker — halts new entries on excessive losses.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #14
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DAILY_MAX_LOSS_PCT = -0.08
HOURLY_MAX_LOSS_PCT = -0.05
CONSECUTIVE_LOSS_LIMIT = 4
COOLDOWN_AFTER_DAILY = 120
COOLDOWN_AFTER_HOURLY = 60
COOLDOWN_AFTER_CONSECUTIVE = 60
ENTRY_BLOCK_THRESHOLD = -0.03  # Soft block at -3% daily (fires before hourly -5% hard limit)
STATE_FILE = Path("logs/circuit_breaker_state.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CircuitBreaker:
    def __init__(self):
        self.daily_realized_pnl_pct: float = 0.0
        self.hourly_realized_pnl_pct: float = 0.0
        self.consecutive_losses: int = 0
        self.breaker_active_until: datetime | None = None
        self.last_daily_reset: datetime = _now()
        self.last_hourly_reset: datetime = _now()

    def record_exit(self, pnl_usd: float, portfolio_value: float) -> None:
        pnl_pct = pnl_usd / portfolio_value if portfolio_value > 0 else 0
        self.daily_realized_pnl_pct += pnl_pct
        self.hourly_realized_pnl_pct += pnl_pct
        if pnl_usd < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        self.save()

    def reset_if_needed(self) -> None:
        now = _now()
        if (now - self.last_daily_reset).total_seconds() >= 86400:
            self.daily_realized_pnl_pct = 0.0
            self.last_daily_reset = now
        if (now - self.last_hourly_reset).total_seconds() >= 3600:
            self.hourly_realized_pnl_pct = 0.0
            self.last_hourly_reset = now

    def should_halt_entries(self) -> tuple[bool, str]:
        """Returns (halt, reason). Never halts exits — only entry decisions."""
        self.reset_if_needed()
        now = _now()

        if self.breaker_active_until and now < self.breaker_active_until:
            remaining = int((self.breaker_active_until - now).total_seconds() // 60)
            return True, f"Circuit breaker cooldown ({remaining}min remaining)"

        if self.daily_realized_pnl_pct <= DAILY_MAX_LOSS_PCT:
            self.breaker_active_until = now + timedelta(minutes=COOLDOWN_AFTER_DAILY)
            logger.warning("Circuit breaker: daily loss %.1f%% hit %.0f%% limit",
                           self.daily_realized_pnl_pct * 100, DAILY_MAX_LOSS_PCT * 100)
            self.save()
            return True, f"Daily loss {self.daily_realized_pnl_pct:.1%} hit {DAILY_MAX_LOSS_PCT:.0%} limit"

        if self.hourly_realized_pnl_pct <= HOURLY_MAX_LOSS_PCT:
            self.breaker_active_until = now + timedelta(minutes=COOLDOWN_AFTER_HOURLY)
            self.save()
            return True, f"Hourly loss {self.hourly_realized_pnl_pct:.1%} hit {HOURLY_MAX_LOSS_PCT:.0%} limit"

        if self.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            self.breaker_active_until = now + timedelta(minutes=COOLDOWN_AFTER_CONSECUTIVE)
            self.consecutive_losses = 0
            self.save()
            return True, f"{CONSECUTIVE_LOSS_LIMIT} consecutive losses"

        if self.daily_realized_pnl_pct <= ENTRY_BLOCK_THRESHOLD:
            return True, f"Daily loss {self.daily_realized_pnl_pct:.1%} exceeded soft limit {ENTRY_BLOCK_THRESHOLD:.0%}"

        return False, ""

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
    def from_dict(cls, d: dict) -> CircuitBreaker:
        cb = cls()
        cb.daily_realized_pnl_pct = d.get("daily_realized_pnl_pct", 0.0)
        cb.hourly_realized_pnl_pct = d.get("hourly_realized_pnl_pct", 0.0)
        cb.consecutive_losses = d.get("consecutive_losses", 0)
        raw = d.get("breaker_active_until")
        cb.breaker_active_until = datetime.fromisoformat(raw) if raw else None
        cb.last_daily_reset = datetime.fromisoformat(d["last_daily_reset"])
        cb.last_hourly_reset = datetime.fromisoformat(d["last_hourly_reset"])
        return cb

    def save(self) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> CircuitBreaker:
        if STATE_FILE.exists():
            try:
                return cls.from_dict(json.loads(STATE_FILE.read_text()))
            except Exception:
                pass
        return cls()
