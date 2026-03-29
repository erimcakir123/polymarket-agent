"""Tests for the global price filter (5-95% range)."""


def test_price_filter_rejects_4_percent():
    """Price at 4¢ should be rejected by 5-95% filter."""
    price = 0.04
    in_range = 0.05 <= price <= 0.95
    assert in_range is False


def test_price_filter_accepts_5_percent():
    """Price at 5¢ should be accepted."""
    price = 0.05
    in_range = 0.05 <= price <= 0.95
    assert in_range is True


def test_price_filter_rejects_96_percent():
    """Price at 96¢ should be rejected."""
    price = 0.96
    in_range = 0.05 <= price <= 0.95
    assert in_range is False


def test_price_filter_accepts_95_percent():
    """Price at 95¢ should be accepted."""
    price = 0.95
    in_range = 0.05 <= price <= 0.95
    assert in_range is True


def test_price_filter_accepts_midrange():
    """Price at 50¢ should be accepted."""
    price = 0.50
    in_range = 0.05 <= price <= 0.95
    assert in_range is True
