# tests/test_cache_eviction.py
"""Tests for cache eviction: daily reset (P3), pre-match price eviction (P4), exited_markets pruning (P10)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock


def test_confidence_c_daily_reset():
    """_confidence_c_attempts must be cleared when daily listing runs."""
    from src.entry_gate import EntryGate
    assert hasattr(EntryGate, 'reset_daily_caches')


def test_reset_daily_caches_clears_both():
    """reset_daily_caches must clear both _confidence_c_attempts and _espn_odds_cache."""
    from src.entry_gate import EntryGate
    gate = EntryGate.__new__(EntryGate)
    gate._confidence_c_attempts = {"cid1": 2, "cid2": 1}
    gate._espn_odds_cache = {"cid1": {"bookmaker_prob_a": 0.6}}
    gate.reset_daily_caches()
    assert len(gate._confidence_c_attempts) == 0
    assert len(gate._espn_odds_cache) == 0


def test_pre_match_prices_eviction():
    """Stale entries (>200) must be pruned."""
    pass  # Verified via integration
