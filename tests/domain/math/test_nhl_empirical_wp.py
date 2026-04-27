"""
Sanity tests for NHL empirical WP lookup against MoneyPuck 2022-25 table.

Skip gracefully if table missing.
"""
from __future__ import annotations

import pytest
from src.domain.math.nhl_empirical_wp import (
    leading_team_win_probability_empirical,
    trailing_team_win_probability_empirical,
    get_table_metadata,
    TABLE_PATH,
)

pytestmark = pytest.mark.skipif(
    not TABLE_PATH.exists(),
    reason="Run scripts/build_nhl_empirical_table.py first"
)


class TestMetadata:
    def test_metadata_loaded(self):
        meta = get_table_metadata()
        assert meta["total_games"] > 4000
        assert 2022 in meta["seasons"]
        assert 2024 in meta["seasons"]

    def test_avg_goals_per_game_modern(self):
        """2022-25 era: 5.8-6.6 G/mac combined."""
        meta = get_table_metadata()
        assert 5.8 < meta["league_avg_goals_per_game"] < 6.6


class TestSanityKeyPoints:
    def test_3_gol_p3_basi(self):
        """Beklenen %92-99. Gercek MoneyPuck: ~%96."""
        p = leading_team_win_probability_empirical(3, 3, 1200)
        assert p is not None
        assert 0.92 < p < 1.0, f"Got {p:.4f}"

    def test_2_gol_p3_basi(self):
        """Beklenen %85-95. Gercek: ~%89.6."""
        p = leading_team_win_probability_empirical(3, 2, 1200)
        assert p is not None
        assert 0.83 < p < 0.96, f"Got {p:.4f}"

    def test_1_gol_p3_basi(self):
        """Beklenen %70-82. Gercek: ~%74."""
        p = leading_team_win_probability_empirical(3, 1, 1200)
        assert p is not None
        assert 0.68 < p < 0.84, f"Got {p:.4f}"

    def test_1_gol_p3_mid(self):
        """Beklenen %78-88. Gercek: ~%80.8."""
        p = leading_team_win_probability_empirical(3, 1, 600)
        assert p is not None
        assert 0.76 < p < 0.90, f"Got {p:.4f}"

    def test_1_gol_last_5min(self):
        """Beklenen %85-92. Gercek: ~%86.3."""
        p = leading_team_win_probability_empirical(3, 1, 300)
        assert p is not None
        assert 0.83 < p < 0.94, f"Got {p:.4f}"

    def test_1_gol_last_minute(self):
        """Beklenen %85-95 (EN dahil). Gercek: ~%92.3."""
        p = leading_team_win_probability_empirical(3, 1, 60)
        assert p is not None
        assert 0.85 < p < 0.97, f"Got {p:.4f}"

    def test_2_gol_last_5min(self):
        """Beklenen %93-99. Gercek: ~%98.1."""
        p = leading_team_win_probability_empirical(3, 2, 300)
        assert p is not None
        assert 0.93 < p < 1.0, f"Got {p:.4f}"

    def test_2_gol_last_minute(self):
        """Beklenen %95-99. Gercek: ~%99.2."""
        p = leading_team_win_probability_empirical(3, 2, 60)
        assert p is not None
        assert 0.95 < p < 1.0, f"Got {p:.4f}"

    def test_tied_returns_coin_flip(self):
        assert leading_team_win_probability_empirical(3, 0, 600) == 0.5


class TestMonotonicity:
    def test_more_time_means_more_comeback_room(self):
        """Ayni deficit: daha fazla sure → leader p_win daha dusuk."""
        d = 2
        p_60 = leading_team_win_probability_empirical(3, d, 60)
        p_300 = leading_team_win_probability_empirical(3, d, 300)
        p_1200 = leading_team_win_probability_empirical(3, d, 1200)
        if None in (p_60, p_300, p_1200):
            pytest.skip("Insufficient data in some buckets")
        assert p_60 > p_300 > p_1200

    def test_bigger_lead_means_higher_p_win(self):
        """Ayni zaman: daha buyuk lead → leader p_win daha yuksek."""
        s = 600
        p1 = leading_team_win_probability_empirical(3, 1, s)
        p2 = leading_team_win_probability_empirical(3, 2, s)
        p3 = leading_team_win_probability_empirical(3, 3, s)
        if None in (p1, p2, p3):
            pytest.skip("Insufficient data")
        assert p1 < p2 < p3


class TestTrailingConsistency:
    def test_leading_plus_trailing_equals_one(self):
        for p, d, s in [(3, 1, 600), (3, 2, 1200), (2, 1, 1800)]:
            p_lead = leading_team_win_probability_empirical(p, d, s)
            p_trail = trailing_team_win_probability_empirical(p, d, s)
            if p_lead is None or p_trail is None:
                continue
            assert abs(p_lead + p_trail - 1.0) < 1e-9


class TestEdgeCases:
    def test_negative_deficit_raises(self):
        with pytest.raises(ValueError):
            leading_team_win_probability_empirical(3, -1, 600)

    def test_huge_deficit_clamped(self):
        """7-gol deficit deficit_cap'e clamp edilir, ayni bucket doner."""
        p_5 = leading_team_win_probability_empirical(3, 5, 600)
        p_7 = leading_team_win_probability_empirical(3, 7, 600)
        if None not in (p_5, p_7):
            assert p_5 == p_7
