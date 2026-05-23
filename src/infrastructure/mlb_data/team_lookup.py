"""MLB takım kısaltma ↔ Stats API team_id lookup (sabit veri).

Slug formatı (`mlb-cle-phi-2026-05-22-total-9pt5`) takım kısaltmaları kullanır
ama Stats API `get_schedule()` `home_team_id`/`away_team_id` döndürür. Bu modül
çeviri sağlar.

Reference: https://statsapi.mlb.com/api/v1/teams (sportId=1, 30 MLB takımı)
"""
from __future__ import annotations


# Stats API team_id'leri (statsapi.mlb.com/api/v1/teams sportId=1).
# 30 MLB takımı (sabit, sayı yıllardır değişmez).
TEAM_ABBREVIATIONS: dict[str, int] = {
    # AL East
    "bal": 110,  # Baltimore Orioles
    "bos": 111,  # Boston Red Sox
    "nyy": 147,  # New York Yankees
    "tb": 139,   # Tampa Bay Rays
    "tor": 141,  # Toronto Blue Jays
    # AL Central
    "cws": 145,  # Chicago White Sox
    "cle": 114,  # Cleveland Guardians
    "det": 116,  # Detroit Tigers
    "kc": 118,   # Kansas City Royals
    "min": 142,  # Minnesota Twins
    # AL West
    "hou": 117,  # Houston Astros
    "laa": 108,  # Los Angeles Angels
    "oak": 133,  # Oakland Athletics
    "sea": 136,  # Seattle Mariners
    "tex": 140,  # Texas Rangers
    # NL East
    "atl": 144,  # Atlanta Braves
    "mia": 146,  # Miami Marlins
    "nym": 121,  # New York Mets
    "phi": 143,  # Philadelphia Phillies
    "wsh": 120,  # Washington Nationals
    # NL Central
    "chc": 112,  # Chicago Cubs
    "cin": 113,  # Cincinnati Reds
    "mil": 158,  # Milwaukee Brewers
    "pit": 134,  # Pittsburgh Pirates
    "stl": 138,  # St. Louis Cardinals
    # NL West
    "ari": 109,  # Arizona Diamondbacks
    "col": 115,  # Colorado Rockies
    "lad": 119,  # Los Angeles Dodgers
    "sd": 135,   # San Diego Padres
    "sf": 137,   # San Francisco Giants
}

_REVERSE: dict[int, str] = {v: k for k, v in TEAM_ABBREVIATIONS.items()}


def abbreviation_to_team_id(abbr: str) -> int | None:
    """`cle` → 114 (Cleveland Guardians team_id). Bilinmeyen → None.

    Input case-insensitive (CLE, cle, Cle hepsi çalışır).
    """
    return TEAM_ABBREVIATIONS.get((abbr or "").lower())


def team_id_to_abbreviation(team_id: int) -> str | None:
    """114 → `cle` (Cleveland Guardians abbr). Bilinmeyen → None."""
    return _REVERSE.get(team_id)
