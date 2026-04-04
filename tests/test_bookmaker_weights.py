"""Tests for bookmaker quality weight tiers."""


def test_sharp_bookmakers_get_weight_3():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("pinnacle") == 3.0
    assert get_bookmaker_weight("betfair_ex_eu") == 3.0
    assert get_bookmaker_weight("betfair_ex_uk") == 3.0
    assert get_bookmaker_weight("matchbook") == 3.0


def test_reputable_bookmakers_get_weight_1_5():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("bet365") == 1.5
    assert get_bookmaker_weight("williamhill") == 1.5
    assert get_bookmaker_weight("unibet_eu") == 1.5
    assert get_bookmaker_weight("unibet_uk") == 1.5
    assert get_bookmaker_weight("betclic") == 1.5
    assert get_bookmaker_weight("marathonbet") == 1.5


def test_standard_bookmakers_get_weight_1():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("draftkings") == 1.0
    assert get_bookmaker_weight("fanduel") == 1.0
    assert get_bookmaker_weight("betmgm") == 1.0
    assert get_bookmaker_weight("caesars") == 1.0


def test_unknown_bookmaker_defaults_to_1():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("some_random_book") == 1.0
    assert get_bookmaker_weight("") == 1.0


def test_case_insensitive():
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("Pinnacle") == 3.0
    assert get_bookmaker_weight("BET365") == 1.5
    assert get_bookmaker_weight("DraftKings") == 1.0


def test_display_name_normalization():
    """ESPN returns display names like 'Bet365' or 'William Hill' — handle these too."""
    from src.matching.bookmaker_weights import get_bookmaker_weight
    assert get_bookmaker_weight("William Hill") == 1.5
    assert get_bookmaker_weight("Bet 365") == 1.5


def test_is_sharp_helper():
    from src.matching.bookmaker_weights import is_sharp
    assert is_sharp("pinnacle") is True
    assert is_sharp("betfair_ex_eu") is True
    assert is_sharp("bet365") is False
    assert is_sharp("draftkings") is False
