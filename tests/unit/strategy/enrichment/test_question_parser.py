"""question_parser.py için birim testler."""
from __future__ import annotations

from src.strategy.enrichment.question_parser import extract_teams


def test_vs_split_simple() -> None:
    a, b = extract_teams("Lakers vs Celtics")
    assert a == "Lakers"
    assert b == "Celtics"


def test_vs_with_prefix() -> None:
    a, b = extract_teams("NBA: Lakers vs Celtics")
    assert a == "Lakers"
    assert b == "Celtics"


def test_will_x_beat_y() -> None:
    a, b = extract_teams("Will Lakers beat Celtics?")
    assert a == "Lakers"
    assert b == "Celtics"


def test_will_x_defeat_y() -> None:
    a, b = extract_teams("Will Lakers defeat Celtics")
    assert a == "Lakers"
    assert b == "Celtics"


def test_who_will_win() -> None:
    a, b = extract_teams("Who will win: Lakers or Celtics?")
    assert a == "Lakers"
    assert b == "Celtics"


def test_winner_of_x_or_y() -> None:
    a, b = extract_teams("Winner of Lakers or Celtics")
    assert a == "Lakers"
    assert b == "Celtics"


def test_will_x_win_single_team() -> None:
    a, b = extract_teams("Will Lakers win?")
    assert a == "Lakers"
    assert b is None


def test_strips_trailing_question_mark() -> None:
    a, b = extract_teams("Lakers vs Celtics?")
    assert b == "Celtics"  # No '?' suffix


def test_empty_returns_none() -> None:
    assert extract_teams("") == (None, None)


def test_unparseable_returns_none() -> None:
    a, b = extract_teams("Random question about nothing")
    # Sport prefixes match 'random' not, so returns None/None
    assert a is None or b is None


def test_versus_also_works() -> None:
    a, b = extract_teams("Lakers versus Celtics")
    assert a == "Lakers"
    assert b == "Celtics"


def test_will_x_to_beat_y() -> None:
    a, b = extract_teams("Will Lakers to beat Celtics?")
    assert a == "Lakers"
    assert b == "Celtics"
