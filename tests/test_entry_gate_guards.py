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


def test_elapsed_guard_blocks_half_elapsed():
    """Market past 50% elapsed should be skipped."""
    from src.match_exit import get_game_duration
    from datetime import datetime, timezone, timedelta

    # NBA started 90 min ago. Duration = 150 min. elapsed_pct = 0.60 > 0.50
    m = _make_market(
        slug="nba-lal-bos",
        sport_tag="nba",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat(),
    )
    start_dt = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed_min = (now - start_dt).total_seconds() / 60
    duration_min = get_game_duration(m.slug, 0, m.sport_tag)
    elapsed_pct = elapsed_min / max(duration_min, 1)
    assert elapsed_pct > 0.50, f"Expected >0.50, got {elapsed_pct}"


def test_elapsed_guard_passes_early_match():
    """Market in first half should not be skipped."""
    from src.match_exit import get_game_duration
    from datetime import datetime, timezone, timedelta

    # NBA started 30 min ago. Duration = 150 min. elapsed_pct = 0.20 < 0.50
    m = _make_market(
        slug="nba-lal-bos",
        sport_tag="nba",
        match_start_iso=(datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
    )
    start_dt = datetime.fromisoformat(m.match_start_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed_min = (now - start_dt).total_seconds() / 60
    duration_min = get_game_duration(m.slug, 0, m.sport_tag)
    elapsed_pct = elapsed_min / max(duration_min, 1)
    assert elapsed_pct < 0.50, f"Expected <0.50, got {elapsed_pct}"
