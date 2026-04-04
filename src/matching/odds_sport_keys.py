"""Polymarket slug/tag -> The Odds API sport key mapping.

Single source of truth for resolving Polymarket market identifiers
to Odds API sport keys. Used by odds_api.py for sport detection.

Odds API sport keys from: https://the-odds-api.com/sports-odds-data/sports-apis.html
Polymarket slug prefixes from: src/matching/sport_classifier.py
Polymarket Gamma tags from: src/sports_data.py _SERIES_TO_ESPN
"""
from __future__ import annotations

import re
from typing import Optional

# ── Polymarket slug prefix -> Odds API sport key ─────────────────────────
_SLUG_TO_ODDS: dict[str, str] = {
    # American sports
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "nfl": "americanfootball_nfl",
    "cfb": "americanfootball_ncaaf",
    # MMA
    "ufc": "mma_mixed_martial_arts",
    # Soccer — England
    "epl": "soccer_epl",
    "efa": "soccer_fa_cup",
    "efl": "soccer_efl_champ",
    # Soccer — Spain
    "lal": "soccer_spain_la_liga",
    "cde": "soccer_spain_copa_del_rey",
    "cdr": "soccer_spain_copa_del_rey",
    # Soccer — Germany
    "bun": "soccer_germany_bundesliga",
    "bl2": "soccer_germany_bundesliga2",
    "dfb": "soccer_germany_dfb_pokal",
    # Soccer — Italy
    "sea": "soccer_italy_serie_a",
    "ser": "soccer_italy_serie_a",
    "itc": "soccer_italy_coppa_italia",
    # Soccer — France
    "fl1": "soccer_france_ligue_one",
    "fr2": "soccer_france_ligue_two",
    "cof": "soccer_france_coupe_de_france",
    # Soccer — Other Europe
    "ere": "soccer_netherlands_eredivisie",
    "por": "soccer_portugal_primeira_liga",
    "tur": "soccer_turkey_super_league",
    "sco": "soccer_spl",
    "bel": "soccer_belgium_first_div",
    "den": "soccer_denmark_superliga",
    "nor": "soccer_norway_eliteserien",
    "swe": "soccer_sweden_allsvenskan",
    "rus": "soccer_russia_premier_league",
    "gre": "soccer_greece_super_league",
    "aut": "soccer_austria_bundesliga",
    # Soccer — Americas
    "mls": "soccer_usa_mls",
    "arg": "soccer_argentina_primera_division",
    "bra": "soccer_brazil_campeonato",
    "bra2": "soccer_brazil_serie_b",
    "mex": "soccer_mexico_ligamx",
    "col": "soccer_chile_campeonato",
    "col1": "soccer_chile_campeonato",
    "chi": "soccer_chile_campeonato",
    "chi1": "soccer_chile_campeonato",
    # Soccer — Asia/Middle East
    "spl": "soccer_saudi_arabia_pro_league",
    "kor": "soccer_korea_kleague1",
    "jpn": "soccer_japan_j_league",
    # Soccer — Cups/International
    "ucl": "soccer_uefa_champs_league",
    "uel": "soccer_uefa_europa_league",
    "uecl": "soccer_uefa_europa_conference_league",
    "lib": "soccer_conmebol_copa_libertadores",
    "sud": "soccer_conmebol_copa_sudamericana",
    "fif": "soccer_fifa_world_cup",
    "euro": "soccer_uefa_european_championship",
    "con": "soccer_conmebol_copa_libertadores",
    "gold": "soccer_concacaf_gold_cup",
    # Soccer — Australia
    "aus": "soccer_australia_aleague",
}

# ── Polymarket Gamma series tag -> Odds API sport key ────────────────────
_TAG_TO_ODDS: dict[str, str] = {
    # Soccer
    "premier-league": "soccer_epl",
    "la-liga": "soccer_spain_la_liga",
    "la-liga-2": "soccer_spain_segunda_division",
    "bundesliga": "soccer_germany_bundesliga",
    "serie-a": "soccer_italy_serie_a",
    "ligue-1": "soccer_france_ligue_one",
    "eredivisie": "soccer_netherlands_eredivisie",
    "primeira-liga": "soccer_portugal_primeira_liga",
    "super-lig": "soccer_turkey_super_league",
    "scottish-premiership": "soccer_spl",
    "belgian-pro-league": "soccer_belgium_first_div",
    "danish-superliga": "soccer_denmark_superliga",
    "eliteserien": "soccer_norway_eliteserien",
    "allsvenskan": "soccer_sweden_allsvenskan",
    "greek-super-league": "soccer_greece_super_league",
    "austrian-bundesliga": "soccer_austria_bundesliga",
    "russian-premier-league": "soccer_russia_premier_league",
    "saudi-professional-league": "soccer_saudi_arabia_pro_league",
    "k-league": "soccer_korea_kleague1",
    "j1-league": "soccer_japan_j_league",
    "a-league": "soccer_australia_aleague",
    "liga-mx": "soccer_mexico_ligamx",
    "liga-betplay": "soccer_chile_campeonato",
    "brasileirao": "soccer_brazil_campeonato",
    "brazil-serie-b": "soccer_brazil_serie_b",
    "mls": "soccer_usa_mls",
    # Soccer — Cups
    "champions-league": "soccer_uefa_champs_league",
    "europa-league": "soccer_uefa_europa_league",
    "conference-league": "soccer_uefa_europa_conference_league",
    "copa-libertadores": "soccer_conmebol_copa_libertadores",
    "copa-sudamericana": "soccer_conmebol_copa_sudamericana",
    "fa-cup": "soccer_fa_cup",
    "efl-cup": "soccer_england_efl_cup",
    "dfb-pokal": "soccer_germany_dfb_pokal",
    "copa-del-rey": "soccer_spain_copa_del_rey",
    "coppa-italia": "soccer_italy_coppa_italia",
    "coupe-de-france": "soccer_france_coupe_de_france",
    # Non-soccer (tag fallbacks)
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "nfl": "americanfootball_nfl",
}


def slug_to_odds_key(slug_prefix: str) -> Optional[str]:
    """Map a Polymarket slug prefix to an Odds API sport key."""
    return _SLUG_TO_ODDS.get(slug_prefix.lower().strip()) if slug_prefix else None


def tag_to_odds_key(tag: str) -> Optional[str]:
    """Map a Polymarket Gamma series tag to an Odds API sport key.
    Strips year suffixes (e.g. "serie-a-2025" -> "serie-a") before lookup.
    """
    if not tag:
        return None
    tag_lower = tag.lower().strip()
    if tag_lower in _TAG_TO_ODDS:
        return _TAG_TO_ODDS[tag_lower]
    stripped = re.sub(r"-\d{4}$", "", tag_lower)
    if stripped != tag_lower and stripped in _TAG_TO_ODDS:
        return _TAG_TO_ODDS[stripped]
    return None


def resolve_odds_key(slug: Optional[str], tags: Optional[list[str]]) -> Optional[str]:
    """Resolve Odds API sport key from slug + tags. Slug wins, tags are fallback."""
    prefix = slug.split("-")[0].lower() if slug else ""
    result = slug_to_odds_key(prefix)
    if result:
        return result
    _tags: list[str] = tags if tags else []
    for tag in _tags:
        result = tag_to_odds_key(tag)
        if result:
            return result
    return None


def is_soccer_key(sport_key: Optional[str]) -> bool:
    """Return True if the Odds API sport key is a soccer league."""
    if not sport_key:
        return False
    return sport_key.startswith("soccer_")
