"""Tests for monitor.evaluate() NHL routing — TDD §3C.

Verify that NHL positions route through check_nhl_exit (NHL_* reasons)
and non-NHL positions keep the generic near_resolve / scale_out reasons.
"""
from __future__ import annotations

from src.models.enums import ExitReason
from src.models.position import Position
from src.strategy.exit.monitor import evaluate


def _make_pos(sport_tag: str, bid: float, entry: float = 0.45,
              current: float | None = None, scaled_out_50: bool = False) -> Position:
    cp = current if current is not None else bid
    return Position(
        condition_id=f"test-{sport_tag}-cid",
        token_id=f"test-{sport_tag}-token",
        direction="BUY_YES",
        entry_price=entry,
        current_price=cp,
        bid_price=bid,
        size_usdc=10.0,
        shares=20.0,
        anchor_probability=0.60,
        sport_tag=sport_tag,
        scaled_out_50=scaled_out_50,
    )


# ---------------------------------------------------------------------------
# 1. NHL position → NHL_NEAR_RESOLVE (not generic NEAR_RESOLVE)
# ---------------------------------------------------------------------------
def test_nhl_position_returns_nhl_near_resolve_not_generic():
    pos = _make_pos("nhl", bid=0.95, entry=0.45, current=0.95)
    score_info = dict(
        available=True, period=3, clock_seconds=300,
        our_score=2, opp_score=1, is_shootout=False,
    )
    result = evaluate(pos, score_info=score_info, nhl_exit_cfg=None, nhl_wp_table={})
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.NHL_NEAR_RESOLVE
    assert result.exit_signal.reason != ExitReason.NEAR_RESOLVE


# ---------------------------------------------------------------------------
# 2. NBA position → generic NEAR_RESOLVE (not NHL routing)
# ---------------------------------------------------------------------------
def test_nba_position_gets_generic_near_resolve():
    pos = _make_pos("nba", bid=0.95, entry=0.45, current=0.95)
    # NBA score_info.available=False → NBA score exit skipped; generic near-resolve fires
    score_info = {"available": False}
    result = evaluate(pos, score_info=score_info)
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.NEAR_RESOLVE


# ---------------------------------------------------------------------------
# 3. NHL position → NHL_SCALE_OUT (not generic SCALE_OUT)
# ---------------------------------------------------------------------------
def test_nhl_position_returns_nhl_scale_out_not_generic():
    pos = _make_pos("nhl", bid=0.87, entry=0.45, current=0.87, scaled_out_50=False)
    score_info = dict(
        available=True, period=2, clock_seconds=600,
        our_score=1, opp_score=0, is_shootout=False,
    )
    result = evaluate(pos, score_info=score_info, nhl_exit_cfg=None, nhl_wp_table={})
    assert result.exit_signal is not None
    assert result.exit_signal.reason == ExitReason.NHL_SCALE_OUT
    assert result.exit_signal.reason != ExitReason.SCALE_OUT
