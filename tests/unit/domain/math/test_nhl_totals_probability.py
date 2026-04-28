"""Hybrid totals probability wrapper tests."""
from __future__ import annotations

from src.domain.math.nhl_totals_probability import p_over_hybrid


_FAKE_TABLE = {
    "totals_over": {
        "3_4_300_5.5": {"p_over": 0.35, "n_games": 200},
        "3_5_600_5.5": None,
    }
}


def test_uses_empirical_when_available():
    p, src = p_over_hybrid(period=3, current_total=4, seconds_remaining=300, target_total=5.5, table=_FAKE_TABLE)
    assert p == 0.35
    assert src == "empirical"


def test_falls_back_when_target_not_in_table():
    p, src = p_over_hybrid(period=3, current_total=4, seconds_remaining=300, target_total=7.5, table=_FAKE_TABLE)
    assert 0.0 <= p <= 1.0
    assert src == "skellam_fallback"


def test_falls_back_when_entry_is_none():
    p, src = p_over_hybrid(period=3, current_total=5, seconds_remaining=600, target_total=5.5, table=_FAKE_TABLE)
    assert src == "skellam_fallback"


def test_seconds_bucketed_to_30s():
    p, src = p_over_hybrid(period=3, current_total=4, seconds_remaining=315, target_total=5.5, table=_FAKE_TABLE)
    assert p == 0.35
    assert src == "empirical"
