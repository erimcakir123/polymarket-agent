"""probability.py için birim testler (TDD §6.1)."""
from __future__ import annotations

from src.domain.analysis.probability import BookmakerProbability, calculate_bookmaker_probability


def test_insufficient_data_returns_05_with_C_conf() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=None, num_bookmakers=0, has_sharp=False)
    assert r.probability == 0.5
    assert r.confidence == "C"
    assert r.bookmaker_prob == 0.0


def test_num_bookmakers_below_1_returns_05() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=0.7, num_bookmakers=0.5, has_sharp=True)
    assert r.probability == 0.5


def test_normal_prob_with_sharp_returns_A() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=0.70, num_bookmakers=12, has_sharp=True)
    assert r.confidence == "A"
    assert r.probability == 0.7
    assert r.bookmaker_prob == 0.7
    assert r.has_sharp is True


def test_normal_prob_without_sharp_returns_B() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=0.60, num_bookmakers=8, has_sharp=False)
    assert r.confidence == "B"
    assert r.probability == 0.6


def test_clamp_too_high() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=0.99, num_bookmakers=10, has_sharp=True)
    assert r.probability == 0.95


def test_clamp_too_low() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=0.01, num_bookmakers=10, has_sharp=True)
    assert r.probability == 0.05


def test_zero_bookmaker_prob_returns_05() -> None:
    r = calculate_bookmaker_probability(bookmaker_prob=0.0, num_bookmakers=10, has_sharp=True)
    assert r.probability == 0.5


def test_returns_dataclass() -> None:
    r = calculate_bookmaker_probability(0.7, 10, True)
    assert isinstance(r, BookmakerProbability)
