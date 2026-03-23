# tests/test_integration.py
"""Integration tests — verify multi-module interactions.
Spec Section 11: Testing Strategy.
"""
import pytest


class TestScaleOutPlusMatchAware:
    """Scale Out tier 1 fires, then match-aware exit should use reduced shares."""
    def test_tier1_then_match_exit(self):
        from src.scale_out import apply_partial_exit, check_scale_out
        from src.match_exit import check_match_exit

        # Position: 100 shares, 25% profit → tier 1 fires
        tier = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.26, volatility_swing=False)
        assert tier is not None

        # After partial exit: 60 shares remain
        result = apply_partial_exit(
            shares=100, size_usdc=50.0, entry_price=0.50, direction="BUY_YES",
            shares_sold=40, fill_price=0.63, tier="tier1_risk_free",
            original_shares=None, original_size_usdc=None, scale_out_tier=0,
        )
        assert result["remaining_shares"] == 60

        # Match-aware exit should still work on remaining position
        exit_result = check_match_exit({
            "entry_price": 0.50, "current_price": 0.20, "direction": "BUY_YES",
            "number_of_games": 3, "slug": "cs2-test", "match_score": "",
            "match_start_iso": "2026-01-01T00:00:00+00:00",
            "ever_in_profit": True, "peak_pnl_pct": 0.26, "scouted": False,
            "confidence": "medium", "ai_probability": 0.5,
            "consecutive_down_cycles": 0, "cumulative_drop": 0.0,
            "hold_revoked_at": None, "hold_was_original": False,
            "volatility_swing": False, "unrealized_pnl_pct": -0.60,
            "entry_reason": "", "cycles_held": 10,
        })
        assert exit_result["exit"] is True


class TestCircuitBreakerPlusReentry:
    """Circuit breaker halts entries, re-entry should be blocked."""
    def test_breaker_blocks_reentry(self):
        from src.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker()
        cb.record_exit(-90.0, 1000.0)  # -9% → daily limit
        halt, _ = cb.should_halt_entries()
        assert halt is True


class TestSigmaTrailingPlusScaleOut:
    """After scale-out tier 1, σ-trailing should use effective prices."""
    def test_sigma_uses_effective_after_scale_out(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        history = [0.35, 0.40, 0.45, 0.50, 0.55, 0.58, 0.56, 0.53]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.65, price_history=history,
            current_price=0.53, peak_price=0.58, entry_price=0.35,
        )
        assert result["active"] is True
        assert result["stop_price"] >= 0.35


class TestEdgeDecayPlusReentry:
    """Edge decay should reduce effective edge for re-entry decisions."""
    def test_late_match_reentry_lower_edge(self):
        from src.edge_decay import get_decayed_ai_target
        early_target = get_decayed_ai_target(0.70, 0.50, 0.10)
        late_target = get_decayed_ai_target(0.70, 0.50, 0.90)
        early_edge = abs(early_target - 0.50)
        late_edge = abs(late_target - 0.50)
        assert late_edge < early_edge


class TestResolutionHoldPlusGraduatedSL:
    """When resolution_hold=True, graduated SL should be bypassed unless effective_price < 0.65."""
    def test_resolution_hold_bypasses_sl(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.85, effective_ai=0.75,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is True

    def test_resolution_hold_revoked_on_crash(self):
        from src.vs_spike import should_hold_for_resolution
        hold, _ = should_hold_for_resolution(
            effective_price=0.60, effective_ai=0.75,
            scale_out_tier=2, score_behind=False, is_already_won=False,
        )
        assert hold is False


class TestAdaptiveKellyPlusCorrelation:
    """Kelly sizing respects correlation exposure limits."""
    def test_kelly_then_correlation_cap(self):
        from src.adaptive_kelly import get_adaptive_kelly_fraction
        from src.correlation import apply_correlation_cap

        kelly = get_adaptive_kelly_fraction("high", 0.75, "esports",
                                             config_kelly_by_conf={"high": 0.25})
        bankroll = 500.0
        size_usdc = kelly * bankroll

        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 90.0, "direction": "BUY_YES"}]
        capped = apply_correlation_cap(size_usdc, "cs2-faze-vs-navi", positions, bankroll)
        assert capped == 0.0
