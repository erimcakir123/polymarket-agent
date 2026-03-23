# tests/test_scale_in.py
import pytest


class TestShouldScaleIn:
    def test_scale_in_when_profitable(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.05, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=False,
        )
        assert ok is True  # 5% profit > 2% threshold, 4 cycles, room to scale

    def test_scale_in_via_score_ahead(self):
        """Score-ahead can confirm even if PnL is marginal (but still positive)."""
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.01, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=True,
        )
        assert ok is True  # PnL > 0 + score_ahead → confirmed

    def test_no_scale_in_losing(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=-0.05, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=True,
        )
        assert ok is False  # Losing position, don't add even with score ahead

    def test_no_scale_in_too_early(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.08, cycles_held=1,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=False,
        )
        assert ok is False  # Need min 3 cycles

    def test_no_scale_in_already_complete(self):
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.15, cycles_held=10,
            scale_in_complete=True, intended_size_usdc=100.0,
            current_size_usdc=100.0, score_ahead=False,
        )
        assert ok is False  # Already at full size

    def test_marginal_pnl_no_score_rejected(self):
        """PnL between 0-2% without score_ahead → not confirmed."""
        from src.scale_out import should_scale_in
        ok, _ = should_scale_in(
            unrealized_pnl_pct=0.01, cycles_held=4,
            scale_in_complete=False, intended_size_usdc=100.0,
            current_size_usdc=50.0, score_ahead=False,
        )
        assert ok is False


class TestGetScaleInSize:
    def test_kelly_based_sizing(self):
        from src.scale_out import get_scale_in_size
        size = get_scale_in_size(
            intended_size_usdc=100.0, current_size_usdc=50.0,
            kelly_size_now=80.0,
        )
        # min(remaining=50, kelly_now - current=30) = 30
        assert abs(size - 30.0) < 0.01

    def test_kelly_larger_than_remaining(self):
        from src.scale_out import get_scale_in_size
        size = get_scale_in_size(
            intended_size_usdc=100.0, current_size_usdc=90.0,
            kelly_size_now=200.0,
        )
        # min(remaining=10, kelly_now - current=110) = 10
        assert abs(size - 10.0) < 0.01

    def test_kelly_smaller_than_current(self):
        """If Kelly now says less than current position, don't add."""
        from src.scale_out import get_scale_in_size
        size = get_scale_in_size(
            intended_size_usdc=100.0, current_size_usdc=50.0,
            kelly_size_now=40.0,
        )
        assert size == 0.0  # Kelly says we're already overexposed
