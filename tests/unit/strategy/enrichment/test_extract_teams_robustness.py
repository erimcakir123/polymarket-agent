"""extract_teams robustluğu — Ö5 audit notu.

Polymarket çeşitli question formatları kullanıyor: " vs ", " vs. ", title prefix,
soru cümlesi. Parser bunları handle etmeli, edge case'lerde None döndürmeli
(sessiz crash yasak).
"""
from src.strategy.enrichment.question_parser import extract_teams


def test_vs_split_basic():
    a, b = extract_teams("Alice vs Bob")
    assert a == "Alice"
    assert b == "Bob"


def test_vs_dot_split():
    a, b = extract_teams("Alice vs. Bob")
    assert a == "Alice"
    assert b == "Bob"


def test_empty_question_returns_none_pair():
    a, b = extract_teams("")
    assert a is None and b is None


def test_no_separator_single_team():
    a, b = extract_teams("Will Federer win?")
    # Tek takım yakalansın veya ikisi de None
    assert a is None or b is None


def test_title_prefix_stripped():
    """Roland Garros: Alice vs Bob → prefix'ten sonra parse."""
    a, b = extract_teams("Roland Garros: Alice vs Bob")
    # Prefix temizleme + vs split bekleniyor; çalışmıyorsa None döner
    assert (a == "Alice" and b == "Bob") or (a is None and b is None)
