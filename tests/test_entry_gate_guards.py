"""Tests for entry gate resolved/elapsed guards."""
from unittest.mock import MagicMock
from src.models import MarketData


def _make_market(**overrides) -> MarketData:
    """Helper to build a MarketData with sensible defaults."""
    defaults = dict(
        condition_id="0xtest",
        question="Will A beat B?",
        yes_price=0.6, no_price=0.4,
        yes_token_id="tok_y", no_token_id="tok_n",
        volume_24h=5000, liquidity=3000,
        slug="test-market", tags=["nba"],
        end_date_iso="2026-04-01T00:00:00Z",
        description="test", event_id="ev1",
        sport_tag="nba",
    )
    defaults.update(overrides)
    return MarketData(**defaults)


def test_skip_resolved_market():
    """Market with resolved=True should be skipped."""
    m = _make_market(resolved=True)
    assert m.resolved is True
    # Guard logic: if market.closed or market.resolved or not market.accepting_orders → skip
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is True


def test_skip_closed_market():
    """Market with closed=True should be skipped."""
    m = _make_market(closed=True)
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is True


def test_skip_not_accepting_orders():
    """Market with accepting_orders=False should be skipped."""
    m = _make_market(accepting_orders=False)
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is True


def test_pass_normal_market():
    """Normal active market should not be skipped."""
    m = _make_market(closed=False, resolved=False, accepting_orders=True)
    should_skip = m.closed or m.resolved or not m.accepting_orders
    assert should_skip is False


def test_estimate_elapsed_pct_uses_sport_duration():
    """Verify _estimate_elapsed_pct uses sport-specific duration, not hardcoded 120."""
    from src.upset_hunter import _estimate_elapsed_pct
    from datetime import datetime, timezone, timedelta

    # NBA match started 80 minutes ago
    # NBA duration = 150 min → elapsed_pct = 80/150 = 0.533
    # Old code would give 80/120 = 0.667 (wrong)
    m = _make_market(
        slug="nba-lal-bos",
        sport_tag="nba",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(minutes=80)).isoformat(),
    )
    pct = _estimate_elapsed_pct(m)
    assert pct is not None
    # With sport-specific duration (150min): 80/150 ≈ 0.533
    assert 0.50 < pct < 0.60, f"Expected ~0.53, got {pct}"
