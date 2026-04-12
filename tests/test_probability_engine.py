"""Tests for bookmaker-only probability engine."""
import pytest

from src.probability_engine import BookmakerProbability, calculate_bookmaker_probability


class TestCalculateBookmakerProbability:
    """Tests for calculate_bookmaker_probability()."""

    def test_no_bookmaker_data_returns_default(self):
        result = calculate_bookmaker_probability(bookmaker_prob=None, num_bookmakers=0)
        assert result.probability == 0.5
        assert result.confidence == "C"
        assert result.bookmaker_prob == 0.0

    def test_zero_weight_returns_default(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.6, num_bookmakers=0)
        assert result.probability == 0.5
        assert result.confidence == "C"

    def test_negative_prob_returns_default(self):
        result = calculate_bookmaker_probability(bookmaker_prob=-0.1, num_bookmakers=3)
        assert result.probability == 0.5

    def test_normal_case_no_sharp(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.65, num_bookmakers=6, has_sharp=False)
        assert result.probability == 0.65
        assert result.confidence == "B"
        assert result.has_sharp is False

    def test_normal_case_with_sharp(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.70, num_bookmakers=8, has_sharp=True)
        assert result.probability == 0.70
        assert result.confidence == "A"
        assert result.has_sharp is True

    def test_low_weight_gives_c_confidence(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.55, num_bookmakers=3, has_sharp=False)
        assert result.confidence == "C"

    def test_clamp_high(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.99, num_bookmakers=5)
        assert result.probability == 0.95

    def test_clamp_low(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.02, num_bookmakers=5)
        assert result.probability == 0.05

    def test_sharp_with_low_weight_gives_c(self):
        """Sharp book present but total weight < 5 → still C."""
        result = calculate_bookmaker_probability(bookmaker_prob=0.60, num_bookmakers=2, has_sharp=True)
        assert result.confidence == "C"

    def test_returns_bookmaker_probability_dataclass(self):
        result = calculate_bookmaker_probability(bookmaker_prob=0.55, num_bookmakers=6)
        assert isinstance(result, BookmakerProbability)
        assert result.num_bookmakers == 6
        assert result.bookmaker_prob == 0.55
