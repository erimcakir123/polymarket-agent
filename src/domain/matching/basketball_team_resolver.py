"""Polymarket slug ↔ NBA/WNBA team abbreviation eşlemesi.

Tennis player resolver paraleli (src/domain/matching/tennis_player_resolver.py).
Saf domain — I/O yok, sabit lookup tabloları.

Polymarket slug pattern'leri:
  - "nba-lal-gsw-2024-11-01" (3-harf abbreviation)
  - "nba-lakers-vs-warriors-2024-11-01" (full team adı)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# NBA team abbreviations + alternate full-name kelimeleri.
_NBA_TEAMS: dict[str, str] = {
    "lal": "LAL", "lakers": "LAL",
    "gsw": "GSW", "warriors": "GSW",
    "bos": "BOS", "celtics": "BOS",
    "lac": "LAC", "clippers": "LAC",
    "phx": "PHX", "suns": "PHX", "phoenix": "PHX",
    "den": "DEN", "nuggets": "DEN",
    "mia": "MIA", "heat": "MIA",
    "nyk": "NYK", "knicks": "NYK",
    "bkn": "BKN", "nets": "BKN", "brooklyn": "BKN",
    "phi": "PHI", "76ers": "PHI", "sixers": "PHI",
    "mil": "MIL", "bucks": "MIL",
    "tor": "TOR", "raptors": "TOR",
    "chi": "CHI", "bulls": "CHI",
    "cle": "CLE", "cavaliers": "CLE", "cavs": "CLE",
    "det": "DET", "pistons": "DET",
    "ind": "IND", "pacers": "IND",
    "atl": "ATL", "hawks": "ATL",
    "cha": "CHA", "hornets": "CHA",
    "orl": "ORL", "magic": "ORL",
    "was": "WAS", "wizards": "WAS",
    "sas": "SAS", "spurs": "SAS",
    "hou": "HOU", "rockets": "HOU",
    "mem": "MEM", "grizzlies": "MEM",
    "nop": "NOP", "pelicans": "NOP",
    "dal": "DAL", "mavericks": "DAL", "mavs": "DAL",
    "okc": "OKC", "thunder": "OKC",
    "min": "MIN", "timberwolves": "MIN", "wolves": "MIN",
    "por": "POR", "blazers": "POR", "trail": "POR",
    "sac": "SAC", "kings": "SAC",
    "uta": "UTA", "jazz": "UTA",
}

# WNBA 12 takım.
_WNBA_TEAMS: dict[str, str] = {
    "atl": "ATL", "dream": "ATL",
    "chi": "CHI", "sky": "CHI",
    "con": "CON", "sun": "CON", "connecticut": "CON",
    "dal": "DAL", "wings": "DAL",
    "ind": "IND", "fever": "IND",
    "las": "LAS", "sparks": "LAS",
    "lva": "LVA", "aces": "LVA", "vegas": "LVA",
    "min": "MIN", "lynx": "MIN",
    "nyl": "NYL", "liberty": "NYL",
    "phx": "PHX", "mercury": "PHX",
    "sea": "SEA", "storm": "SEA",
    "was": "WAS", "mystics": "WAS",
}


@dataclass(frozen=True)
class ResolveResult:
    home: Optional[str]
    away: Optional[str]
    ok: bool
    fail_reason: Optional[str] = None


def _lookup(league: str) -> dict[str, str]:
    if league == "nba":
        return _NBA_TEAMS
    if league == "wnba":
        return _WNBA_TEAMS
    return {}


def resolve_team_pair(slug: str, league: str) -> ResolveResult:
    """Polymarket slug'undan home/away abbreviation çıkar."""
    tbl = _lookup(league)
    if not tbl:
        return ResolveResult(None, None, False, f"unknown_league:{league}")
    parts = [p for p in slug.lower().split("-") if p and p not in {"vs", "v"}]
    found: list[str] = []
    for p in parts:
        if p in tbl:
            abbr = tbl[p]
            if abbr not in found:
                found.append(abbr)
        if len(found) == 2:
            break
    if len(found) < 2:
        return ResolveResult(None, None, False, f"teams_not_found:{slug}")
    return ResolveResult(home=found[0], away=found[1], ok=True)
