"""slug_parser.py için birim testler."""
from __future__ import annotations

from src.domain.matching.slug_parser import extract_slug_tokens, parse_slug


def test_parse_standard_nba_slug() -> None:
    p = parse_slug("nba-lal-bos-2026-04-13")
    assert p.sport == "nba"
    assert p.team_tokens == ["lal", "bos"]


def test_parse_standard_nfl_slug() -> None:
    p = parse_slug("nfl-kc-buf-2026-01-26")
    assert p.sport == "nfl"
    assert p.team_tokens == ["kc", "buf"]


def test_parse_no_sport_prefix() -> None:
    p = parse_slug("will-team-a-beat-team-b-2026-04-13")
    assert p.sport is None
    # 'will'/'beat' noise tokens filtered — 'team' 2 char OK, kalanlar
    assert "will" not in p.team_tokens
    assert "beat" not in p.team_tokens


def test_parse_empty() -> None:
    p = parse_slug("")
    assert p.sport is None
    assert p.team_tokens == []


def test_parse_strips_date_tokens() -> None:
    p = parse_slug("nba-lal-bos-2026-04-13")
    # Raw tokens (date stripped) should not contain date numerals
    for tok in p.raw_tokens:
        assert not (tok.isdigit() and len(tok) == 4)  # no year


def test_parse_no_date() -> None:
    # Bazı slug'lar tarihli değil
    p = parse_slug("nba-lal-bos")
    assert p.sport == "nba"
    assert p.team_tokens == ["lal", "bos"]


def test_extract_tokens() -> None:
    tokens = extract_slug_tokens("nba-lal-bos-2026-04-13")
    assert "nba" in tokens
    assert "lal" in tokens
    assert "bos" in tokens
    # Tarih rakamları filtrelenir
    assert "2026" not in tokens
    assert "04" not in tokens


def test_extract_filters_single_char() -> None:
    tokens = extract_slug_tokens("a-ab-abc")
    assert "a" not in tokens
    assert "ab" in tokens
    assert "abc" in tokens
