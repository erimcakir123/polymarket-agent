# tests/test_reentry.py
import pytest
import tempfile
import os


class TestCanReenter:
    def test_profitable_exit_allowed(self):
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="take_profit", exit_price=0.60, current_price=0.50,
            ai_prob=0.70, direction="BUY_YES",
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is True

    def test_loss_exit_rejected(self):
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="stop_loss", exit_price=0.60, current_price=0.50,
            ai_prob=0.70, direction="BUY_YES",
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is False

    def test_buy_no_effective_prices(self):
        """BUY_NO at YES exit=0.25 (eff=0.75). YES now=0.35 (eff=0.65).
        Effective drop = (0.75-0.65)/0.75 = 13.3% > 5% min → allowed."""
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="take_profit", exit_price=0.25, current_price=0.35,
            ai_prob=0.30, direction="BUY_NO",  # effective_ai = 0.70
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is True

    def test_buy_no_low_ai_rejected(self):
        """BUY_NO with ai_prob=0.50 → effective_ai=0.50 < 0.60 → rejected."""
        from src.reentry import can_reenter
        ok, reason = can_reenter(
            exit_reason="take_profit", exit_price=0.25, current_price=0.35,
            ai_prob=0.50, direction="BUY_NO",
            score_info={"available": False}, elapsed_pct=0.30,
            slug="cs2-test", number_of_games=3,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is False

    def test_too_late_rejected(self):
        from src.reentry import can_reenter
        ok, _ = can_reenter(
            exit_reason="take_profit", exit_price=0.60, current_price=0.50,
            ai_prob=0.70, direction="BUY_YES",
            score_info={"available": False}, elapsed_pct=0.90,
            slug="lol-test", number_of_games=1,
            minutes_since_exit=10, daily_reentry_count=0, market_reentry_count=0,
        )
        assert ok is False  # LoL BO1 max_elapsed = 0.40


class TestBlacklistRules:
    def test_take_profit_is_reentry_type(self):
        from src.reentry import get_blacklist_rule
        btype, duration = get_blacklist_rule("take_profit", elapsed_pct=0.5)
        assert btype == "reentry"
        assert duration == 5

    def test_catastrophic_is_permanent(self):
        from src.reentry import get_blacklist_rule
        btype, duration = get_blacklist_rule("catastrophic_floor", elapsed_pct=0.5)
        assert btype == "permanent"

    def test_graduated_sl_dynamic_duration(self):
        from src.reentry import get_blacklist_rule
        btype, duration_early = get_blacklist_rule("graduated_sl", elapsed_pct=0.30)
        btype, duration_late = get_blacklist_rule("graduated_sl", elapsed_pct=0.90)
        assert duration_early < duration_late  # Early = shorter cooldown


class TestReentryDynamicParams:
    def test_moba_tight_elapsed(self):
        from src.reentry import get_reentry_max_elapsed
        assert get_reentry_max_elapsed("lol-test", 1) == 0.40

    def test_cs2_bo3_wider(self):
        from src.reentry import get_reentry_max_elapsed
        assert get_reentry_max_elapsed("cs2-test", 3) == 0.70

    def test_min_drop_cheap(self):
        from src.reentry import get_min_reentry_drop
        assert get_min_reentry_drop(0.20) == 0.15

    def test_min_drop_expensive(self):
        from src.reentry import get_min_reentry_drop
        assert get_min_reentry_drop(0.80) == 0.05

    def test_size_multiplier_high_ai(self):
        from src.reentry import get_reentry_size_multiplier
        mult = get_reentry_size_multiplier(0.20, "BUY_NO", {"available": False}, 0.40)
        # effective_ai = 0.80 → +0.25 bonus
        assert mult >= 0.70


class TestBlacklist:
    @pytest.fixture
    def bl(self, tmp_path):
        from src.reentry import Blacklist
        path = str(tmp_path / "blacklist.json")
        return Blacklist(path=path)

    def test_permanent_always_blocked(self, bl):
        bl.add("cond-1", "catastrophic_floor", "permanent", expires_at_cycle=None)
        assert bl.is_blocked("cond-1", current_cycle=0) is True
        assert bl.is_blocked("cond-1", current_cycle=999999) is True

    def test_timed_blocked_before_expiry(self, bl):
        bl.add("cond-2", "stop_loss", "timed", expires_at_cycle=100)
        assert bl.is_blocked("cond-2", current_cycle=50) is True
        assert bl.is_blocked("cond-2", current_cycle=99) is True

    def test_timed_unblocked_after_expiry(self, bl):
        bl.add("cond-2", "stop_loss", "timed", expires_at_cycle=100)
        assert bl.is_blocked("cond-2", current_cycle=100) is False
        assert bl.is_blocked("cond-2", current_cycle=200) is False

    def test_reentry_blocked_before_expiry(self, bl):
        bl.add("cond-3", "take_profit", "reentry", expires_at_cycle=50)
        assert bl.is_blocked("cond-3", current_cycle=30) is True

    def test_reentry_unblocked_after_expiry(self, bl):
        bl.add("cond-3", "take_profit", "reentry", expires_at_cycle=50)
        assert bl.is_blocked("cond-3", current_cycle=50) is False
        assert bl.is_blocked("cond-3", current_cycle=51) is False

    def test_cleanup_removes_expired_keeps_permanent(self, bl):
        bl.add("perm-1", "catastrophic_floor", "permanent", expires_at_cycle=None)
        bl.add("timed-1", "stop_loss", "timed", expires_at_cycle=10)
        bl.add("timed-2", "graduated_sl", "timed", expires_at_cycle=20)
        bl.cleanup(current_cycle=15)
        # timed-1 expired (10 < 15), timed-2 still active, perm-1 permanent
        assert bl.get_entry("perm-1") is not None
        assert bl.get_entry("timed-1") is None
        assert bl.get_entry("timed-2") is not None

    def test_get_entry_returns_correct_or_none(self, bl):
        bl.add("cond-5", "take_profit", "reentry", expires_at_cycle=50,
               exit_data={"price": 0.60})
        entry = bl.get_entry("cond-5")
        assert entry is not None
        assert entry.condition_id == "cond-5"
        assert entry.exit_reason == "take_profit"
        assert entry.exit_data == {"price": 0.60}
        assert bl.get_entry("nonexistent") is None


class TestSnowballBan:
    def test_moba_behind_banned(self):
        from src.reentry import is_snowball_banned
        banned, _ = is_snowball_banned("lol-test", 0.40, {"available": True, "map_diff": -1})
        assert banned is True

    def test_cs2_behind_not_banned(self):
        from src.reentry import is_snowball_banned
        banned, _ = is_snowball_banned("cs2-test", 0.40, {"available": True, "map_diff": -1})
        assert banned is False

    def test_moba_early_not_banned(self):
        from src.reentry import is_snowball_banned
        banned, _ = is_snowball_banned("lol-test", 0.20, {"available": True, "map_diff": -1})
        assert banned is False


class TestGracePeriod:
    def test_reentry_gets_grace(self):
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 3,
            "entry_price": 0.50, "current_price": 0.49, "direction": "BUY_YES",
        }) is True

    def test_grace_expired(self):
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 10,
            "entry_price": 0.50, "current_price": 0.49, "direction": "BUY_YES",
        }) is False

    def test_grace_revoked_on_drop(self):
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 2,
            "entry_price": 0.50, "current_price": 0.46, "direction": "BUY_YES",
        }) is False  # 4c drop > 3c max

    def test_buy_no_grace_direction(self):
        """BUY_NO: YES price rising = bad for us = should revoke grace."""
        from src.reentry import is_grace_period_active
        assert is_grace_period_active({
            "entry_reason": "re_entry_after_profit", "cycles_held": 2,
            "entry_price": 0.60, "current_price": 0.64, "direction": "BUY_NO",
        }) is False  # eff drop = (0.64-0.60) = 4c > 3c


class TestScoreReversal:
    def test_convincing_lead_overrides(self):
        from src.reentry import qualifies_for_score_reversal_reentry, BlacklistEntry
        entry = BlacklistEntry("cid1", "graduated_sl", "timed", 100, {})
        ok, _ = qualifies_for_score_reversal_reentry(
            entry, {"available": True, "map_diff": 2}, elapsed_pct=0.50, current_cycle=50,
        )
        assert ok is True

    def test_single_map_lead_not_enough(self):
        from src.reentry import qualifies_for_score_reversal_reentry, BlacklistEntry
        entry = BlacklistEntry("cid1", "graduated_sl", "timed", 100, {})
        ok, _ = qualifies_for_score_reversal_reentry(
            entry, {"available": True, "map_diff": 1}, elapsed_pct=0.50, current_cycle=50,
        )
        assert ok is False

    def test_permanent_blacklist_not_overrideable(self):
        from src.reentry import qualifies_for_score_reversal_reentry, BlacklistEntry
        entry = BlacklistEntry("cid1", "catastrophic_floor", "permanent", None, {})
        ok, _ = qualifies_for_score_reversal_reentry(
            entry, {"available": True, "map_diff": 3}, elapsed_pct=0.50, current_cycle=50,
        )
        assert ok is False
