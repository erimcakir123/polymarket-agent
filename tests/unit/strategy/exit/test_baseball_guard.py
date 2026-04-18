"""Baseball inning guard testleri (SPEC-008)."""
from __future__ import annotations

from src.config.sport_rules import get_sport_rule
from src.strategy.exit.stop_loss import parse_baseball_inning


def test_mlb_comeback_thresholds_configured() -> None:
    thresholds = get_sport_rule("mlb", "comeback_thresholds")
    assert thresholds is not None
    assert thresholds[3] == 6   # inning 1-3: 6 run
    assert thresholds[5] == 5   # inning 4-5: 5 run
    assert thresholds[7] == 4   # inning 6-7: 4 run
    assert thresholds[8] == 3   # inning 8: 3 run
    assert thresholds[9] == 2   # inning 9: 2 run


def test_mlb_extra_inning_threshold_configured() -> None:
    assert get_sport_rule("mlb", "extra_inning_threshold") == 1


def test_parse_inning_top_1st_returns_1() -> None:
    assert parse_baseball_inning("Top 1st") == 1


def test_parse_inning_bot_5th_returns_5() -> None:
    assert parse_baseball_inning("Bot 5th") == 5


def test_parse_inning_mid_9th_returns_9() -> None:
    assert parse_baseball_inning("Mid 9th") == 9


def test_parse_inning_top_2nd_returns_2() -> None:
    assert parse_baseball_inning("Top 2nd") == 2


def test_parse_inning_bot_3rd_returns_3() -> None:
    assert parse_baseball_inning("Bot 3rd") == 3


def test_parse_inning_extra_11th_returns_11() -> None:
    assert parse_baseball_inning("Top 11th") == 11


def test_parse_inning_empty_returns_none() -> None:
    assert parse_baseball_inning("") is None


def test_parse_inning_final_returns_none() -> None:
    assert parse_baseball_inning("Final") is None


def test_parse_inning_in_progress_returns_none() -> None:
    assert parse_baseball_inning("In Progress") is None
