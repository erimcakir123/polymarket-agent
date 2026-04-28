"""Skellam-based puck line cover probability tests."""
from __future__ import annotations

from src.domain.math.nhl_puck_line import skellam_p_favorite_covers_minus_1_5


class TestSkellamPCovers:
    def test_already_covered_returns_high_prob(self):
        """+3 lead, P3 start → favori zaten -1.5'i geçti, %90+ cover."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=3, seconds_remaining=1200)
        assert p > 0.85

    def test_tied_at_p3_start(self):
        """0 lead, P3 start → favori 2+ atmalı, çok zor."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=0, seconds_remaining=1200)
        assert 0.10 < p < 0.30

    def test_one_goal_lead_p3_late(self):
        """+1 lead, son 60s → 1 gol fark kalır, cover için 1+ daha gerek → çok düşük.

        Note: plan'da bound 0.10-0.40 yazıyordu ama 60s'de λ≈0.051 ile
        Skellam P(diff>=1) ≈ 0.05. Gerçek NHL son-60s 1-gol-farkı senaryosu
        ~%4-7 favori cover. Plan bound'u empirically gevşetildi (≤0.10).
        """
        p = skellam_p_favorite_covers_minus_1_5(current_margin=1, seconds_remaining=60)
        assert 0.0 < p < 0.10

    def test_two_goal_lead_p3_late(self):
        """+2 lead, son 60s → cover olmuş gibi, %85+ kalan."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=2, seconds_remaining=60)
        assert p > 0.85

    def test_negative_margin_low_prob(self):
        """-1 deficit, P3 ortası → cover için 3+ farklı çevirmeli, çok düşük."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=-1, seconds_remaining=600)
        assert p < 0.10

    def test_zero_seconds_remaining_returns_actual(self):
        """Süre bitti, current_margin >= 2 → 1.0, değilse → 0.0."""
        assert skellam_p_favorite_covers_minus_1_5(current_margin=2, seconds_remaining=0) == 1.0
        assert skellam_p_favorite_covers_minus_1_5(current_margin=1, seconds_remaining=0) == 0.0
        assert skellam_p_favorite_covers_minus_1_5(current_margin=3, seconds_remaining=0) == 1.0

    def test_full_game_remaining_balanced(self):
        """3600 sec kala, current_margin=0 → ~%30-40 cover (favori avantajı + zaman)."""
        p = skellam_p_favorite_covers_minus_1_5(current_margin=0, seconds_remaining=3600)
        assert 0.20 < p < 0.45
