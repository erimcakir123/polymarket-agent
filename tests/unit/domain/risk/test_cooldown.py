"""cooldown.py için birim testler."""
from __future__ import annotations

from src.domain.risk.cooldown import CooldownTracker


def test_fresh_tracker_inactive() -> None:
    tr = CooldownTracker()
    assert tr.is_active() is False


def test_losses_below_threshold_no_cooldown() -> None:
    tr = CooldownTracker(trigger_threshold=3, cooldown_cycles=2)
    tr.record_outcome(win=False)
    tr.record_outcome(win=False)
    tr.new_cycle()
    assert tr.is_active() is False


def test_threshold_hit_triggers_cooldown() -> None:
    tr = CooldownTracker(trigger_threshold=3, cooldown_cycles=2)
    for _ in range(3):
        tr.record_outcome(win=False)
    assert tr.state.cooldown_remaining == 2


def test_win_resets_consecutive_count() -> None:
    tr = CooldownTracker(trigger_threshold=3)
    tr.record_outcome(win=False)
    tr.record_outcome(win=False)
    tr.record_outcome(win=True)
    assert tr.state.consecutive_losses == 0


def test_cooldown_decrements_once_per_cycle() -> None:
    tr = CooldownTracker(trigger_threshold=3, cooldown_cycles=3)
    for _ in range(3):
        tr.record_outcome(win=False)
    # cycle 1
    tr.new_cycle()
    assert tr.is_active() is True
    assert tr.is_active() is True  # Same cycle, still active, no double decrement
    # cycle 2
    tr.new_cycle()
    assert tr.is_active() is True
    # cycle 3 — final decrement
    tr.new_cycle()
    result3 = tr.is_active()
    # cycle 4 — cooldown ends
    tr.new_cycle()
    assert tr.is_active() is False


def test_cooldown_expires() -> None:
    tr = CooldownTracker(trigger_threshold=3, cooldown_cycles=2)
    for _ in range(3):
        tr.record_outcome(win=False)
    tr.new_cycle()
    tr.is_active()  # decrement 1
    tr.new_cycle()
    tr.is_active()  # decrement 2
    tr.new_cycle()
    assert tr.is_active() is False
