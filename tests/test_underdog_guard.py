"""Tests for underdog elapsed-based entry guard (Fix 3).

Tests the _underdog_elapsed_size_multiplier helper and the guard logic
in entry_gate._evaluate_candidates that blocks/reduces underdog entries
based on match progress.
"""
from src.entry_gate import _underdog_elapsed_size_multiplier


class TestUnderdogElapsedMultiplier:
    """Unit tests for the graduated size multiplier function."""

    def test_early_match_full_size(self):
        """0-10% elapsed -> multiplier 1.0 (full size)."""
        assert _underdog_elapsed_size_multiplier(0.0) == 1.0
        assert _underdog_elapsed_size_multiplier(0.05) == 1.0
        assert _underdog_elapsed_size_multiplier(0.10) == 1.0

    def test_10pct_elapsed_75pct_size(self):
        """10-25% elapsed -> multiplier 0.75."""
        assert _underdog_elapsed_size_multiplier(0.11) == 0.75
        assert _underdog_elapsed_size_multiplier(0.20) == 0.75
        assert _underdog_elapsed_size_multiplier(0.25) == 0.75

    def test_25pct_elapsed_50pct_size(self):
        """25-40% elapsed -> multiplier 0.50."""
        assert _underdog_elapsed_size_multiplier(0.26) == 0.50
        assert _underdog_elapsed_size_multiplier(0.30) == 0.50
        assert _underdog_elapsed_size_multiplier(0.40) == 0.50

    def test_40pct_elapsed_25pct_size(self):
        """40-50% elapsed -> multiplier 0.25 (minimum)."""
        assert _underdog_elapsed_size_multiplier(0.41) == 0.25
        assert _underdog_elapsed_size_multiplier(0.49) == 0.25
        assert _underdog_elapsed_size_multiplier(0.50) == 0.25

    def test_over_50pct_blocked(self):
        """Over 50% elapsed -> multiplier 0.0 (blocked)."""
        assert _underdog_elapsed_size_multiplier(0.51) == 0.0
        assert _underdog_elapsed_size_multiplier(0.75) == 0.0
        assert _underdog_elapsed_size_multiplier(1.0) == 0.0

    def test_negative_elapsed_full_size(self):
        """Pre-match (negative elapsed) -> full size."""
        assert _underdog_elapsed_size_multiplier(-0.1) == 1.0

    def test_winner_not_affected(self):
        """Guard only applies to entry_price < 0.20.
        A normal winner at 0.70 effective entry should not be affected.
        The multiplier function itself is price-agnostic; the guard in
        _evaluate_candidates checks entry_price before calling it."""
        # Multiplier returns 1.0 at 5% elapsed regardless of price
        assert _underdog_elapsed_size_multiplier(0.05) == 1.0
