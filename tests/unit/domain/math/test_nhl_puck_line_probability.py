"""Hybrid puck line probability wrapper tests."""
from __future__ import annotations

from src.domain.math.nhl_puck_line_probability import p_favorite_covers_hybrid


_FAKE_TABLE = {
    "puck_line_cover": {
        "3_1_300": {"p_favorite_covers": 0.55, "n_games": 200, "ci_low": 0.50, "ci_high": 0.60},
        "3_-2_600": None,  # insufficient sample
    }
}


def test_uses_empirical_when_available():
    p, src = p_favorite_covers_hybrid(period=3, current_margin=1, seconds_remaining=300, table=_FAKE_TABLE)
    assert p == 0.55
    assert src == "empirical"


def test_falls_back_to_skellam_when_table_missing(monkeypatch):
    p, src = p_favorite_covers_hybrid(period=3, current_margin=1, seconds_remaining=999, table=_FAKE_TABLE)
    assert 0.0 <= p <= 1.0
    assert src == "skellam_fallback"


def test_falls_back_when_table_entry_is_none():
    p, src = p_favorite_covers_hybrid(period=3, current_margin=-2, seconds_remaining=600, table=_FAKE_TABLE)
    assert 0.0 <= p <= 1.0
    assert src == "skellam_fallback"


def test_seconds_bucketed_to_30s():
    p, src = p_favorite_covers_hybrid(period=3, current_margin=1, seconds_remaining=315, table=_FAKE_TABLE)
    assert p == 0.55
    assert src == "empirical"


def test_margin_clamped_to_5():
    table = {"puck_line_cover": {"3_5_600": {"p_favorite_covers": 0.95, "n_games": 50}}}
    p, src = p_favorite_covers_hybrid(period=3, current_margin=8, seconds_remaining=600, table=table)
    assert src == "empirical"
    assert p == 0.95
