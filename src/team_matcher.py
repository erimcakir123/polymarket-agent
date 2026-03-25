"""Centralized team name matching — replaces unsafe low-threshold fuzzy matching.

Three-stage matching:
1. Exact / Alias lookup (confidence 1.0)
2. Token-based overlap (confidence 0.85-0.90)
3. High-threshold fuzzy fallback (confidence >= 0.80)

Old thresholds (0.40-0.60) caused wrong team matches → wrong odds → wrong trades.
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

# Known aliases — exact match (lowercase key → canonical name)
TEAM_ALIASES: dict[str, str] = {
    # NBA
    "lakers": "los angeles lakers", "la lakers": "los angeles lakers",
    "celtics": "boston celtics", "boston": "boston celtics",
    "warriors": "golden state warriors", "gsw": "golden state warriors",
    "bucks": "milwaukee bucks", "sixers": "philadelphia 76ers",
    "76ers": "philadelphia 76ers", "knicks": "new york knicks",
    "nets": "brooklyn nets", "heat": "miami heat",
    "nuggets": "denver nuggets", "suns": "phoenix suns",
    "mavs": "dallas mavericks", "mavericks": "dallas mavericks",
    "thunder": "oklahoma city thunder", "okc": "oklahoma city thunder",
    "wolves": "minnesota timberwolves", "timberwolves": "minnesota timberwolves",
    "cavs": "cleveland cavaliers", "cavaliers": "cleveland cavaliers",
    "clips": "la clippers", "clippers": "la clippers",
    "rockets": "houston rockets", "grizzlies": "memphis grizzlies",
    "pelicans": "new orleans pelicans", "hawks": "atlanta hawks",
    "bulls": "chicago bulls", "pacers": "indiana pacers",
    "magic": "orlando magic", "raptors": "toronto raptors",
    "wizards": "washington wizards", "pistons": "detroit pistons",
    "hornets": "charlotte hornets", "kings": "sacramento kings",
    "blazers": "portland trail blazers", "trail blazers": "portland trail blazers",
    "jazz": "utah jazz", "spurs": "san antonio spurs",
    # Soccer
    "man utd": "manchester united", "man u": "manchester united",
    "mufc": "manchester united", "man city": "manchester city",
    "mcfc": "manchester city", "liverpool": "liverpool fc",
    "lfc": "liverpool fc", "chelsea": "chelsea fc", "cfc": "chelsea fc",
    "arsenal": "arsenal fc", "afc": "arsenal fc",
    "tottenham": "tottenham hotspur",
    "real": "real madrid", "real madrid": "real madrid",
    "barca": "fc barcelona", "barcelona": "fc barcelona", "fcb": "fc barcelona",
    "bayern": "bayern munich", "bayern munich": "bayern munich",
    "psg": "paris saint-germain", "inter": "inter milan",
    "inter milan": "inter milan", "juve": "juventus", "juventus": "juventus fc",
    "atletico": "atletico madrid", "atleti": "atletico madrid",
    "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
    # CS2 / Esports
    "navi": "natus vincere", "na'vi": "natus vincere",
    "g2": "g2 esports", "faze": "faze clan", "vitality": "team vitality",
    "spirit": "team spirit", "heroic": "heroic",
    "mouz": "mouz", "mousesports": "mouz",
    "col": "complexity gaming", "complexity": "complexity gaming",
    "c9": "cloud9", "cloud9": "cloud9", "liquid": "team liquid",
    "eg": "evil geniuses",
    # Tennis (usually full names, but abbreviations exist)
    "djokovic": "novak djokovic", "nole": "novak djokovic",
    "nadal": "rafael nadal", "rafa": "rafael nadal",
    "alcaraz": "carlos alcaraz", "sinner": "jannik sinner",
    "medvedev": "daniil medvedev",
    # NHL
    "leafs": "toronto maple leafs", "maple leafs": "toronto maple leafs",
    "habs": "montreal canadiens", "canadiens": "montreal canadiens",
    "bruins": "boston bruins", "rangers": "new york rangers",
    "pens": "pittsburgh penguins", "penguins": "pittsburgh penguins",
    "caps": "washington capitals", "capitals": "washington capitals",
    "oilers": "edmonton oilers", "flames": "calgary flames",
    "canucks": "vancouver canucks", "avs": "colorado avalanche",
    "avalanche": "colorado avalanche",
    # NFL
    "chiefs": "kansas city chiefs", "eagles": "philadelphia eagles",
    "niners": "san francisco 49ers", "49ers": "san francisco 49ers",
    "cowboys": "dallas cowboys", "bills": "buffalo bills",
    "ravens": "baltimore ravens", "bengals": "cincinnati bengals",
    "lions": "detroit lions", "dolphins": "miami dolphins",
    "steelers": "pittsburgh steelers", "chargers": "los angeles chargers",
    "seahawks": "seattle seahawks", "vikings": "minnesota vikings",
    "packers": "green bay packers", "saints": "new orleans saints",
    "bucs": "tampa bay buccaneers", "buccaneers": "tampa bay buccaneers",
    "rams": "los angeles rams", "bears": "chicago bears",
    "jaguars": "jacksonville jaguars", "jags": "jacksonville jaguars",
    "titans": "tennessee titans", "texans": "houston texans",
    "commanders": "washington commanders", "panthers": "carolina panthers",
    "broncos": "denver broncos", "raiders": "las vegas raiders",
    "colts": "indianapolis colts", "cardinals": "arizona cardinals",
    "falcons": "atlanta falcons", "giants": "new york giants",
    "jets": "new york jets", "browns": "cleveland browns",
    # MLB
    "yankees": "new york yankees", "red sox": "boston red sox",
    "dodgers": "los angeles dodgers", "astros": "houston astros",
    "braves": "atlanta braves", "mets": "new york mets",
    "phillies": "philadelphia phillies", "cubs": "chicago cubs",
    "white sox": "chicago white sox", "guardians": "cleveland guardians",
    "padres": "san diego padres", "mariners": "seattle mariners",
    "twins": "minnesota twins", "orioles": "baltimore orioles",
    "rays": "tampa bay rays", "blue jays": "toronto blue jays",
    "royals": "kansas city royals", "reds": "cincinnati reds",
    "pirates": "pittsburgh pirates", "brewers": "milwaukee brewers",
    "diamondbacks": "arizona diamondbacks", "dbacks": "arizona diamondbacks",
    "rockies": "colorado rockies", "nationals": "washington nationals",
    "angels": "los angeles angels", "athletics": "oakland athletics",
    "a's": "oakland athletics", "marlins": "miami marlins",
    "tigers": "detroit tigers",
}

# Noise suffixes to strip for normalization
_STRIP_SUFFIXES = (" fc", " sc", " esports", " gaming", " clan", " team")


def _normalize(name: str) -> str:
    """Lowercase, strip whitespace and common suffixes."""
    name = name.lower().strip()
    for suffix in _STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


def _canonicalize(name: str) -> str:
    """Resolve through alias dict if possible."""
    n = _normalize(name)
    return TEAM_ALIASES.get(n, n)


def match_team(query: str, candidate: str) -> tuple[bool, float, str]:
    """Three-stage team matching.

    Returns: (is_match, confidence, method)
    """
    q = _normalize(query)
    c = _normalize(candidate)

    # Stage 1: Exact / Alias
    if _canonicalize(query) == _canonicalize(candidate):
        return True, 1.0, "exact_alias"

    # Stage 2: Token-based
    q_tokens = set(q.split())
    c_tokens = set(c.split())
    noise = {"team", "the", "of", "de", "fc", "sc", "city"}

    # Single-word query → substring check in candidate tokens
    if len(q_tokens) == 1:
        q_word = list(q_tokens)[0]
        if q_word not in noise and (q_word in c_tokens or any(q_word in ct for ct in c_tokens)):
            return True, 0.90, "token_substring"

    # Multi-word → meaningful overlap
    if len(q_tokens) > 1 and len(c_tokens) > 1:
        overlap = q_tokens & c_tokens
        meaningful = overlap - noise
        if meaningful and len(overlap) / min(len(q_tokens), len(c_tokens)) >= 0.5:
            return True, 0.85, "token_overlap"

    # Stage 3: Fuzzy — HIGH threshold only
    score = SequenceMatcher(None, q, c).ratio()
    if score >= 0.80:
        return True, score, "fuzzy"

    return False, score, "no_match"


def match_team_pair(
    query_a: str, query_b: str,
    candidate_a: str, candidate_b: str,
) -> tuple[bool, float]:
    """Match two team pairs. Both teams must match individually.

    Tries normal order first, then swapped (home/away reversal).
    Returns: (is_match, min_confidence)
    """
    # Normal order
    ma, ca, _ = match_team(query_a, candidate_a)
    mb, cb, _ = match_team(query_b, candidate_b)
    if ma and mb:
        return True, min(ca, cb)

    # Swapped order
    ma2, ca2, _ = match_team(query_a, candidate_b)
    mb2, cb2, _ = match_team(query_b, candidate_a)
    if ma2 and mb2:
        return True, min(ca2, cb2)

    return False, 0.0


def find_best_event_match(
    team_a: str,
    team_b: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
) -> Optional[tuple[dict, float]]:
    """Find the best matching event for a team pair.

    Args:
        team_a, team_b: Polymarket team names
        events: List of event dicts from Odds API / ESPN
        home_key, away_key: Keys for team names in event dicts
        min_confidence: Minimum match confidence

    Returns:
        (best_event, confidence) or None
    """
    best_event = None
    best_conf = 0.0

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue

        is_match, conf = match_team_pair(team_a, team_b, home, away)
        if is_match and conf > best_conf:
            best_conf = conf
            best_event = event

    if best_event and best_conf >= min_confidence:
        return best_event, best_conf

    return None
