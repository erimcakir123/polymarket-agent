"""Poisson-based NHL totals (over/under) probability tests."""
from __future__ import annotations

from src.domain.math.nhl_totals import poisson_p_over


class TestPOverSkellam:
    def test_already_over_returns_one(self):
        """current_total=6 > target=5.5 → 1.0 (zaten geçti)."""
        p = poisson_p_over(current_total=6, target_total=5.5, seconds_remaining=600)
        assert p == 1.0

    def test_zero_seconds_uses_current_only(self):
        """Süre bitti — current > target → 1.0, değilse → 0.0."""
        assert poisson_p_over(current_total=6, target_total=5.5, seconds_remaining=0) == 1.0
        assert poisson_p_over(current_total=5, target_total=5.5, seconds_remaining=0) == 0.0

    def test_p3_late_low_total_low_p_over(self):
        """current=2, target=5.5, 300s — 4 gol gerek, çok düşük."""
        p = poisson_p_over(current_total=2, target_total=5.5, seconds_remaining=300)
        assert p < 0.05

    def test_p3_late_close_to_target(self):
        """current=5, target=5.5, 300s — 1 gol yeter, makul."""
        p = poisson_p_over(current_total=5, target_total=5.5, seconds_remaining=300)
        assert 0.10 < p < 0.50

    def test_full_game_balanced(self):
        """current=0, target=5.5, 3600s — lig avg 6.142 → over edge favor."""
        p = poisson_p_over(current_total=0, target_total=5.5, seconds_remaining=3600)
        assert 0.50 < p < 0.75

    def test_full_game_target_6_5(self):
        """current=0, target=6.5, 3600s — lig avg altında, edge yakın 50/50."""
        p = poisson_p_over(current_total=0, target_total=6.5, seconds_remaining=3600)
        assert 0.35 < p < 0.55
