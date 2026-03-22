# tests/test_scale_out.py
import pytest


class TestCheckScaleOut:
    def test_tier1_at_25pct(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.26, volatility_swing=False)
        assert result is not None
        assert result["tier"] == "tier1_risk_free"
        assert result["sell_pct"] == 0.40

    def test_no_trigger_below_threshold(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.20, volatility_swing=False)
        assert result is None

    def test_tier2_at_50pct(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=1, unrealized_pnl_pct=0.55, volatility_swing=False)
        assert result is not None
        assert result["tier"] == "tier2_profit_lock"

    def test_vs_positions_skipped(self):
        from src.scale_out import check_scale_out
        result = check_scale_out(scale_out_tier=0, unrealized_pnl_pct=0.50, volatility_swing=True)
        assert result is None


class TestApplyPartialExit:
    def test_buy_yes_pnl_correct(self):
        from src.scale_out import apply_partial_exit
        # Entry: 100 shares at 0.45, size_usdc=45. Sell 40 shares at 0.65.
        result = apply_partial_exit(
            shares=100, size_usdc=45.0, entry_price=0.45, direction="BUY_YES",
            shares_sold=40, fill_price=0.65, tier="tier1_risk_free",
            original_shares=None, original_size_usdc=None, scale_out_tier=0,
        )
        assert result["status"] == "OK"
        assert result["remaining_shares"] == 60
        assert abs(result["remaining_size_usdc"] - 27.0) < 0.01  # 45 * (1 - 40/100)
        assert result["realized_pnl"] > 0  # 40*0.65 - 45*(40/100) = 26 - 18 = 8

    def test_buy_no_pnl_correct(self):
        from src.scale_out import apply_partial_exit
        # BUY_NO: 100 shares at YES=0.65 (eff=0.35), size_usdc=35. Sell 40 at YES=0.30.
        result = apply_partial_exit(
            shares=100, size_usdc=35.0, entry_price=0.65, direction="BUY_NO",
            shares_sold=40, fill_price=0.30, tier="tier1_risk_free",
            original_shares=None, original_size_usdc=None, scale_out_tier=0,
        )
        # proceeds = 40 * (1 - 0.30) = 28. cost_basis_sold = 35 * (40/100) = 14. pnl = 14.
        assert result["realized_pnl"] == 14.0

    def test_dust_closes_remainder(self):
        from src.scale_out import apply_partial_exit
        result = apply_partial_exit(
            shares=2, size_usdc=1.0, entry_price=0.50, direction="BUY_YES",
            shares_sold=1.5, fill_price=0.60, tier="tier2_profit_lock",
            original_shares=10, original_size_usdc=5.0, scale_out_tier=1,
        )
        assert result["status"] == "CLOSE_REMAINDER"
