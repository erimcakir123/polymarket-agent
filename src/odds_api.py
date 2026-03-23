"""The Odds API client — bookmaker odds as 'ultimate' second opinion.

Free tier: 500 requests/month. Used ONLY when AI confidence is low/medium
on sports markets to compare against sharp bookmaker lines.
"""
from __future__ import annotations
import logging
import os
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call

logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Map Polymarket slug prefixes to Odds API sport keys
_SPORT_KEYS = {
    "cbb": "basketball_ncaab",
    "ncaab": "basketball_ncaab",
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
    "cfb": "americanfootball_ncaaf",
    "ncaaf": "americanfootball_ncaaf",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "ufc": "mma_mixed_martial_arts",
    "mma": "mma_mixed_martial_arts",
    "epl": "soccer_epl",
    "laliga": "soccer_spain_la_liga",
    "seriea": "soccer_italy_serie_a",
    "bundesliga": "soccer_germany_bundesliga",
    "ligue1": "soccer_france_ligue_one",
    "ucl": "soccer_uefa_champions_league",
}

# Keywords in question text -> sport key
_QUESTION_SPORT_KEYS = {
    "ncaa": "basketball_ncaab",
    "march madness": "basketball_ncaab",
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "premier league": "soccer_epl",
    "la liga": "soccer_spain_la_liga",
    "serie a": "soccer_italy_serie_a",
    "bundesliga": "soccer_germany_bundesliga",
    "champions league": "soccer_uefa_champions_league",
    "ufc": "mma_mixed_martial_arts",
}


class OddsAPIClient:
    """Fetches bookmaker odds from The Odds API (500 req/month free tier).

    Used as an 'ultimate ability' — only activated when AI is uncertain.
    """

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 3600  # 1 hour cache (save quota)
        self._requests_used = 0

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _detect_sport_key(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Detect The Odds API sport key from market data."""
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_KEYS:
            return _SPORT_KEYS[slug_prefix]

        q_lower = question.lower()
        for keyword, sport_key in _QUESTION_SPORT_KEYS.items():
            if keyword in q_lower:
                return sport_key

        return None

    def _get(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Make authenticated GET to The Odds API with caching."""
        if not self.available:
            return None

        cache_key = f"{endpoint}:{sorted(params.items())}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        params["apiKey"] = self.api_key
        try:
            resp = requests.get(f"{ODDS_API_BASE}{endpoint}", params=params, timeout=10)
            resp.raise_for_status()

            # Track remaining quota from headers
            remaining = resp.headers.get("x-requests-remaining", "?")
            used = resp.headers.get("x-requests-used", "?")
            logger.info("Odds API quota: %s used, %s remaining", used, remaining)
            self._requests_used += 1
            record_call("odds_api")

            data = resp.json()
            self._cache[cache_key] = (data, time.monotonic())
            return data
        except requests.RequestException as e:
            logger.warning("Odds API error: %s", e)
            if "401" in str(e):
                logger.warning("Odds API key invalid/expired — disabling for this session")
                self.api_key = ""
            return None

    def get_bookmaker_odds(
        self, question: str, slug: str, tags: List[str]
    ) -> Optional[Dict]:
        """Get bookmaker implied probability for a sports match.

        Returns dict with: team_a, team_b, bookmaker_avg_prob_a, bookmaker_avg_prob_b,
                          num_bookmakers, odds_summary
        Or None if not a sports market / no data.
        """
        sport_key = self._detect_sport_key(question, slug, tags)
        if not sport_key:
            return None

        # Fetch odds for this sport
        events = self._get(f"/sports/{sport_key}/odds", {
            "regions": "us,eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
        })
        if not events:
            return None

        # Extract team names from question
        team_a_name, team_b_name = self._extract_teams(question)
        if not team_a_name or not team_b_name:
            return None

        # Find matching event
        best_event = None
        best_score = 0.0
        for event in events:
            home = event.get("home_team", "").lower()
            away = event.get("away_team", "").lower()

            score_a = max(
                SequenceMatcher(None, team_a_name.lower(), home).ratio(),
                SequenceMatcher(None, team_a_name.lower(), away).ratio(),
            )
            score_b = max(
                SequenceMatcher(None, team_b_name.lower(), home).ratio(),
                SequenceMatcher(None, team_b_name.lower(), away).ratio(),
            )
            combined = (score_a + score_b) / 2
            if combined > best_score:
                best_score = combined
                best_event = event

        if best_score < 0.4 or not best_event:
            logger.debug("No matching event for '%s vs %s' (best=%.2f)",
                         team_a_name, team_b_name, best_score)
            return None

        # Calculate average implied probability across bookmakers
        home_team = best_event.get("home_team", "")
        away_team = best_event.get("away_team", "")

        # Figure out which Polymarket team maps to home/away
        home_is_a = SequenceMatcher(None, team_a_name.lower(), home_team.lower()).ratio() > \
                     SequenceMatcher(None, team_a_name.lower(), away_team.lower()).ratio()

        probs_team_a = []
        probs_team_b = []
        bookmaker_names = []

        for bookmaker in best_event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = market.get("outcomes", [])
                home_odds = None
                away_odds = None
                for outcome in outcomes:
                    if outcome.get("name") == home_team:
                        home_odds = outcome.get("price", 0)
                    elif outcome.get("name") == away_team:
                        away_odds = outcome.get("price", 0)

                if home_odds and away_odds and home_odds > 0 and away_odds > 0:
                    # Convert decimal odds to implied probability
                    home_prob = 1 / home_odds
                    away_prob = 1 / away_odds
                    # Normalize (remove vig)
                    total = home_prob + away_prob
                    home_prob /= total
                    away_prob /= total

                    if home_is_a:
                        probs_team_a.append(home_prob)
                        probs_team_b.append(away_prob)
                    else:
                        probs_team_a.append(away_prob)
                        probs_team_b.append(home_prob)
                    bookmaker_names.append(bookmaker.get("title", ""))

        if not probs_team_a:
            return None

        avg_a = sum(probs_team_a) / len(probs_team_a)
        avg_b = sum(probs_team_b) / len(probs_team_b)

        return {
            "team_a": team_a_name,
            "team_b": team_b_name,
            "bookmaker_prob_a": round(avg_a, 3),
            "bookmaker_prob_b": round(avg_b, 3),
            "num_bookmakers": len(probs_team_a),
            "bookmakers": bookmaker_names[:5],
        }

    def build_odds_context(self, odds: Dict) -> str:
        """Build context string for AI from bookmaker odds."""
        return (
            f"\n=== BOOKMAKER ODDS (The Odds API) ===\n"
            f"  {odds['team_a']}: {odds['bookmaker_prob_a']:.0%} implied probability\n"
            f"  {odds['team_b']}: {odds['bookmaker_prob_b']:.0%} implied probability\n"
            f"  Sources: {odds['num_bookmakers']} bookmakers ({', '.join(odds['bookmakers'])})\n"
            f"  NOTE: Bookmaker lines reflect sharp money. Large disagreement with "
            f"Polymarket = potential edge or Polymarket inefficiency."
        )

    def _extract_teams(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from question."""
        q = question.strip()
        for sep in [" vs. ", " vs ", " versus "]:
            if sep in q.lower():
                idx = q.lower().index(sep)
                a = q[:idx].strip()
                b = q[idx + len(sep):].strip()
                for char in ["(", " -"]:
                    if char in a:
                        a = a[:a.index(char)].strip()
                    if char in b:
                        b = b[:b.index(char)].strip()
                if a.lower().startswith("will "):
                    a = a[5:].strip()
                return a, b
        return None, None
