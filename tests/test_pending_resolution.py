"""Tests for pending resolution exit logic (Fix 4).

Rules:
- pending + profitable -> HOLD (skip TP and match_exit, wait for oracle)
- pending + losing -> evaluate normally (SL, match_exit can fire)
- pending + losing + SL trigger -> EXIT
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.models import Position
from src.portfolio import Portfolio


def _make_portfolio_with_position(**overrides) -> tuple[Portfolio, str]:
    """Create a Portfolio with one position. Return (portfolio, condition_id)."""
    cid = overrides.pop("condition_id", "0xpending")
    defaults = dict(
        condition_id=cid,
        token_id="tok_y",
        direction="BUY_YES",
        entry_price=0.60,
        size_usdc=10.0,
        shares=16.67,
        current_price=0.60,
        slug="test-pending-market",
        confidence="B+",
        ai_probability=0.65,
    )
    defaults.update(overrides)

    p = Portfolio.__new__(Portfolio)
    p.positions = {}
    p._initial_bankroll = 1000
    p.bankroll = 990
    p.high_water_mark = 1000
    p.realized_pnl = 0.0
    p.realized_wins = 0
    p.realized_losses = 0
    pos = Position(**defaults)
    p.positions[cid] = pos
    return p, cid


def test_pending_in_profit_holds_match_exit():
    """Pending + profitable position should NOT trigger match-aware exit."""
    port, cid = _make_portfolio_with_position(
        entry_price=0.30,
        current_price=0.95,
        shares=33.33,
        pending_resolution=True,
        match_start_iso=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        sport_tag="nba",
    )
    pos = port.positions[cid]
    assert pos.unrealized_pnl_pct > 0

    results = port.check_match_aware_exits()
    exit_results = [r for r in results if r.get("exit")]
    assert not any(r["condition_id"] == cid for r in exit_results), \
        "Pending + profitable should NOT trigger match exit"


def test_pending_in_loss_evaluates_sl():
    """Pending + losing position should still trigger stop-loss."""
    port, cid = _make_portfolio_with_position(
        entry_price=0.70,
        current_price=0.05,  # massive loss, marked pending
        shares=14.29,  # size=10, entry=0.70
        pending_resolution=True,
    )
    pos = port.positions[cid]
    assert pos.unrealized_pnl_pct < 0, f"Expected loss, got {pos.unrealized_pnl_pct}"

    # Stop loss should fire (PnL is ~-93%, any SL threshold triggers)
    triggered = port.check_stop_losses(stop_loss_pct=0.30)
    assert cid in triggered, "Pending + losing should trigger SL"


def test_pending_loss_evaluates_match_exit():
    """Pending + losing position should go through match-aware exit check."""
    port, cid = _make_portfolio_with_position(
        entry_price=0.70,
        current_price=0.05,
        shares=14.29,
        pending_resolution=True,
        match_start_iso=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        slug="nba-lal-bos",
        sport_tag="nba",
    )
    pos = port.positions[cid]
    assert pos.unrealized_pnl_pct < 0

    # Match-aware exit should evaluate (not skip) this position
    results = port.check_match_aware_exits()
    # Graduated SL should fire (PnL -92.9% far below max_loss tier)
    exit_results = [r for r in results if r.get("exit") and r["condition_id"] == cid]
    assert len(exit_results) > 0, "Pending + losing should be evaluated by match exit"


