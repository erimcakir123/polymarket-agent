"""Hybrid empirical-first wrapper tests."""
from __future__ import annotations

import pytest
from unittest.mock import patch
from src.domain.math.nhl_win_probability import (
    trailing_team_win_probability,
    leading_team_win_probability,
)


class TestHybridSourceSelection:
    def test_uses_empirical_when_available(self):
        """3_1_1200 high-sample bucket (n=1511)."""
        prob, source = trailing_team_win_probability(3, 1, 1200)
        assert source == "empirical"
        assert 0.18 < prob < 0.32

    def test_falls_back_to_skellam_when_empirical_none(self):
        with patch(
            "src.domain.math.nhl_win_probability.nhl_empirical_wp"
            ".trailing_team_win_probability_empirical",
            return_value=None,
        ):
            prob, source = trailing_team_win_probability(3, 1, 1200)
            assert source == "skellam_fallback"
            assert 0.0 <= prob <= 1.0


class TestHybridTrivialEdgeCases:
    def test_zero_deficit_trivial(self):
        prob, source = trailing_team_win_probability(3, 0, 600)
        assert prob == 1.0
        assert source == "trivial"

    def test_zero_seconds_trivial(self):
        prob, source = trailing_team_win_probability(3, 2, 0)
        assert prob == 0.0
        assert source == "trivial"

    def test_zero_lead_trivial(self):
        prob, source = leading_team_win_probability(3, 0, 600)
        assert prob == 0.0
        assert source == "trivial"


class TestHybridConsistency:
    def test_leading_plus_trailing_equals_one_empirical(self):
        for p, d, s in [(3, 1, 600), (3, 2, 1200), (3, 1, 60)]:
            p_lead, _ = leading_team_win_probability(p, d, s)
            p_trail, _ = trailing_team_win_probability(p, d, s)
            assert abs(p_lead + p_trail - 1.0) < 1e-9
