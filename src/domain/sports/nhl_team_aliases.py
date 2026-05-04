"""
NHL team alias normalization.

Maps Polymarket question phrasings (e.g. "Bruins", "Boston Bruins") and
The Odds API team names ("Boston Bruins") to ESPN abbreviation ("BOS")
which is the canonical key used throughout the bot.

32 NHL teams (2024-25 season, Utah Mammoth replaces Utah Hockey Club).

References:
- ESPN team abbreviations (probe response, 2026-04-27)
- Odds API icehockey_nhl team names (consistent with team display name)
- Polymarket NHL question patterns (mostly mascot-only, e.g. "Bruins vs. Sabres")
"""
from __future__ import annotations

# Canonical: ESPN abbreviation -> {name, mascot, [alt_abbrs], [former_names]}
NHL_TEAMS: dict[str, dict] = {
    "ANA": {"name": "Anaheim Ducks",         "mascot": "Ducks"},
    "BOS": {"name": "Boston Bruins",          "mascot": "Bruins"},
    "BUF": {"name": "Buffalo Sabres",         "mascot": "Sabres"},
    "CGY": {"name": "Calgary Flames",         "mascot": "Flames"},
    "CAR": {"name": "Carolina Hurricanes",    "mascot": "Hurricanes"},
    "CHI": {"name": "Chicago Blackhawks",     "mascot": "Blackhawks"},
    "COL": {"name": "Colorado Avalanche",     "mascot": "Avalanche"},
    "CBJ": {"name": "Columbus Blue Jackets",  "mascot": "Blue Jackets"},
    "DAL": {"name": "Dallas Stars",           "mascot": "Stars"},
    "DET": {"name": "Detroit Red Wings",      "mascot": "Red Wings"},
    "EDM": {"name": "Edmonton Oilers",        "mascot": "Oilers"},
    "FLA": {"name": "Florida Panthers",       "mascot": "Panthers"},
    "LA":  {"name": "Los Angeles Kings",      "mascot": "Kings",          "alt_abbrs": ["LAK"]},
    "MIN": {"name": "Minnesota Wild",         "mascot": "Wild"},
    "MTL": {"name": "Montreal Canadiens",     "mascot": "Canadiens"},
    "NSH": {"name": "Nashville Predators",    "mascot": "Predators"},
    "NJ":  {"name": "New Jersey Devils",      "mascot": "Devils",         "alt_abbrs": ["NJD"]},
    "NYI": {"name": "New York Islanders",     "mascot": "Islanders"},
    "NYR": {"name": "New York Rangers",       "mascot": "Rangers"},
    "OTT": {"name": "Ottawa Senators",        "mascot": "Senators"},
    "PHI": {"name": "Philadelphia Flyers",    "mascot": "Flyers"},
    "PIT": {"name": "Pittsburgh Penguins",    "mascot": "Penguins"},
    "SJ":  {"name": "San Jose Sharks",        "mascot": "Sharks",         "alt_abbrs": ["SJS"]},
    "SEA": {"name": "Seattle Kraken",         "mascot": "Kraken"},
    "STL": {"name": "St. Louis Blues",        "mascot": "Blues"},
    "TB":  {"name": "Tampa Bay Lightning",    "mascot": "Lightning",      "alt_abbrs": ["TBL"]},
    "TOR": {"name": "Toronto Maple Leafs",    "mascot": "Maple Leafs"},
    "UTA": {"name": "Utah Mammoth",           "mascot": "Mammoth",
            "former_names": ["Utah Hockey Club"]},
    "VAN": {"name": "Vancouver Canucks",      "mascot": "Canucks"},
    "VGK": {"name": "Vegas Golden Knights",   "mascot": "Golden Knights"},
    "WSH": {"name": "Washington Capitals",    "mascot": "Capitals"},
    "WPG": {"name": "Winnipeg Jets",          "mascot": "Jets"},
}


def _build_lookup_map() -> dict[str, str]:
    """Build flat normalized-string -> canonical abbr lookup."""
    lookup: dict[str, str] = {}
    for abbr, info in NHL_TEAMS.items():
        lookup[abbr.upper()] = abbr
        lookup[info["name"].upper()] = abbr
        lookup[info["mascot"].upper()] = abbr
        for alt in info.get("alt_abbrs", []):
            lookup[alt.upper()] = abbr
        for former in info.get("former_names", []):
            lookup[former.upper()] = abbr
    return lookup


_LOOKUP: dict[str, str] = _build_lookup_map()


def resolve_nhl_team(query: str) -> str | None:
    """
    Resolve a team name/abbreviation/mascot to canonical ESPN abbr.

    Args:
        query: e.g. "Bruins", "Boston Bruins", "BOS", "Utah Hockey Club"

    Returns:
        Canonical ESPN abbr (e.g. "BOS"), or None if no match.
    """
    if not query or not isinstance(query, str):
        return None
    return _LOOKUP.get(query.strip().upper())


def get_team_info(abbr: str) -> dict | None:
    """Return full team info dict by canonical abbr."""
    if not abbr or not isinstance(abbr, str):
        return None
    return NHL_TEAMS.get(abbr.strip().upper())
