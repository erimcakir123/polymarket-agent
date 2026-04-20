"""Signal için birim testler."""
from __future__ import annotations

import pytest

from src.models.enums import Direction, EntryReason
from src.models.signal import Signal


def _valid(**overrides) -> Signal:
    base = dict(
        condition_id="0x1",
        direction=Direction.BUY_YES,
        anchor_probability=0.60,
        market_price=0.50,
        confidence="B",
        size_usdc=40.0,
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=0.58,
    )
    base.update(overrides)
    return Signal(**base)


def test_signal_valid() -> None:
    s = _valid()
    assert s.direction == Direction.BUY_YES
    assert s.entry_reason == EntryReason.NORMAL


def test_signal_anchor_probability_out_of_range_raises() -> None:
    with pytest.raises(Exception):
        _valid(anchor_probability=0.0)


def test_signal_default_sport_tag_and_event_id() -> None:
    s = _valid()
    assert s.sport_tag == ""
    assert s.event_id == ""
