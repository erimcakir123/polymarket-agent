"""CricketData.org (cricapi.com) client — cricket match data for IPL, PSL, T20.

Free tier: 500 requests/day.
Covers: IPL, PSL, T20 Internationals, ODI, Test matches.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call

logger = logging.getLogger(__name__)

_BASE = "https://api.cricapi.com/v1"

# Map Polymarket slug prefixes → series name keywords for filtering
_SLUG_TO_SERIES: Dict[str, str] = {
    "ipl": "indian premier league",
    "psl": "pakistan super league",
    "t20": "t20",
    "crint": "t20",
    "cricpakt20cup": "pakistan",
    "criclcl": "legends",
}

# Question text keywords → series name keywords
_KEYWORD_TO_SERIES: Dict[str, str] = {
    "ipl": "indian premier league",
    "psl": "pakistan super league",
    "t20": "t20",
    "pakistan": "pakistan",
    "india": "india",
}


class CricketDataClient:
    """Fetch cricket match data from CricketData.org (free, API key required)."""

    def __init__(self) -> None:
        self._api_key = os.getenv("CRICKET_DATA_API_KEY", "")
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 1800  # 30 min
        self._last_call: float = 0.0
        self.available = bool(self._api_key)
        if not self.available:
            logger.info("CricketData: no API key, client disabled")

    def _rate_limit(self) -> None:
        """Conservative rate limit: 1 req per 2 sec (100/day budget)."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        self._last_call = time.monotonic()

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[dict]:
        """GET request with caching and API key."""
        if not self.available:
            return None

        full_params = {"apikey": self._api_key}
        if params:
            full_params.update(params)

        cache_key = f"{endpoint}:{sorted(full_params.items())}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        self._rate_limit()
        try:
            resp = requests.get(f"{_BASE}/{endpoint}", params=full_params, timeout=10)
            resp.raise_for_status()
            record_call("cricket_data")
            data = resp.json()
            if data.get("status") != "success":
                logger.warning("CricketData API error: %s", data.get("status"))
                return None
            self._cache[cache_key] = (data, time.monotonic())
            return data
        except requests.RequestException as e:
            logger.warning("CricketData request failed: %s", e)
            return None

    def get_current_matches(self) -> List[Dict]:
        """Get all currently active/recent cricket matches."""
        data = self._get("currentMatches", {"offset": "0"})
        if not data:
            return []

        matches = []
        for m in data.get("data", []):
            teams = m.get("teams", [])
            if len(teams) < 2:
                continue

            team_info = m.get("teamInfo", [])
            shortnames = {}
            for ti in team_info:
                if ti.get("name") and ti.get("shortname"):
                    shortnames[ti["name"]] = ti["shortname"]

            # Parse score innings
            score_data = m.get("score", [])
            score_str = ""
            if score_data:
                innings = []
                for inn in score_data:
                    r = inn.get("r", 0)
                    w = inn.get("w", 0)
                    o = inn.get("o", 0)
                    innings.append(f"{r}/{w} ({o}ov)")
                score_str = " | ".join(innings)

            matches.append({
                "id": m.get("id", ""),
                "name": m.get("name", ""),
                "match_type": m.get("matchType", ""),
                "status": m.get("status", ""),
                "teams": teams,
                "shortnames": shortnames,
                "score": score_str,
                "date": m.get("date", ""),
                "venue": m.get("venue", ""),
                "started": m.get("matchStarted", False),
                "ended": m.get("matchEnded", False),
                "series_id": m.get("series_id", ""),
            })

        return matches

    def get_match_context(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Build context string for AI analyst — same interface as other data clients."""
        if not self.available:
            return None

        # Check if this is a cricket market
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        is_cricket = slug_prefix in _SLUG_TO_SERIES

        if not is_cricket:
            q_lower = question.lower()
            for kw in _KEYWORD_TO_SERIES:
                if kw in q_lower:
                    is_cricket = True
                    break

        if not is_cricket:
            tags_lower = " ".join(t.lower() for t in tags)
            if "cricket" in tags_lower:
                is_cricket = True

        if not is_cricket:
            return None

        # Extract team names
        team_a, team_b = self._extract_teams(question)
        if not team_a or not team_b:
            return None

        logger.info("Fetching CricketData: %s vs %s", team_a, team_b)

        # Get current matches and find the relevant one
        current = self.get_current_matches()
        matched_match = None
        team_a_lower = team_a.lower()
        team_b_lower = team_b.lower()

        for m in current:
            teams_lower = [t.lower() for t in m["teams"]]
            shortnames_lower = {k.lower(): v.lower() for k, v in m["shortnames"].items()}

            # Check if both teams are in this match
            a_found = any(
                team_a_lower in t or t in team_a_lower
                for t in teams_lower
            ) or any(
                team_a_lower in sn or sn in team_a_lower
                for sn in shortnames_lower.values()
            )
            b_found = any(
                team_b_lower in t or t in team_b_lower
                for t in teams_lower
            ) or any(
                team_b_lower in sn or sn in team_b_lower
                for sn in shortnames_lower.values()
            )

            if a_found and b_found:
                matched_match = m
                break

        parts = ["=== SPORTS DATA (CricketData) ==="]

        if matched_match:
            parts.append(f"\nMatch: {matched_match['name']}")
            parts.append(f"Type: {matched_match['match_type'].upper()}")
            parts.append(f"Venue: {matched_match['venue']}")
            parts.append(f"Status: {matched_match['status']}")
            if matched_match["score"]:
                parts.append(f"Score: {matched_match['score']}")
            if matched_match["started"] and not matched_match["ended"]:
                parts.append("State: LIVE")
            elif matched_match["ended"]:
                parts.append("State: COMPLETED")
            else:
                parts.append("State: UPCOMING")
        else:
            parts.append(f"\n{team_a} vs {team_b}")
            parts.append("No live/recent match data found for this fixture.")

        parts.append("\nUse match status, score, and format to inform your estimate.")
        return "\n".join(parts)

    def get_upcoming_matches(self) -> List[Dict]:
        """Get upcoming cricket matches (for scout scheduler)."""
        data = self._get("matches", {"offset": "0"})
        if not data:
            return []

        upcoming = []
        for m in data.get("data", []):
            if m.get("matchStarted"):
                continue
            teams = m.get("teams", [])
            if len(teams) < 2:
                continue
            upcoming.append({
                "teams": teams,
                "match_type": m.get("matchType", ""),
                "date": m.get("dateTimeGMT", m.get("date", "")),
                "name": m.get("name", ""),
                "series_id": m.get("series_id", ""),
            })

        return upcoming[:20]  # limit to 20 most relevant

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
