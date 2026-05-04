"""MLB team alias normalization.

Maps Polymarket question phrasings ("Braves", "Atlanta Braves") and
MLB-StatsAPI / Odds API team names to ESPN abbreviation, the canonical
key used throughout the bot.

30 MLB teams (2026 season, no expansion).

References:
- ESPN team abbreviations
- MLB-StatsAPI team table
- Polymarket MLB question patterns (mostly mascot-only)
"""
from __future__ import annotations

# Canonical: ESPN abbreviation -> {name, mascot, espn_id, mlb_id, [alt_abbrs]}
# mlb_id: MLB-StatsAPI team ID (different from ESPN; required for all statsapi calls)
MLB_TEAMS: dict[str, dict] = {
    "ARI": {"name": "Arizona Diamondbacks",  "mascot": "Diamondbacks", "espn_id": "29", "mlb_id": "109", "alt_abbrs": ["AZ"]},
    "ATL": {"name": "Atlanta Braves",        "mascot": "Braves",       "espn_id": "15", "mlb_id": "144"},
    "BAL": {"name": "Baltimore Orioles",     "mascot": "Orioles",      "espn_id": "1",  "mlb_id": "110"},
    "BOS": {"name": "Boston Red Sox",        "mascot": "Red Sox",      "espn_id": "2",  "mlb_id": "111"},
    "CHC": {"name": "Chicago Cubs",          "mascot": "Cubs",         "espn_id": "16", "mlb_id": "112"},
    "CWS": {"name": "Chicago White Sox",     "mascot": "White Sox",    "espn_id": "4",  "mlb_id": "145", "alt_abbrs": ["CHW"]},
    "CIN": {"name": "Cincinnati Reds",       "mascot": "Reds",         "espn_id": "17", "mlb_id": "113"},
    "CLE": {"name": "Cleveland Guardians",   "mascot": "Guardians",    "espn_id": "5",  "mlb_id": "114"},
    "COL": {"name": "Colorado Rockies",      "mascot": "Rockies",      "espn_id": "27", "mlb_id": "115"},
    "DET": {"name": "Detroit Tigers",        "mascot": "Tigers",       "espn_id": "6",  "mlb_id": "116"},
    "HOU": {"name": "Houston Astros",        "mascot": "Astros",       "espn_id": "18", "mlb_id": "117"},
    "KC":  {"name": "Kansas City Royals",    "mascot": "Royals",       "espn_id": "7",  "mlb_id": "118", "alt_abbrs": ["KCR"]},
    "LAA": {"name": "Los Angeles Angels",    "mascot": "Angels",       "espn_id": "3",  "mlb_id": "108"},
    "LAD": {"name": "Los Angeles Dodgers",   "mascot": "Dodgers",      "espn_id": "19", "mlb_id": "119"},
    "MIA": {"name": "Miami Marlins",         "mascot": "Marlins",      "espn_id": "28", "mlb_id": "146"},
    "MIL": {"name": "Milwaukee Brewers",     "mascot": "Brewers",      "espn_id": "8",  "mlb_id": "158"},
    "MIN": {"name": "Minnesota Twins",       "mascot": "Twins",        "espn_id": "9",  "mlb_id": "142"},
    "NYM": {"name": "New York Mets",         "mascot": "Mets",         "espn_id": "21", "mlb_id": "121"},
    "NYY": {"name": "New York Yankees",      "mascot": "Yankees",      "espn_id": "10", "mlb_id": "147"},
    "OAK": {
        "name": "Athletics",
        "mascot": "Athletics",
        "espn_id": "11",
        "mlb_id": "133",
        "former_names": ["Oakland Athletics", "Sacramento Athletics"],
    },
    "PHI": {"name": "Philadelphia Phillies", "mascot": "Phillies",     "espn_id": "22", "mlb_id": "143"},
    "PIT": {"name": "Pittsburgh Pirates",    "mascot": "Pirates",      "espn_id": "23", "mlb_id": "134"},
    "SD":  {"name": "San Diego Padres",      "mascot": "Padres",       "espn_id": "25", "mlb_id": "135", "alt_abbrs": ["SDP"]},
    "SEA": {"name": "Seattle Mariners",      "mascot": "Mariners",     "espn_id": "12", "mlb_id": "136"},
    "SF":  {"name": "San Francisco Giants",  "mascot": "Giants",       "espn_id": "26", "mlb_id": "137", "alt_abbrs": ["SFG"]},
    "STL": {"name": "St. Louis Cardinals",   "mascot": "Cardinals",    "espn_id": "24", "mlb_id": "138"},
    "TB":  {"name": "Tampa Bay Rays",        "mascot": "Rays",         "espn_id": "30", "mlb_id": "139", "alt_abbrs": ["TBR"]},
    "TEX": {"name": "Texas Rangers",         "mascot": "Rangers",      "espn_id": "13", "mlb_id": "140"},
    "TOR": {"name": "Toronto Blue Jays",     "mascot": "Blue Jays",    "espn_id": "14", "mlb_id": "141"},
    "WSH": {"name": "Washington Nationals",  "mascot": "Nationals",    "espn_id": "20", "mlb_id": "120", "alt_abbrs": ["WSN"]},
}


def _build_lookup_map() -> dict[str, str]:
    """Build flat normalized-string -> canonical abbr lookup."""
    lookup: dict[str, str] = {}
    for abbr, info in MLB_TEAMS.items():
        lookup[abbr.upper()] = abbr
        lookup[info["name"].upper()] = abbr
        lookup[info["mascot"].upper()] = abbr
        for alt in info.get("alt_abbrs", []):
            lookup[alt.upper()] = abbr
        for former in info.get("former_names", []):
            lookup[former.upper()] = abbr
    return lookup


_LOOKUP: dict[str, str] = _build_lookup_map()


def resolve_mlb_team(query: str | None) -> str | None:
    """Resolve a team name/abbr/mascot to canonical ESPN abbr.

    Args:
        query: e.g. "Braves", "Atlanta Braves", "ATL"

    Returns:
        Canonical ESPN abbr or None if no match.
    """
    if not query or not isinstance(query, str):
        return None
    return _LOOKUP.get(query.strip().upper())


def get_team_info(abbr: str | None) -> dict | None:
    """Return full team info dict by canonical abbr."""
    if not abbr or not isinstance(abbr, str):
        return None
    return MLB_TEAMS.get(abbr.strip().upper())
