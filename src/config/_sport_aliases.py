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
    # Tennis kaldırıldı 2026-05-05 — matching katmanı domain/matching/tennis_*_resolver.py altında korunuyor
    # Combat sports
    "mma_ufc": "mma",
    "ufc": "mma",
    "boxing": "mma",
    # Golf
    "golf_lpga_tour": "golf",
    "golf_liv_tour": "golf",
}
