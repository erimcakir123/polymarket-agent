import pytest
from datetime import datetime, timezone, timedelta


class TestCircuitBreaker:
    def _make_breaker(self):
        from src.circuit_breaker import CircuitBreaker
        return CircuitBreaker()

    def test_no_halt_initially(self):
        cb = self._make_breaker()
        halt, reason = cb.should_halt_entries()
        assert halt is False

    def test_daily_limit_triggers(self):
        cb = self._make_breaker()
        cb.record_exit(-90.0, 1000.0)  # -9%
        halt, reason = cb.should_halt_entries()
        assert halt is True
        assert "Daily" in reason or "daily" in reason

    def test_hourly_limit_triggers(self):
        cb = self._make_breaker()
        cb.record_exit(-60.0, 1000.0)  # -6%
        halt, reason = cb.should_halt_entries()
        assert halt is True

    def test_consecutive_losses_trigger(self):
        cb = self._make_breaker()
        for _ in range(4):
            cb.record_exit(-5.0, 1000.0)
        halt, reason = cb.should_halt_entries()
        assert halt is True
        assert "consecutive" in reason.lower()

    def test_winning_exit_resets_consecutive(self):
        cb = self._make_breaker()
        cb.record_exit(-5.0, 1000.0)
        cb.record_exit(-5.0, 1000.0)
        cb.record_exit(10.0, 1000.0)  # Win resets
        cb.record_exit(-5.0, 1000.0)
        halt, _ = cb.should_halt_entries()
        assert halt is False  # Only 1 consecutive loss

    def test_soft_block_at_3pct(self):
        cb = self._make_breaker()
        cb.record_exit(-35.0, 1000.0)  # -3.5%
        halt, reason = cb.should_halt_entries()
        assert halt is True
        assert "soft" in reason.lower() or "limit" in reason.lower()

    def test_below_soft_block_no_halt(self):
        cb = self._make_breaker()
        cb.record_exit(-25.0, 1000.0)  # -2.5%
        halt, _ = cb.should_halt_entries()
        assert halt is False

    def test_hourly_reset(self):
        cb = self._make_breaker()
        cb.record_exit(-60.0, 1000.0)
        cb.last_hourly_reset = datetime.now(timezone.utc) - timedelta(minutes=61)
        cb.reset_if_needed()
        assert cb.hourly_realized_pnl_pct == 0.0

    def test_never_halts_exits(self):
        cb = self._make_breaker()
        cb.record_exit(-90.0, 1000.0)
        halt, _ = cb.should_halt_entries()
        assert halt is True

    def test_persistence_fields(self):
        cb = self._make_breaker()
        state = cb.to_dict()
        assert "daily_realized_pnl_pct" in state
        assert "last_daily_reset" in state
        from src.circuit_breaker import CircuitBreaker
        cb2 = CircuitBreaker.from_dict(state)
        assert cb2.daily_realized_pnl_pct == cb.daily_realized_pnl_pct
