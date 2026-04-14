"""circuit_breaker.py için birim testler (TDD §6.15)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.domain.risk.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
)


def _fixed_now(ts: datetime):
    return lambda: ts


def _cb(now: datetime | None = None, cfg: CircuitBreakerConfig | None = None) -> CircuitBreaker:
    now = now or datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(last_daily_reset=now, last_hourly_reset=now)
    return CircuitBreaker(config=cfg, state=state, now_fn=_fixed_now(now))


def test_no_losses_no_halt() -> None:
    cb = _cb()
    halt, reason = cb.should_halt_entries()
    assert halt is False
    assert reason == ""


def test_daily_loss_triggers_halt_and_cooldown() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-100, portfolio_value=1000)  # -%10 daily
    halt, reason = cb.should_halt_entries()
    assert halt is True
    assert "Daily loss" in reason
    assert cb.state.breaker_active_until is not None


def test_hourly_loss_triggers_halt() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-60, portfolio_value=1000)  # -%6 (soft block + hourly)
    halt, reason = cb.should_halt_entries()
    assert halt is True
    # -6% < -3% soft block threshold AND also < -5% hourly
    # should_halt_entries order: cooldown > daily > hourly > consecutive > soft
    # Daily threshold -8% not hit; hourly -5% hit first
    assert "Hourly loss" in reason or "soft" in reason.lower()


def test_soft_block_at_3pct_daily() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-35, portfolio_value=1000)  # -3.5% daily
    halt, reason = cb.should_halt_entries()
    assert halt is True
    assert "soft" in reason.lower()


def test_consecutive_losses_trigger_halt() -> None:
    cb = _cb()
    for _ in range(4):
        cb.record_exit(pnl_usd=-1, portfolio_value=1000)
    halt, reason = cb.should_halt_entries()
    assert halt is True
    assert "consecutive losses" in reason


def test_win_resets_consecutive_losses() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-1, portfolio_value=1000)
    cb.record_exit(pnl_usd=-1, portfolio_value=1000)
    cb.record_exit(pnl_usd=+1, portfolio_value=1000)  # Win resets
    assert cb.state.consecutive_losses == 0


def test_cooldown_active_blocks_entry() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    cb = _cb(now=start)
    cb.state.breaker_active_until = start + timedelta(minutes=30)
    halt, reason = cb.should_halt_entries()
    assert halt is True
    assert "cooldown" in reason.lower()


def test_cooldown_expires() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        last_daily_reset=start, last_hourly_reset=start,
        breaker_active_until=start - timedelta(minutes=1),  # already expired
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(start))
    halt, _ = cb.should_halt_entries()
    assert halt is False


def test_daily_reset_after_24h() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    # Eski reset 25 saat önce
    state = CircuitBreakerState(
        daily_realized_pnl_pct=-0.10,
        last_daily_reset=start - timedelta(hours=25),
        last_hourly_reset=start,
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(start))
    cb.reset_if_needed()
    assert cb.state.daily_realized_pnl_pct == 0.0


def test_hourly_reset_after_60min() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        hourly_realized_pnl_pct=-0.07,
        last_daily_reset=start,
        last_hourly_reset=start - timedelta(minutes=61),
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(start))
    cb.reset_if_needed()
    assert cb.state.hourly_realized_pnl_pct == 0.0


def test_state_to_dict_from_dict_roundtrip() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        daily_realized_pnl_pct=-0.05,
        hourly_realized_pnl_pct=-0.02,
        consecutive_losses=2,
        breaker_active_until=now + timedelta(minutes=30),
        last_daily_reset=now,
        last_hourly_reset=now,
    )
    data = state.to_dict()
    restored = CircuitBreakerState.from_dict(data)
    assert restored.daily_realized_pnl_pct == -0.05
    assert restored.consecutive_losses == 2
    assert restored.breaker_active_until is not None


def test_config_defaults_match_tdd() -> None:
    cfg = CircuitBreakerConfig()
    assert cfg.daily_max_loss_pct == -0.08
    assert cfg.hourly_max_loss_pct == -0.05
    assert cfg.consecutive_loss_limit == 4
    assert cfg.entry_block_threshold == -0.03
