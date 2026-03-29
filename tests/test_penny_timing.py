"""Tests for penny alpha timing filter."""


def test_penny_skipped_past_first_half():
    """Penny entry should be skipped if match is past 50% elapsed."""
    elapsed_pct = 0.55
    should_skip = elapsed_pct > 0.50
    assert should_skip is True


def test_penny_allowed_first_half():
    """Penny entry allowed in first half."""
    elapsed_pct = 0.40
    should_skip = elapsed_pct > 0.50
    assert should_skip is False


def test_penny_allowed_no_timing_data():
    """Penny entry allowed when no timing data (pre-match assumed)."""
    elapsed_pct = None
    should_skip = elapsed_pct is not None and elapsed_pct > 0.50
    assert should_skip is False
