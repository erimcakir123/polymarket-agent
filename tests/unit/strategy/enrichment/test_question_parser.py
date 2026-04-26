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


def test_tournament_prefix_stripped_from_team_a() -> None:
    """Turnuva adı prefix'i (ATP/WTA whitelist dışı) team_a'yı kirletmemeli."""
    a, b = extract_teams("Porsche Tennis Grand Prix: Eva Lys vs Elina Svitolina")
    assert a == "Eva Lys"
    assert b == "Elina Svitolina"


def test_tournament_prefix_with_complex_name() -> None:
    a, b = extract_teams("Open Capfinances Rouen Metropole: Katie Boulter vs Jaqueline Cristian")
    assert a == "Katie Boulter"
    assert b == "Jaqueline Cristian"


def test_city_prefix_stripped() -> None:
    a, b = extract_teams("Tallahassee: Alex Rybakov vs Pedro Boscardin Dias")
    assert a == "Alex Rybakov"
    assert b == "Pedro Boscardin Dias"


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


def test_spread_single_team_with_line() -> None:
    """'Spread: TeamName (-X.5)' formatı — tek takım, line parantez içinde."""
    a, b = extract_teams("Spread: Knicks (-2.5)")
    assert a == "Knicks"
    assert b is None


def test_spread_negative_line_timberwolves() -> None:
    a, b = extract_teams("Spread: Timberwolves (-1.5)")
    assert a == "Timberwolves"
    assert b is None


def test_spread_positive_line() -> None:
    a, b = extract_teams("Spread: Lakers (+5.5)")
    assert a == "Lakers"
    assert b is None


def test_spread_multi_word_team() -> None:
    a, b = extract_teams("Spread: Los Angeles Lakers (-3.5)")
    assert a == "Los Angeles Lakers"
    assert b is None


def test_spread_prefix_only_no_parenthetical() -> None:
    """Parantez olmadan tek takım adı — pattern 6 çalışmaz, diğer pattern'ler dener."""
    a, b = extract_teams("Spread: Lakers")
    # Spread: soyulur → "Lakers" kalır; hiçbir 2-team pattern yok, (  yok → None
    assert a is None
    assert b is None
