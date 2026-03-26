"""TheSportsDB client — fallback team stats for international sports not covered by ESPN.

Free API, no key required. Covers national teams, World Cup qualifiers, and smaller leagues.
Used as fallback when ESPN returns no data for a market.
"""
from __future__ import annotations
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_BASE = "https://www.thesportsdb.com/api/v1/json/3"
_CACHE_TTL = 3600  # 1 hour


class TheSportsDBClient:
    """Fetch team stats from TheSportsDB (free, no API key)."""

    def __init__(self) -> None:
        self._team_cache: Dict[str, Tuple[Optional[str], float]] = {}   # name → (id, ts)
        self._events_cache: Dict[str, Tuple[list, float]] = {}          # team_id → (events, ts)

    def _get(self, url: str, params: dict | None = None) -> Optional[dict]:
        """Make a GET request, return JSON or None on error."""
        try:
            resp = requests.get(url, params=params, timeout=8)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException as exc:
            logger.debug("TheSportsDB request failed: %s", exc)
        return None

    def _search_team_id(self, team_name: str) -> Optional[str]:
        """Search for a team by name, return its idTeam or None."""
        key = team_name.lower().strip()
        cached_id, cached_ts = self._team_cache.get(key, (None, 0.0))
        if time.time() - cached_ts < _CACHE_TTL:
            return cached_id

        data = self._get(f"{_BASE}/searchteams.php", {"t": team_name})
        team_id = None
        if data and data.get("teams"):
            team_id = str(data["teams"][0]["idTeam"])

        self._team_cache[key] = (team_id, time.time())
        return team_id

    def _get_recent_events(self, team_id: str) -> List[dict]:
        """Fetch last 5 events for a team."""
        cached_events, cached_ts = self._events_cache.get(team_id, ([], 0.0))
        if time.time() - cached_ts < _CACHE_TTL:
            return cached_events

        data = self._get(f"{_BASE}/eventslast.php", {"id": team_id})
        events = []
        if data and data.get("results"):
            for ev in data["results"]:
                try:
                    home_id = str(ev.get("idHomeTeam", ""))
                    is_home = home_id == team_id
                    home_score = int(ev.get("intHomeScore") or 0)
                    away_score = int(ev.get("intAwayScore") or 0)
                    won = (is_home and home_score > away_score) or (
                        not is_home and away_score > home_score
                    )
                    opponent = ev.get("strAwayTeam" if is_home else "strHomeTeam", "Unknown")
                    score = f"{home_score}-{away_score}" if is_home else f"{away_score}-{home_score}"
                    events.append({
                        "opponent": opponent,
                        "won": won,
                        "score": score,
                        "home_away": "H" if is_home else "A",
                        "date": ev.get("dateEvent", "")[:10],
                        "league": ev.get("strLeague", ""),
                    })
                except (ValueError, TypeError, KeyError):
                    continue

        self._events_cache[team_id] = (events, time.time())
        return events

    def _extract_teams(self, question: str) -> Tuple[str, str]:
        """Extract two team names from a market question.

        Handles patterns like:
          "Team A vs Team B: Who will win?"
          "Will Team A beat Team B?"
          "Team A to defeat Team B"
        Returns (team_a, team_b) or ("", "") if extraction fails.
        """
        q = question.strip()

        # Pattern: "X vs Y" or "X v Y"
        m = re.search(r"^(.+?)\s+vs?\.?\s+(.+?)(?::\s*who|\?|$)", q, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Pattern: "Will X beat/defeat/win against Y"
        m = re.search(
            r"will\s+(.+?)\s+(?:beat|defeat|win\s+against|beat|eliminate)\s+(.+?)[\?$]",
            q, re.IGNORECASE,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Pattern: "X to beat/defeat Y"
        m = re.search(r"(.+?)\s+to\s+(?:beat|defeat|win)\s+(.+?)[\?$]", q, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        return "", ""

    def get_match_context(self, question: str) -> Optional[str]:
        """Build a context string for a market question.

        Returns a formatted string with both teams' recent results,
        or None if team extraction or API lookup fails.
        """
        team_a_name, team_b_name = self._extract_teams(question)
        if not team_a_name or not team_b_name:
            logger.debug("TheSportsDB: could not extract teams from: %s", question[:60])
            return None

        team_a_id = self._search_team_id(team_a_name)
        team_b_id = self._search_team_id(team_b_name)

        if not team_a_id and not team_b_id:
            logger.debug("TheSportsDB: neither team found: %s vs %s", team_a_name, team_b_name)
            return None

        parts = ["=== SPORTS DATA (TheSportsDB) ==="]

        for label, name, team_id in [
            ("TEAM A", team_a_name, team_a_id),
            ("TEAM B", team_b_name, team_b_id),
        ]:
            parts.append(f"\n{label}: {name}")
            if not team_id:
                parts.append("  No data found")
                continue

            events = self._get_recent_events(team_id)
            if not events:
                parts.append("  No recent match data")
                continue

            wins = sum(1 for e in events if e["won"])
            total = len(events)
            parts.append(f"  Last {total}: {wins}W-{total - wins}L")
            if events[0].get("league"):
                parts.append(f"  Competition: {events[0]['league']}")
            parts.append("  Recent games:")
            for ev in events:
                result = "W" if ev["won"] else "L"
                parts.append(
                    f"    [{result}] {ev['home_away']} vs {ev['opponent']} "
                    f"{ev['score']} ({ev['date']})"
                )

        parts.append("\nUse recent form to assess current team strength.")
        return "\n".join(parts)
