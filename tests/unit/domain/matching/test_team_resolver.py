"""team_resolver.py için birim testler (pure, static)."""
from __future__ import annotations

from src.domain.matching.team_resolver import canonicalize, normalize, resolve


def test_normalize_lowercase_and_strip() -> None:
    assert normalize("  Los Angeles Lakers  ") == "los angeles lakers"


def test_normalize_turkish_dotless_i() -> None:
    # Turkish ı → i
    assert normalize("Fenerbahçe") == "fenerbahce"


def test_normalize_accents() -> None:
    assert normalize("São Paulo") == "sao paulo"
    assert normalize("Bayern München") == "bayern munchen"


def test_normalize_strips_fc_suffix() -> None:
    assert normalize("Liverpool FC") == "liverpool"


def test_normalize_strips_esports_suffix() -> None:
    assert normalize("G2 Esports") == "g2"


def test_normalize_empty() -> None:
    assert normalize("") == ""


def test_resolve_nba_abbreviation() -> None:
    assert resolve("lal") == "los angeles lakers"
    assert resolve("bos") == "boston celtics"
    assert resolve("gsw") == "golden state warriors"


def test_resolve_nfl_abbreviation() -> None:
    assert resolve("kc") == "kansas city chiefs"
    assert resolve("sf") == "san francisco 49ers"


def test_resolve_alias_lakers() -> None:
    assert resolve("Lakers") == "los angeles lakers"
    assert resolve("lakers") == "los angeles lakers"


def test_resolve_alias_chiefs() -> None:
    assert resolve("Chiefs") == "kansas city chiefs"


def test_resolve_alias_leafs() -> None:
    assert resolve("leafs") == "toronto maple leafs"


def test_resolve_unknown_returns_none() -> None:
    assert resolve("nonexistent team") is None
    assert resolve("") is None


def test_canonicalize_via_abbrev() -> None:
    assert canonicalize("LAL") == "los angeles lakers"


def test_canonicalize_via_alias() -> None:
    assert canonicalize("Lakers") == "los angeles lakers"


def test_canonicalize_already_canonical() -> None:
    # Suffix-free isim → normalize haliyle döner
    assert canonicalize("Random Club") == "random club"
