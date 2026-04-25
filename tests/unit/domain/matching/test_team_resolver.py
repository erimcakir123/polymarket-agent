"""team_resolver.py için birim testler (pure, static)."""
from __future__ import annotations

from src.domain.matching.team_resolver import canonicalize, normalize, resolve, resolve_nba_espn_id


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


# ── resolve_nba_espn_id ──────────────────────────────────────────

def test_resolve_nba_espn_id_full_name() -> None:
    assert resolve_nba_espn_id("Los Angeles Lakers") == "13"
    assert resolve_nba_espn_id("Boston Celtics") == "2"
    assert resolve_nba_espn_id("Orlando Magic") == "19"
    assert resolve_nba_espn_id("Oklahoma City Thunder") == "25"


def test_resolve_nba_espn_id_via_alias() -> None:
    # "Lakers" → canonicalize → "los angeles lakers" → "13"
    assert resolve_nba_espn_id("Lakers") == "13"
    assert resolve_nba_espn_id("Celtics") == "2"
    assert resolve_nba_espn_id("Thunder") == "25"


def test_resolve_nba_espn_id_short_canonical_forms() -> None:
    # Teams where canonicalize() doesn't expand to full city+name
    assert resolve_nba_espn_id("Trail Blazers") == "22"
    assert resolve_nba_espn_id("Timberwolves") == "16"
    assert resolve_nba_espn_id("Cavaliers") == "5"
    assert resolve_nba_espn_id("Mavericks") == "6"
    assert resolve_nba_espn_id("Wizards") == "27"
    assert resolve_nba_espn_id("Pistons") == "8"


def test_resolve_nba_espn_id_la_clippers() -> None:
    assert resolve_nba_espn_id("LA Clippers") == "12"
    assert resolve_nba_espn_id("Clips") == "12"  # alias "clips" → "la clippers" → "12"


def test_resolve_nba_espn_id_unknown_returns_empty() -> None:
    assert resolve_nba_espn_id("Unknown Team") == ""
    assert resolve_nba_espn_id("") == ""
    assert resolve_nba_espn_id("Soccer FC") == ""


def test_resolve_nba_espn_id_all_30_teams_covered() -> None:
    # Every NBA team in the static abbrev table should resolve to a non-empty ID
    nba_abbrevs = [
        "lal", "bos", "gsw", "bkn", "nyk", "phi", "mil", "mia",
        "chi", "phx", "dal", "den", "min", "okc", "cle", "lac",
        "hou", "mem", "nop", "atl", "ind", "orl", "tor", "wsh",
        "det", "cha", "sac", "por", "uta", "sas",
    ]
    for abbrev in nba_abbrevs:
        result = resolve_nba_espn_id(abbrev)
        assert result != "", f"No ESPN ID for NBA team: {abbrev}"
