"""circuit_breaker.py için birim testler (TDD §6.15).

NET PnL bazlı: USD biriktirilir, kontrol anında portfolio_value'ya bölünür.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.domain.risk.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
)

PORTFOLIO = 1000.0  # test portfolio value


def _fixed_now(ts: datetime):
    return lambda: ts


def _cb(now: datetime | None = None, cfg: CircuitBreakerConfig | None = None) -> CircuitBreaker:
    now = now or datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(last_daily_reset=now, last_hourly_reset=now)
    return CircuitBreaker(config=cfg, state=state, now_fn=_fixed_now(now))


def test_no_losses_no_halt() -> None:
    cb = _cb()
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is False
    assert reason == ""


def test_daily_loss_triggers_halt_and_cooldown() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-100)  # -$100 = -%10 daily
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is True
    assert "Daily net loss" in reason
    assert cb.state.breaker_active_until is not None


def test_hourly_loss_triggers_halt() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-60)  # -$60 = -%6 (hourly -5% hit)
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is True
    # -6% < -5% hourly threshold, but also < -3% soft block
    assert "Hourly" in reason or "soft" in reason.lower()


def test_soft_block_at_3pct_daily() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-35)  # -$35 = -3.5% daily
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is True
    assert "soft" in reason.lower()


def test_consecutive_losses_trigger_halt() -> None:
    cb = _cb()
    for _ in range(4):
        cb.record_exit(pnl_usd=-1)
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is True
    assert "consecutive losses" in reason


def test_win_resets_consecutive_losses() -> None:
    cb = _cb()
    cb.record_exit(pnl_usd=-1)
    cb.record_exit(pnl_usd=-1)
    cb.record_exit(pnl_usd=+1)  # Win resets
    assert cb.state.consecutive_losses == 0


def test_cooldown_active_blocks_entry() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    cb = _cb(now=start)
    cb.state.breaker_active_until = start + timedelta(minutes=30)
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is True
    assert "cooldown" in reason.lower()


def test_cooldown_expires() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        last_daily_reset=start, last_hourly_reset=start,
        breaker_active_until=start - timedelta(minutes=1),  # already expired
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(start))
    halt, _ = cb.should_halt_entries(PORTFOLIO)
    assert halt is False


def test_daily_reset_after_24h() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    # Eski reset 25 saat önce
    state = CircuitBreakerState(
        daily_realized_pnl_usd=-100.0,
        last_daily_reset=start - timedelta(hours=25),
        last_hourly_reset=start,
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(start))
    cb.reset_if_needed()
    assert cb.state.daily_realized_pnl_usd == 0.0


def test_hourly_reset_after_60min() -> None:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        hourly_realized_pnl_usd=-70.0,
        last_daily_reset=start,
        last_hourly_reset=start - timedelta(minutes=61),
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(start))
    cb.reset_if_needed()
    assert cb.state.hourly_realized_pnl_usd == 0.0


def test_state_to_dict_from_dict_roundtrip() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        daily_realized_pnl_usd=-50.0,
        hourly_realized_pnl_usd=-20.0,
        consecutive_losses=2,
        breaker_active_until=now + timedelta(minutes=30),
        last_daily_reset=now,
        last_hourly_reset=now,
    )
    data = state.to_dict()
    restored = CircuitBreakerState.from_dict(data)
    assert restored.daily_realized_pnl_usd == -50.0
    assert restored.consecutive_losses == 2
    assert restored.breaker_active_until is not None


def test_config_defaults_match_tdd() -> None:
    cfg = CircuitBreakerConfig()
    assert cfg.daily_max_loss_pct == -0.08
    assert cfg.hourly_max_loss_pct == -0.05
    assert cfg.consecutive_loss_limit == 4
    assert cfg.entry_block_threshold == -0.03


def test_net_pnl_wins_offset_losses() -> None:
    """Kazançlar kayıpları dengelerse circuit breaker tetiklenmemeli."""
    cb = _cb()
    cb.record_exit(pnl_usd=-30)  # -$30 kayıp
    cb.record_exit(pnl_usd=+100)  # +$100 kazanç
    # Net: +$70 → +7% → hiçbir eşik tetiklenmez
    halt, _ = cb.should_halt_entries(PORTFOLIO)
    assert halt is False


def test_net_pnl_losses_exceed_wins() -> None:
    """Kayıplar kazançları geçerse circuit breaker tetiklenmeli."""
    cb = _cb()
    cb.record_exit(pnl_usd=+20)   # +$20 kazanç
    cb.record_exit(pnl_usd=-60)   # -$60 kayıp
    # Net: -$40 → -4% → soft block (-3%) tetiklenir
    halt, reason = cb.should_halt_entries(PORTFOLIO)
    assert halt is True
    assert "soft" in reason.lower()


def test_partial_exits_count_toward_net() -> None:
    """Partial exit kârları da net PnL'e dahil."""
    cb = _cb()
    # Partial kazançlar
    cb.record_exit(pnl_usd=+5)
    cb.record_exit(pnl_usd=+7)
    # Full kayıp
    cb.record_exit(pnl_usd=-30)
    # Net: -$18 → -1.8% → soft block (-3%) altında, geçmeli
    halt, _ = cb.should_halt_entries(PORTFOLIO)
    assert halt is False


def test_is_active_true_when_cooldown_future() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        last_daily_reset=now, last_hourly_reset=now,
        breaker_active_until=now + timedelta(minutes=30),
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(now))
    assert cb.is_active is True


def test_is_active_false_when_cooldown_expired() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    state = CircuitBreakerState(
        last_daily_reset=now, last_hourly_reset=now,
        breaker_active_until=now - timedelta(minutes=1),  # geçmiş tarih
    )
    cb = CircuitBreaker(state=state, now_fn=_fixed_now(now))
    assert cb.is_active is False


def test_is_active_false_when_no_cooldown() -> None:
    cb = _cb()
    assert cb.is_active is False


def test_backward_compat_from_dict_old_format() -> None:
    """Eski pct formatındaki state dosyası 0'dan başlamalı."""
    old_data = {
        "daily_realized_pnl_pct": -0.05,  # eski format
        "hourly_realized_pnl_pct": -0.02,
        "consecutive_losses": 1,
        "breaker_active_until": None,
        "last_daily_reset": "2026-04-13T12:00:00+00:00",
        "last_hourly_reset": "2026-04-13T12:00:00+00:00",
    }
    state = CircuitBreakerState.from_dict(old_data)
    # Eski pct alanları yoksayılır, usd 0'dan başlar
    assert state.daily_realized_pnl_usd == 0.0
    assert state.hourly_realized_pnl_usd == 0.0
    assert state.consecutive_losses == 1
