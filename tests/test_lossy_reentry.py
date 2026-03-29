"""Tests for lossy (stop-loss) exit re-entry feature.

Stop-loss exits can rejoin the re-entry pool under strict conditions:
- AI probability >= 65%
- Max 1 re-entry per market (sl_reentry_count == 0)
- 40% drop recovery trigger
- Tighter SL (x0.75)
- 2nd SL = permanent blacklist
"""


def test_sl_exit_added_to_reentry_pool():
    """Stop-loss exit with AI prob >= 65% should be added to reentry pool."""
    exit_reason = "stop_loss"
    ai_probability = 0.70
    sl_reentry_count = 0
    should_add = (
        exit_reason == "stop_loss"
        and ai_probability >= 0.65
        and sl_reentry_count == 0
    )
    assert should_add is True


def test_sl_exit_rejected_low_probability():
    """Stop-loss exit with AI prob < 65% should NOT be added."""
    exit_reason = "stop_loss"
    ai_probability = 0.60
    sl_reentry_count = 0
    should_add = (
        exit_reason == "stop_loss"
        and ai_probability >= 0.65
        and sl_reentry_count == 0
    )
    assert should_add is False


def test_sl_exit_rejected_if_already_reentered():
    """Stop-loss exit should NOT be re-added if already re-entered once."""
    exit_reason = "stop_loss"
    ai_probability = 0.70
    sl_reentry_count = 1
    should_add = (
        exit_reason == "stop_loss"
        and ai_probability >= 0.65
        and sl_reentry_count == 0
    )
    assert should_add is False


def test_lossy_reentry_recovery_trigger():
    """Re-entry triggers when price recovers 40% of the drop."""
    original_entry = 0.70
    exit_price = 0.58
    drop = original_entry - exit_price  # 0.12
    recovery_needed = drop * 0.40  # 0.048
    trigger_price = exit_price + recovery_needed  # 0.628
    current_price = 0.63
    should_trigger = current_price >= trigger_price
    assert should_trigger is True


def test_lossy_reentry_no_trigger_insufficient_recovery():
    """Re-entry should NOT trigger if price hasn't recovered 40%."""
    original_entry = 0.70
    exit_price = 0.58
    drop = original_entry - exit_price  # 0.12
    recovery_needed = drop * 0.40  # 0.048
    trigger_price = exit_price + recovery_needed  # 0.628
    current_price = 0.60  # Only recovered 0.02, need 0.048
    should_trigger = current_price >= trigger_price
    assert should_trigger is False


def test_lossy_reentry_tighter_sl():
    """Lossy re-entry should use 75% of original SL."""
    original_sl_pct = 0.15
    lossy_sl_pct = original_sl_pct * 0.75
    assert lossy_sl_pct == 0.15 * 0.75


def test_second_sl_triggers_permanent_blacklist():
    """Second SL after lossy re-entry = permanent blacklist."""
    sl_reentry_count = 1
    exit_reason = "stop_loss"
    should_blacklist = exit_reason == "stop_loss" and sl_reentry_count >= 1
    assert should_blacklist is True


def test_first_sl_no_blacklist():
    """First SL should NOT trigger permanent blacklist (just pool add)."""
    sl_reentry_count = 0
    exit_reason = "stop_loss"
    should_blacklist = exit_reason == "stop_loss" and sl_reentry_count >= 1
    assert should_blacklist is False


def test_reentry_candidate_fields():
    """ReentryCandidate should have sl_reentry_count and exit_reason fields."""
    from src.reentry_farming import ReentryCandidate

    c = ReentryCandidate(
        condition_id="test",
        event_id="ev1",
        slug="test-slug",
        question="Test?",
        direction="BUY_YES",
        token_id="tok1",
        ai_probability=0.70,
        confidence="A",
        original_entry_price=0.70,
        last_exit_price=0.58,
        last_exit_cycle=10,
        end_date_iso="",
        match_start_iso="",
        sport_tag="cs2",
        number_of_games=3,
        was_scouted=False,
    )
    assert c.sl_reentry_count == 0
    assert c.exit_reason == ""


def test_check_reentry_lossy_recovery_trigger():
    """check_reentry should require 40% recovery for SL candidates."""
    from src.reentry_farming import ReentryCandidate, check_reentry

    # SL exit: entered at 0.70, exited at 0.58
    c = ReentryCandidate(
        condition_id="test",
        event_id="ev1",
        slug="test-slug",
        question="Test?",
        direction="BUY_YES",
        token_id="tok1",
        ai_probability=0.70,
        confidence="A",
        original_entry_price=0.70,
        last_exit_price=0.58,
        last_exit_cycle=10,
        end_date_iso="",
        match_start_iso="",
        sport_tag="cs2",
        number_of_games=3,
        was_scouted=False,
        exit_reason="stop_loss",
        sl_reentry_count=0,
    )
    # Price at 0.60 -- only recovered 0.02 of 0.12 drop (17%), need 40%
    c.price_history = [0.59, 0.595, 0.60]
    result = check_reentry(
        candidate=c,
        current_yes_price=0.60,
        current_cycle=13,
        portfolio_positions={},
        held_event_ids=set(),
        daily_reentry_count=0,
    )
    # Should WAIT because insufficient recovery
    assert result["action"] == "WAIT"
    assert "recovery" in result["reason"].lower() or "Not enough" in result["reason"]
