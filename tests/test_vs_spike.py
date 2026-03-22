# tests/test_vs_spike.py
import pytest


class TestVsSpike:
    def test_strong_spike_detected(self):
        from src.vs_spike import detect_vs_spike
        # +30% in 2 cycles and still accelerating
        history = [0.10, 0.11, 0.12, 0.10, 0.11, 0.13]  # 0.10→0.13 = +30% in 2 cycles
        result = detect_vs_spike(history, entry_price=0.08)
        assert result["spike"] is True

    def test_no_spike_stable(self):
        from src.vs_spike import detect_vs_spike
        history = [0.10, 0.10, 0.11, 0.10, 0.11, 0.10]
        result = detect_vs_spike(history, entry_price=0.08)
        assert result["spike"] is False

    def test_short_history_no_spike(self):
        from src.vs_spike import detect_vs_spike
        result = detect_vs_spike([0.10, 0.12], entry_price=0.08)
        assert result["spike"] is False


class TestShouldHoldForResolution:
    def test_hold_buy_yes_high_price_high_ai(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is True

    def test_hold_buy_no_where_yes_low(self):
        """BUY_NO where YES=0.15 → effective=0.85 → hold."""
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.80,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is True

    def test_reject_low_scale_out_tier(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=0, score_behind=False, is_already_won=False,
        )
        assert hold is False  # Need scale_out_tier >= 1

    def test_reject_low_ai(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.55,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is False  # AI < 0.70

    def test_reject_score_behind(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=2, score_behind=True, is_already_won=False,
        )
        assert hold is False  # Score behind

    def test_already_won_always_holds(self):
        """score_terminal_win overrides all other conditions."""
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.50, effective_ai=0.40,
            scale_out_tier=0, score_behind=True, is_already_won=True,
        )
        assert hold is True  # Already won overrides everything

    def test_effective_price_below_80c_rejected(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.75, effective_ai=0.80,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is False  # effective_price < 0.80
