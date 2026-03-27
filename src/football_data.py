"""football-data.org client — ESPN fallback for soccer + Copa Libertadores.

Free tier: 12 competitions (PL, ELC, PD, SA, BL1, FL1, DED, PPL, CL, EC, WC, BSA)
+ Copa Libertadores (CLI, TIER_FOUR but works on this key).
Rate limit: 10 requests/minute.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call

logger = logging.getLogger(__name__)

_BASE = "https://api.football-data.org/v4"

# Map Polymarket slug prefixes → football-data.org competition codes
_SLUG_TO_COMPETITION: Dict[str, str] = {
    # England
    "epl": "PL",
    "championship": "ELC", "elc": "ELC",
    # Spain
    "laliga": "PD",
    # Italy
    "seriea": "SA",
    # Germany
    "bundesliga": "BL1",
    # France
    "ligue1": "FL1",
    # Netherlands
    "eredivisie": "DED", "ere": "DED",
    # Portugal
    "primeira": "PPL",
    # Brazil
    "brasileirao": "BSA", "bra": "BSA",
    # UEFA
    "ucl": "CL",
    # Copa Libertadores (unique to this API — ESPN doesn't cover it)
    "libertadores": "CLI", "copa": "CLI",
}

# Question text keywords → competition code
_KEYWORD_TO_COMPETITION: Dict[str, str] = {
    "premier league": "PL",
    "championship": "ELC", "efl championship": "ELC",
    "la liga": "PD",
    "serie a": "SA",
    "bundesliga": "BL1",
    "ligue 1": "FL1",
    "eredivisie": "DED",
    "primeira liga": "PPL",
    "brasileirao": "BSA",
    "champions league": "CL",
    "copa libertadores": "CLI",
}

# Competition code → display name
_COMPETITION_NAMES: Dict[str, str] = {
    "PL": "Premier League",
    "ELC": "EFL Championship",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "BSA": "Brasileirao Serie A",
    "CL": "Champions League",
    "CLI": "Copa Libertadores",
    "EC": "European Championship",
    "WC": "FIFA World Cup",
}


class FootballDataClient:
    """Fetch soccer match data from football-data.org (free, API key required)."""

    def __init__(self) -> None:
        self._api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 1800  # 30 min
        self._last_call: float = 0.0
        self.available = bool(self._api_key)
        if not self.available:
            logger.info("FootballData: no API key, client disabled")

    def _rate_limit(self) -> None:
        """Rate limit: max 10 req/min → 1 req per 6 seconds."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < 6.0:
            time.sleep(6.0 - elapsed)
        self._last_call = time.monotonic()

    def _get(self, path: str) -> Optional[dict]:
        """GET request with caching and auth header."""
        url = f"{_BASE}{path}"
        cached = self._cache.get(url)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        self._rate_limit()
        try:
            resp = requests.get(
                url,
                headers={"X-Auth-Token": self._api_key},
                timeout=10,
            )
            resp.raise_for_status()
            record_call("football_data")
            data = resp.json()
            self._cache[url] = (data, time.monotonic())
            return data
        except requests.RequestException as e:
            logger.warning("football-data.org error: %s", e)
            return None

    def detect_competition(self, question: str, slug: str) -> Optional[str]:
        """Detect competition code from slug prefix or question keywords."""
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SLUG_TO_COMPETITION:
            return _SLUG_TO_COMPETITION[slug_prefix]

        q_lower = question.lower()
        for keyword, code in _KEYWORD_TO_COMPETITION.items():
            if keyword in q_lower:
                return code

        return None

    def get_team_standings(self, competition: str, team_name: str) -> Optional[Dict]:
        """Get team's league standing and recent form."""
        data = self._get(f"/competitions/{competition}/standings")
        if not data:
            return None

        standings = data.get("standings", [])
        if not standings:
            return None

        # Use first standings table (TOTAL, not HOME/AWAY)
        table = None
        for s in standings:
            if s.get("type") == "TOTAL":
                table = s.get("table", [])
                break
        if not table and standings:
            table = standings[0].get("table", [])
        if not table:
            return None

        # Find team by name matching
        team_lower = team_name.lower().strip()
        for row in table:
            team_obj = row.get("team", {})
            names = [
                team_obj.get("name", "").lower(),
                team_obj.get("shortName", "").lower(),
                team_obj.get("tla", "").lower(),
            ]
            if team_lower in names or any(team_lower in n or n in team_lower for n in names if n):
                return {
                    "team_name": team_obj.get("name", team_name),
                    "position": row.get("position"),
                    "played": row.get("playedGames"),
                    "won": row.get("won"),
                    "draw": row.get("draw"),
                    "lost": row.get("lost"),
                    "goals_for": row.get("goalsFor"),
                    "goals_against": row.get("goalsAgainst"),
                    "points": row.get("points"),
                    "form": row.get("form"),  # e.g. "W,W,L,D,W"
                }

        return None

    def get_team_matches(self, competition: str, team_name: str,
                         status: str = "FINISHED") -> List[Dict]:
        """Get recent matches for a team in a competition."""
        data = self._get(f"/competitions/{competition}/matches?status={status}")
        if not data:
            return []

        team_lower = team_name.lower().strip()
        matches = []

        for match in data.get("matches", []):
            home = match.get("homeTeam", {})
            away = match.get("awayTeam", {})

            home_names = [home.get("name", "").lower(), home.get("shortName", "").lower(),
                          home.get("tla", "").lower()]
            away_names = [away.get("name", "").lower(), away.get("shortName", "").lower(),
                          away.get("tla", "").lower()]

            is_home = any(team_lower in n or n in team_lower for n in home_names if n)
            is_away = any(team_lower in n or n in team_lower for n in away_names if n)

            if not is_home and not is_away:
                continue

            score = match.get("score", {}).get("fullTime", {})
            home_goals = score.get("home")
            away_goals = score.get("away")

            if home_goals is None or away_goals is None:
                continue

            if is_home:
                won = home_goals > away_goals
                opponent = away.get("shortName") or away.get("name", "?")
                score_str = f"{home_goals}-{away_goals}"
            else:
                won = away_goals > home_goals
                opponent = home.get("shortName") or home.get("name", "?")
                score_str = f"{away_goals}-{home_goals}"

            matches.append({
                "opponent": opponent,
                "won": won,
                "draw": home_goals == away_goals,
                "score": score_str,
                "home_away": "H" if is_home else "A",
                "date": match.get("utcDate", "")[:10],
                "matchday": match.get("matchday"),
            })

        return matches[-10:]  # last 10

    def get_match_context(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Build context string for AI analyst — same interface as SportsDataClient."""
        if not self.available:
            return None

        competition = self.detect_competition(question, slug)
        if not competition:
            return None

        comp_name = _COMPETITION_NAMES.get(competition, competition)

        # Extract team names from question
        team_a, team_b = self._extract_teams(question)
        if not team_a or not team_b:
            return None

        logger.info("Fetching football-data.org: %s vs %s (%s)", team_a, team_b, comp_name)

        parts = [f"=== SPORTS DATA (football-data.org) — {comp_name} ==="]

        for label, name in [("TEAM A", team_a), ("TEAM B", team_b)]:
            standing = self.get_team_standings(competition, name)
            recent = self.get_team_matches(competition, name)

            if not standing and not recent:
                parts.append(f"\n{label}: {name} — No data available")
                continue

            header = f"\n{label}: "
            if standing:
                header += (f"{standing['team_name']} — "
                           f"#{standing['position']} "
                           f"({standing['won']}W-{standing['draw']}D-{standing['lost']}L, "
                           f"{standing['points']}pts)")
                if standing.get("form"):
                    header += f" Form: {standing['form']}"
            else:
                header += name
            parts.append(header)

            if recent:
                wins = sum(1 for m in recent[-5:] if m["won"])
                draws = sum(1 for m in recent[-5:] if m["draw"])
                losses = 5 - wins - draws
                parts.append(f"  Last 5: {wins}W-{draws}D-{losses}L")
                parts.append("  Recent games:")
                for m in recent[-5:]:
                    result = "W" if m["won"] else ("D" if m["draw"] else "L")
                    parts.append(
                        f"    [{result}] {m['home_away']} vs {m['opponent']} "
                        f"{m['score']} ({m['date']})"
                    )

        parts.append("\nUse standings, form, and recent results to inform your estimate.")
        return "\n".join(parts)

    def get_upcoming_matches(self, competition: str) -> List[Dict]:
        """Get scheduled matches for a competition (for scout scheduler)."""
        data = self._get(f"/competitions/{competition}/matches?status=SCHEDULED,TIMED")
        if not data:
            return []

        matches = []
        for match in data.get("matches", []):
            home = match.get("homeTeam", {})
            away = match.get("awayTeam", {})
            if not home.get("name") or not away.get("name"):
                continue
            matches.append({
                "home": home.get("shortName") or home.get("name"),
                "away": away.get("shortName") or away.get("name"),
                "date": match.get("utcDate", ""),
                "competition": competition,
                "matchday": match.get("matchday"),
                "stage": match.get("stage"),
            })
        return matches

    @staticmethod
    def _extract_teams(question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from 'Team A vs Team B' question."""
        q = question.strip()
        for sep in [" vs. ", " vs ", " versus "]:
            if sep in q.lower():
                idx = q.lower().index(sep)
                team_a = q[:idx].strip()
                team_b = q[idx + len(sep):].strip()
                for char in ["(", " -", ":", "?"]:
                    if char in team_a:
                        team_a = team_a[:team_a.index(char)].strip()
                    if char in team_b:
                        team_b = team_b[:team_b.index(char)].strip()
                if team_a.lower().startswith("will "):
                    team_a = team_a[5:].strip()
                return team_a, team_b
        return None, None
