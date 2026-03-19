"""PandaScore API client for esports match data (CS2, LoL, Dota2, Valorant)."""
from __future__ import annotations
import logging
import os
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

PANDASCORE_BASE = "https://api.pandascore.co"

# Map Polymarket tags/keywords to PandaScore game slugs
_GAME_SLUGS = {
    "counter-strike": "csgo",
    "cs2": "csgo",
    "cs:go": "csgo",
    "csgo": "csgo",
    "league-of-legends": "lol",
    "lol": "lol",
    "dota": "dota2",
    "dota2": "dota2",
    "valorant": "valorant",
}

# Common team name aliases for fuzzy matching
_TEAM_ALIASES = {
    "navi": "natus vincere",
    "natus vincere": "natus vincere",
    "g2": "g2 esports",
    "faze": "faze clan",
    "nip": "ninjas in pyjamas",
    "vitality": "team vitality",
    "spirit": "team spirit",
    "liquid": "team liquid",
    "c9": "cloud9",
    "cloud9": "cloud9",
    "col": "complexity",
    "eg": "evil geniuses",
    "og": "og",
    "fnatic": "fnatic",
    "mouz": "mousesports",
    "ence": "ence",
    "heroic": "heroic",
    "astralis": "astralis",
    "big": "big",
    "eternal fire": "eternal fire",
}


class EsportsDataClient:
    """Fetches team stats and match history from PandaScore free tier."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or os.getenv("PANDASCORE_API_KEY", "")
        self._last_call: float = 0.0
        self._cache: Dict[str, Tuple[object, float]] = {}  # key -> (data, timestamp)
        self._cache_ttl = 1800  # 30 min cache

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _rate_limit(self) -> None:
        """PandaScore free tier: 1000 req/hr ≈ 1 req/3.6s. We use 1 req/2s."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        self._last_call = time.monotonic()

    def _get(self, endpoint: str, params: dict = None) -> Optional[list]:
        """Make authenticated GET request to PandaScore."""
        if not self.available:
            return None
        cache_key = f"{endpoint}:{params}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        self._rate_limit()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = requests.get(
                f"{PANDASCORE_BASE}{endpoint}",
                headers=headers,
                params=params or {},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = (data, time.monotonic())
            return data
        except requests.RequestException as e:
            logger.warning("PandaScore API error: %s", e)
            return None

    def detect_game(self, question: str, tags: List[str]) -> Optional[str]:
        """Detect which esports game a market is about. Returns PandaScore slug."""
        q_lower = question.lower()
        tags_lower = [t.lower() for t in tags]

        # Check tags first
        for tag in tags_lower:
            for keyword, slug in _GAME_SLUGS.items():
                if keyword in tag:
                    return slug

        # Check question text
        for keyword, slug in _GAME_SLUGS.items():
            if keyword in q_lower:
                return slug

        return None

    def _extract_team_names(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract two team names from a 'Team A vs Team B' style question."""
        q = question.strip()
        # Remove common prefixes like "Counter-Strike: "
        for prefix in ["Counter-Strike:", "CS2:", "Valorant:", "LoL:", "Dota 2:"]:
            if q.startswith(prefix):
                q = q[len(prefix):].strip()

        # Split on "vs" or "vs."
        for sep in [" vs. ", " vs ", " versus "]:
            if sep in q.lower():
                idx = q.lower().index(sep)
                team_a = q[:idx].strip()
                team_b = q[idx + len(sep):].strip()
                # Remove tournament info in parentheses
                for t in [team_a, team_b]:
                    if "(" in t:
                        t = t[:t.index("(")].strip()
                # Clean up trailing tournament info after " - "
                if " - " in team_b:
                    team_b = team_b[:team_b.index(" - ")].strip()
                return team_a, team_b

        return None, None

    def _fuzzy_match_team(self, name: str, candidates: List[dict]) -> Optional[dict]:
        """Find best matching team from PandaScore results using fuzzy matching."""
        name_lower = name.lower().strip()

        # Check aliases first
        canonical = _TEAM_ALIASES.get(name_lower, name_lower)

        best_match = None
        best_score = 0.0

        for team in candidates:
            team_name = team.get("name", "").lower()
            team_acronym = (team.get("acronym") or "").lower()
            team_slug = team.get("slug", "").lower()

            # Exact matches
            if canonical == team_name or canonical == team_acronym or canonical == team_slug:
                return team

            # Fuzzy match on name
            score = SequenceMatcher(None, canonical, team_name).ratio()
            if score > best_score:
                best_score = score
                best_match = team

            # Also try acronym
            if team_acronym:
                score2 = SequenceMatcher(None, canonical, team_acronym).ratio()
                if score2 > best_score:
                    best_score = score2
                    best_match = team

        if best_score >= 0.6:
            return best_match
        return None

    def get_team_recent_results(
        self, game_slug: str, team_name: str, limit: int = 20
    ) -> Optional[Dict]:
        """Fetch a team's recent match results from PandaScore.

        Returns dict with: team_name, wins, losses, win_rate, recent_matches
        """
        # Search for team
        teams = self._get(f"/{game_slug}/teams", {"search[name]": team_name, "per_page": 5})
        if not teams:
            return None

        team = self._fuzzy_match_team(team_name, teams)
        if not team:
            logger.debug("Could not match team '%s' in PandaScore", team_name)
            return None

        team_id = team["id"]
        official_name = team.get("name", team_name)

        # Fetch past matches for this team
        matches = self._get(
            f"/{game_slug}/matches/past",
            {"filter[opponent_id]": team_id, "per_page": limit, "sort": "-scheduled_at"},
        )
        if not matches:
            return {"team_name": official_name, "wins": 0, "losses": 0,
                    "win_rate": 0.0, "recent_matches": []}

        wins = 0
        losses = 0
        recent = []
        for m in matches:
            winner = m.get("winner", {})
            won = winner and winner.get("id") == team_id
            if won:
                wins += 1
            else:
                losses += 1

            # Find opponent name
            opponents = m.get("opponents", [])
            opp_name = "Unknown"
            for opp in opponents:
                opp_team = opp.get("opponent", {})
                if opp_team.get("id") != team_id:
                    opp_name = opp_team.get("name", "Unknown")
                    break

            results = m.get("results", [])
            score_str = ""
            if len(results) == 2:
                score_str = f"{results[0].get('score', '?')}-{results[1].get('score', '?')}"

            recent.append({
                "opponent": opp_name,
                "won": won,
                "score": score_str,
                "tournament": m.get("tournament", {}).get("name", ""),
                "date": (m.get("scheduled_at") or "")[:10],
            })

        total = wins + losses
        return {
            "team_name": official_name,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total, 2) if total > 0 else 0.0,
            "recent_matches": recent[:10],  # Last 10 for context
        }

    def get_match_context(
        self, question: str, tags: List[str]
    ) -> Optional[str]:
        """Build a structured context string for the AI analyst.

        Returns None if not an esports market or no data available.
        """
        game_slug = self.detect_game(question, tags)
        if not game_slug:
            return None

        team_a_name, team_b_name = self._extract_team_names(question)
        if not team_a_name or not team_b_name:
            logger.debug("Could not extract team names from: %s", question[:60])
            return None

        logger.info("Fetching esports data: %s vs %s (%s)", team_a_name, team_b_name, game_slug)

        team_a = self.get_team_recent_results(game_slug, team_a_name)
        team_b = self.get_team_recent_results(game_slug, team_b_name)

        if not team_a and not team_b:
            return None

        parts = [f"=== ESPORTS MATCH DATA (PandaScore) ==="]

        for label, stats in [("TEAM A", team_a), ("TEAM B", team_b)]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue
            total = stats["wins"] + stats["losses"]
            parts.append(
                f"\n{label}: {stats['team_name']}\n"
                f"  Record (last {total} matches): {stats['wins']}W - {stats['losses']}L "
                f"(win rate: {stats['win_rate']:.0%})"
            )
            if stats["recent_matches"]:
                parts.append("  Recent matches:")
                for m in stats["recent_matches"][:5]:
                    result = "W" if m["won"] else "L"
                    parts.append(
                        f"    [{result}] vs {m['opponent']} {m['score']} "
                        f"({m['tournament']}, {m['date']})"
                    )

        # Head-to-head (scan recent matches for direct matchups)
        if team_a and team_b:
            h2h_a = 0
            h2h_b = 0
            for m in (team_a.get("recent_matches") or []):
                if team_b and m["opponent"].lower() == team_b["team_name"].lower():
                    if m["won"]:
                        h2h_a += 1
                    else:
                        h2h_b += 1
            if h2h_a + h2h_b > 0:
                parts.append(
                    f"\nHEAD-TO-HEAD (recent): "
                    f"{team_a['team_name']} {h2h_a} - {h2h_b} {team_b['team_name']}"
                )

        parts.append("\nUse this data to inform your probability estimate. "
                     "Weight recent form heavily.")
        return "\n".join(parts)
