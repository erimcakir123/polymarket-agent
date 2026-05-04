"""MLB team aliases tests."""
from src.domain.sports.mlb_team_aliases import (
    MLB_TEAMS,
    resolve_mlb_team,
    get_team_info,
)


def test_mlb_teams_count_30():
    """Exactly 30 MLB teams (no expansion in 2026)."""
    assert len(MLB_TEAMS) == 30


def test_resolve_canonical_abbreviation():
    """Canonical 3-letter abbr resolves to itself."""
    assert resolve_mlb_team("ATL") == "ATL"
    assert resolve_mlb_team("nyy") == "NYY"


def test_resolve_full_name():
    """Full team name resolves to canonical abbr."""
    assert resolve_mlb_team("Atlanta Braves") == "ATL"
    assert resolve_mlb_team("Boston Red Sox") == "BOS"


def test_resolve_mascot_only():
    """Mascot-only string resolves (Polymarket common pattern)."""
    assert resolve_mlb_team("Braves") == "ATL"
    assert resolve_mlb_team("Yankees") == "NYY"
    assert resolve_mlb_team("Red Sox") == "BOS"


def test_resolve_unknown_returns_none():
    assert resolve_mlb_team("Toronto Maple Leafs") is None  # NHL, not MLB
    assert resolve_mlb_team("") is None
    assert resolve_mlb_team(None) is None  # type: ignore[arg-type]


def test_get_team_info_returns_dict():
    info = get_team_info("ATL")
    assert info is not None
    assert info["name"] == "Atlanta Braves"
    assert info["mascot"] == "Braves"
    assert "espn_id" in info
    assert "mlb_id" in info  # MLB Stats API team ID (different from ESPN)


def test_resolve_alt_abbreviation():
    """Alt abbreviations (MLB-StatsAPI / Odds API variants) resolve correctly."""
    assert resolve_mlb_team("CHW") == "CWS"   # White Sox alt
    assert resolve_mlb_team("KCR") == "KC"    # Royals alt
    assert resolve_mlb_team("TBR") == "TB"    # Rays alt
    assert resolve_mlb_team("WSN") == "WSH"   # Nationals alt
    assert resolve_mlb_team("AZ") == "ARI"    # Diamondbacks alt


def test_all_teams_have_mlb_id():
    """Every team entry must carry mlb_id for MLB-StatsAPI calls."""
    for abbr, info in MLB_TEAMS.items():
        assert "mlb_id" in info, f"{abbr} missing mlb_id"
        assert info["mlb_id"].isdigit(), f"{abbr} mlb_id not numeric: {info['mlb_id']}"


def test_resolve_athletics_oakland_and_sacramento():
    """Athletics relocated 2025; both former names + current resolve."""
    assert resolve_mlb_team("Oakland Athletics") == "OAK"
    assert resolve_mlb_team("Sacramento Athletics") == "OAK"
    assert resolve_mlb_team("Athletics") == "OAK"
