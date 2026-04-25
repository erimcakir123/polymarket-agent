"""sports_market_type, spread_line, total_line, total_side field testleri."""
from __future__ import annotations

from src.models.signal import Signal
from src.models.position import Position
from src.models.enums import Direction, EntryReason


def _make_signal(**kw) -> Signal:
    base = dict(
        condition_id="cid",
        direction=Direction.BUY_YES,
        anchor_probability=0.65,
        market_price=0.50,
        confidence="A",
        size_usdc=50.0,
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=0.65,
    )
    base.update(kw)
    return Signal(**base)


def _make_position(**kw) -> Position:
    base = dict(
        condition_id="cid",
        token_id="tok",
        direction="BUY_YES",
        entry_price=0.50,
        size_usdc=50.0,
        shares=100.0,
        current_price=0.50,
        anchor_probability=0.65,
    )
    base.update(kw)
    return Position(**base)


# ── Signal ───────────────────────────────────────────────────────
def test_signal_sports_market_type_default():
    assert _make_signal().sports_market_type == ""


def test_signal_spread_line_default():
    assert _make_signal().spread_line is None


def test_signal_total_line_default():
    assert _make_signal().total_line is None


def test_signal_total_side_default():
    assert _make_signal().total_side is None


def test_signal_spread_fields_set():
    sig = _make_signal(sports_market_type="spreads", spread_line=5.5)
    assert sig.sports_market_type == "spreads"
    assert sig.spread_line == 5.5


def test_signal_totals_fields_set():
    sig = _make_signal(sports_market_type="totals", total_line=220.5, total_side="over")
    assert sig.total_line == 220.5
    assert sig.total_side == "over"


# ── Position ─────────────────────────────────────────────────────
def test_position_sports_market_type_default():
    assert _make_position().sports_market_type == ""


def test_position_spread_line_default():
    assert _make_position().spread_line is None


def test_position_total_line_default():
    assert _make_position().total_line is None


def test_position_total_side_default():
    assert _make_position().total_side is None


def test_position_spread_fields_set():
    pos = _make_position(sports_market_type="spreads", spread_line=7.5)
    assert pos.sports_market_type == "spreads"
    assert pos.spread_line == 7.5


def test_position_totals_fields_set():
    pos = _make_position(sports_market_type="totals", total_line=215.0, total_side="under")
    assert pos.total_line == 215.0
    assert pos.total_side == "under"
