"""odds_sport_keys.py için birim testler."""
from __future__ import annotations

from src.domain.matching.odds_sport_keys import (
    is_soccer_key,
    resolve_odds_key,
    slug_to_odds_key,
    tag_to_odds_key,
)


def test_slug_nba_maps_to_basketball() -> None:
    assert slug_to_odds_key("nba") == "basketball_nba"


def test_slug_mlb_maps() -> None:
    assert slug_to_odds_key("mlb") == "baseball_mlb"


def test_slug_nfl_maps() -> None:
    assert slug_to_odds_key("nfl") == "americanfootball_nfl"


def test_slug_nhl_maps() -> None:
    assert slug_to_odds_key("nhl") == "icehockey_nhl"


def test_slug_lpga_maps_golf() -> None:
    assert slug_to_odds_key("lpga") == "golf_lpga_tour"


def test_slug_unknown_returns_none() -> None:
    assert slug_to_odds_key("xyz_unknown") is None


def test_tag_premier_league() -> None:
    assert tag_to_odds_key("premier-league") == "soccer_epl"


def test_tag_la_liga() -> None:
    assert tag_to_odds_key("la-liga") == "soccer_spain_la_liga"


def test_tag_with_year_suffix_strips() -> None:
    # 'serie-a-2025' → strip → 'serie-a'
    assert tag_to_odds_key("serie-a-2025") == "soccer_italy_serie_a"


def test_tag_unknown_returns_none() -> None:
    assert tag_to_odds_key("random-tag") is None


def test_resolve_with_slug_wins() -> None:
    # Slug prefix 'nba' → basketball_nba, tags göz ardı
    assert resolve_odds_key("nba-lal-bos-2026-04-13", ["some-unrelated-tag"]) == "basketball_nba"


def test_resolve_falls_back_to_tag() -> None:
    # Slug prefix bilinmiyor → tag
    assert resolve_odds_key("unknown-team-match", ["premier-league"]) == "soccer_epl"


def test_resolve_none_if_both_unknown() -> None:
    assert resolve_odds_key("xyz-random", ["another-unknown"]) is None


def test_resolve_empty_inputs() -> None:
    assert resolve_odds_key(None, None) is None
    assert resolve_odds_key("", []) is None


def test_is_soccer_key() -> None:
    assert is_soccer_key("soccer_epl") is True
    assert is_soccer_key("soccer_spain_la_liga") is True
    assert is_soccer_key("basketball_nba") is False
    assert is_soccer_key(None) is False
    assert is_soccer_key("") is False
