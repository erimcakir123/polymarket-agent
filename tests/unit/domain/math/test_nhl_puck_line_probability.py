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


def test_period_boundary_p2_end_normalizes_to_p3():
    """End of P2 (period=2, sec=1200) hits P3 namespace key 3_X_1200.

    Bug repro: bos-buf 2026-04-28 (Sabres -1.5) ve mon-tb 2026-04-29 (Lightning
    -1.5) end-of-P2 tied'da predictive_dead fire etmedi. Dispatch period=2 +
    sec=1200 ile çağırıyor, tablo "2_0_1200" anahtarına sahip değil (P2 keys
    1230'dan başlar). Veri "3_0_1200" altında (P3 just started). Lookup bu
    boundary'i normalize etmeli.
    """
    table = {"puck_line_cover": {"3_0_1200": {"p_favorite_covers": 0.17, "n_games": 890}}}
    p, src = p_favorite_covers_hybrid(period=2, current_margin=0, seconds_remaining=1200, table=table)
    assert src == "empirical"
    assert p == 0.17


def test_period_boundary_p1_end_normalizes_to_p2():
    """End of P1 (period=1, sec=2400) hits P2 namespace key 2_X_2400."""
    table = {"puck_line_cover": {"2_0_2400": {"p_favorite_covers": 0.30, "n_games": 100}}}
    p, src = p_favorite_covers_hybrid(period=1, current_margin=0, seconds_remaining=2400, table=table)
    assert src == "empirical"
    assert p == 0.30


def test_period_boundary_caller_period_inconsistent_uses_seconds():
    """Eğer caller period=2 ile sec_remaining=300 verirse (mantıken P3 demek),
    lookup time_bucket'tan türetilen P3 namespace'ini kullanmalı."""
    table = {"puck_line_cover": {"3_1_300": {"p_favorite_covers": 0.55, "n_games": 200}}}
    p, src = p_favorite_covers_hybrid(period=2, current_margin=1, seconds_remaining=300, table=table)
    assert src == "empirical"
    assert p == 0.55
