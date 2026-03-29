# tests/test_trailing_sigma.py
import pytest


class TestSigmaTrailing:
    def test_inactive_below_30pct_peak(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # Activation threshold is now 30% peak PnL
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.20, price_history=[0.50, 0.51, 0.50, 0.49, 0.50],
            current_price=0.50, peak_price=0.51, entry_price=0.48,
        )
        assert result["active"] is False

    def test_inactive_short_history(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.40, price_history=[0.50, 0.51],
            current_price=0.50, peak_price=0.55, entry_price=0.45,
        )
        assert result["active"] is False

    def test_wide_stop_low_peak(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # Low peak (35%, just above 30% threshold) → z=3.0 → wide stop
        history = [0.50, 0.51, 0.52, 0.51, 0.50, 0.52, 0.53, 0.54]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.35, price_history=history,
            current_price=0.52, peak_price=0.54, entry_price=0.50,
        )
        assert result["active"] is True
        assert result["z_score"] == 3.0
        assert result["triggered"] is False  # Wide stop, not triggered

    def test_tight_stop_high_peak(self):
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # High peak (85%) → z=1.5 → tight stop
        history = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.75, 0.70]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.85, price_history=history,
            current_price=0.65, peak_price=0.80, entry_price=0.50,
        )
        assert result["active"] is True
        assert result["z_score"] == 1.5

    def test_entry_price_floor(self):
        """Stop never goes below entry price."""
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # Very volatile → large sigma → stop would be below entry
        history = [0.50, 0.60, 0.50, 0.70, 0.50, 0.60]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.40, price_history=history,
            current_price=0.55, peak_price=0.70, entry_price=0.50,
        )
        assert result["stop_price"] >= 0.50

    def test_all_params_are_effective_prices(self):
        """For BUY_NO: caller passes effective prices. Function works identically."""
        from src.trailing_sigma import calculate_sigma_trailing_stop
        # BUY_NO: YES entry=0.65, effective_entry=0.35. Peak effective=0.60.
        history = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.58, 0.55]
        result = calculate_sigma_trailing_stop(
            peak_pnl_pct=0.70, price_history=history,
            current_price=0.55, peak_price=0.60, entry_price=0.35,
        )
        assert result["active"] is True
        assert result["stop_price"] >= 0.35  # Floor at effective entry
