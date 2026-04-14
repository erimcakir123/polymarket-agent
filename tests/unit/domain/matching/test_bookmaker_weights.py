"""bookmaker_weights.py için birim testler."""
from __future__ import annotations

from src.domain.matching.bookmaker_weights import (
    REPUTABLE_WEIGHT,
    SHARP_WEIGHT,
    STANDARD_WEIGHT,
    get_bookmaker_weight,
    is_sharp,
)


def test_sharp_pinnacle_weight() -> None:
    assert get_bookmaker_weight("pinnacle") == SHARP_WEIGHT
    assert get_bookmaker_weight("Pinnacle") == SHARP_WEIGHT


def test_sharp_betfair_ex_eu() -> None:
    assert get_bookmaker_weight("betfair_ex_eu") == SHARP_WEIGHT


def test_reputable_bet365() -> None:
    assert get_bookmaker_weight("bet365") == REPUTABLE_WEIGHT
    # Display name variant
    assert get_bookmaker_weight("Bet 365") == REPUTABLE_WEIGHT


def test_reputable_williamhill() -> None:
    assert get_bookmaker_weight("williamhill") == REPUTABLE_WEIGHT
    assert get_bookmaker_weight("William Hill") == REPUTABLE_WEIGHT


def test_unknown_gets_standard() -> None:
    assert get_bookmaker_weight("some_random_book") == STANDARD_WEIGHT
    assert get_bookmaker_weight("") == STANDARD_WEIGHT


def test_is_sharp_true() -> None:
    assert is_sharp("pinnacle") is True
    assert is_sharp("matchbook") is True


def test_is_sharp_false() -> None:
    assert is_sharp("bet365") is False
    assert is_sharp("unknown") is False
    assert is_sharp("") is False


def test_weight_values() -> None:
    assert SHARP_WEIGHT == 3.0
    assert REPUTABLE_WEIGHT == 1.5
    assert STANDARD_WEIGHT == 1.0
