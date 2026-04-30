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

# Canonical: ESPN abbreviation -> {name, mascot, espn_id, [alt_abbrs]}
MLB_TEAMS: dict[str, dict] = {
    "ARI": {"name": "Arizona Diamondbacks",  "mascot": "Diamondbacks", "espn_id": "29", "alt_abbrs": ["AZ"]},
    "ATL": {"name": "Atlanta Braves",        "mascot": "Braves",       "espn_id": "15"},
    "BAL": {"name": "Baltimore Orioles",     "mascot": "Orioles",      "espn_id": "1"},
    "BOS": {"name": "Boston Red Sox",        "mascot": "Red Sox",      "espn_id": "2"},
    "CHC": {"name": "Chicago Cubs",          "mascot": "Cubs",         "espn_id": "16"},
    "CWS": {"name": "Chicago White Sox",     "mascot": "White Sox",    "espn_id": "4",  "alt_abbrs": ["CHW"]},
    "CIN": {"name": "Cincinnati Reds",       "mascot": "Reds",         "espn_id": "17"},
    "CLE": {"name": "Cleveland Guardians",   "mascot": "Guardians",    "espn_id": "5"},
    "COL": {"name": "Colorado Rockies",      "mascot": "Rockies",      "espn_id": "27"},
    "DET": {"name": "Detroit Tigers",        "mascot": "Tigers",       "espn_id": "6"},
    "HOU": {"name": "Houston Astros",        "mascot": "Astros",       "espn_id": "18"},
    "KC":  {"name": "Kansas City Royals",    "mascot": "Royals",       "espn_id": "7",  "alt_abbrs": ["KCR"]},
    "LAA": {"name": "Los Angeles Angels",    "mascot": "Angels",       "espn_id": "3"},
    "LAD": {"name": "Los Angeles Dodgers",   "mascot": "Dodgers",      "espn_id": "19"},
    "MIA": {"name": "Miami Marlins",         "mascot": "Marlins",      "espn_id": "28"},
    "MIL": {"name": "Milwaukee Brewers",     "mascot": "Brewers",      "espn_id": "8"},
    "MIN": {"name": "Minnesota Twins",       "mascot": "Twins",        "espn_id": "9"},
    "NYM": {"name": "New York Mets",         "mascot": "Mets",         "espn_id": "21"},
    "NYY": {"name": "New York Yankees",      "mascot": "Yankees",      "espn_id": "10"},
    "OAK": {"name": "Oakland Athletics",     "mascot": "Athletics",    "espn_id": "11"},
    "PHI": {"name": "Philadelphia Phillies", "mascot": "Phillies",     "espn_id": "22"},
    "PIT": {"name": "Pittsburgh Pirates",    "mascot": "Pirates",      "espn_id": "23"},
    "SD":  {"name": "San Diego Padres",      "mascot": "Padres",       "espn_id": "25", "alt_abbrs": ["SDP"]},
    "SEA": {"name": "Seattle Mariners",      "mascot": "Mariners",     "espn_id": "12"},
    "SF":  {"name": "San Francisco Giants",  "mascot": "Giants",       "espn_id": "26", "alt_abbrs": ["SFG"]},
    "STL": {"name": "St. Louis Cardinals",   "mascot": "Cardinals",    "espn_id": "24"},
    "TB":  {"name": "Tampa Bay Rays",        "mascot": "Rays",         "espn_id": "30", "alt_abbrs": ["TBR"]},
    "TEX": {"name": "Texas Rangers",         "mascot": "Rangers",      "espn_id": "13"},
    "TOR": {"name": "Toronto Blue Jays",     "mascot": "Blue Jays",    "espn_id": "14"},
    "WSH": {"name": "Washington Nationals",  "mascot": "Nationals",    "espn_id": "20", "alt_abbrs": ["WSN"]},
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
    return lookup


_LOOKUP: dict[str, str] = _build_lookup_map()


def resolve_mlb_team(query: str | None) -> str | None:
    """Resolve a team name/abbr/mascot to canonical ESPN abbr."""
    if not query or not isinstance(query, str):
        return None
    return _LOOKUP.get(query.strip().upper())


def get_team_info(abbr: str | None) -> dict | None:
    """Return full team info dict by canonical abbr."""
    if not abbr or not isinstance(abbr, str):
        return None
    return MLB_TEAMS.get(abbr.strip().upper())
