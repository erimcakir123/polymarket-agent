"""Odds API key / Polymarket tag → internal sport key alias tablosu.

_normalize() tarafından kullanılır. Zincir yasak — her değer SPORT_RULES'da olmalı.
"""
from __future__ import annotations

# Odds API key → internal sport key aliases (TDD §7.1 MVP)
_ALIASES: dict[str, str] = {
    # Basketball
    "basketball_nba": "nba",
    "basketball_wnba": "wnba",
    "basketball_ncaab": "ncaab",
    "basketball_wncaab": "ncaab",
    "basketball_euroleague": "euroleague",
    "basketball_nbl": "nbl",
    "basketball": "nba",
    # American Football
    "americanfootball_ncaaf": "nfl",
    "americanfootball_cfl": "nfl",
    "americanfootball_ufl": "nfl",
    "americanfootball": "nfl",
    # Ice Hockey
    "icehockey_nhl": "nhl",
    "icehockey_ahl": "ahl",
    "icehockey_liiga": "liiga",
    "icehockey_mestis": "mestis",
    "icehockey_sweden_hockey_league": "shl",
    "icehockey_sweden_allsvenskan": "allsvenskan",
    "icehockey": "nhl",
    # Baseball
    "baseball_mlb": "mlb",
    "baseball_milb": "mlb",
    "baseball_npb": "npb",
    "baseball_kbo": "kbo",
    "baseball_ncaa": "mlb",
    "baseball": "mlb",
    # Tennis
    "tennis_atp": "tennis",
    "tennis_wta": "tennis_wta",
    # Combat sports
    "mma_ufc": "mma",
    "ufc": "mma",
    "boxing": "mma",
    # Golf
    "golf_lpga_tour": "golf",
    "golf_liv_tour": "golf",
    # Cricket Polymarket/OddsAPI aliases (SPEC-011)
    "indian-premier-league": "cricket_ipl",
    "international-cricket": "cricket_international_t20",
    "cricket_test": "cricket",  # defensive — test cricket not directly supported
    # Soccer aliases (SPEC-015) — common Polymarket tags → soccer
    "epl": "soccer",
    "premier-league": "soccer",
    "la-liga": "soccer",
    "la-liga-2": "soccer",
    "bundesliga": "soccer",
    "serie-a": "soccer",
    "ligue-1": "soccer",
    "champions-league": "soccer",
    "europa-league": "soccer",
    "conference-league": "soccer",
    "mls": "soccer",
    "eredivisie": "soccer",
    "primeira-liga": "soccer",
    "super-lig": "soccer",
    "brasileirao": "soccer",
    "argentine-primera-division": "soccer",
    "liga-mx": "soccer",
    "scottish-premiership": "soccer",
    "belgian-pro-league": "soccer",
    "danish-superliga": "soccer",
    "eliteserien": "soccer",
    "allsvenskan-soccer": "soccer",
    "greek-super-league": "soccer",
    "austrian-bundesliga": "soccer",
    "russian-premier-league": "soccer",
    "saudi-professional-league": "soccer",
    "k-league": "soccer",
    "j1-league": "soccer",
    "a-league": "soccer",
    "chinese-super-league": "soccer",
    "thai-league": "soccer",
    "indian-super-league": "soccer",
    "egyptian-premier-league": "soccer",
    "polish-ekstraklasa": "soccer",
    "czech-first-league": "soccer",
    "romanian-liga-i": "soccer",
    "ukrainian-premier-league": "soccer",
    "croatian-football-league": "soccer",
    "colombian-primera-a": "soccer",
    "peruvian-liga-1": "soccer",
    "uruguayan-primera-division": "soccer",
    "ecuadorian-ligapro": "soccer",
    "fa-cup": "soccer",
    "efl-cup": "soccer",
    "dfb-pokal": "soccer",
    "copa-del-rey": "soccer",
    "coppa-italia": "soccer",
    "coupe-de-france": "soccer",
    "copa-libertadores": "soccer",
    "copa-sudamericana": "soccer",
    "nwsl": "soccer",
    # Rugby aliases (SPEC-015)
    "rugby": "rugby_union",
    "rugby-union": "rugby_union",
    "rugby-league": "rugby_union",
    "six-nations": "rugby_union",
    "premiership-rugby": "rugby_union",
    "nrl": "rugby_union",
    # Cricket Odds API keys (SPEC-011 Task 3)
    "cricket_bbl": "cricket_big_bash",
    "cricket_cpl": "cricket_caribbean_premier_league",
    "cricket_sa20": "cricket",           # SA20 not in MVP scope; fallback to generic T20 cricket
    "cricket_test_match": "cricket",     # Test matches out of scope; degrade gracefully
}
