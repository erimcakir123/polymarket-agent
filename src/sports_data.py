"""ESPN API client for traditional sports data (NBA, NCAA, NFL, MLB, NHL, soccer)."""
from __future__ import annotations
import logging
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call

logger = logging.getLogger(__name__)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

# Map Polymarket slug prefixes and keywords to ESPN sport/league paths
_SPORT_LEAGUES = {
    # slug prefix -> (sport, league, display_name)
    "cbb": ("basketball", "mens-college-basketball", "NCAA Basketball"),
    "ncaab": ("basketball", "mens-college-basketball", "NCAA Basketball"),
    "nba": ("basketball", "nba", "NBA"),
    "nfl": ("football", "nfl", "NFL"),
    "cfb": ("football", "college-football", "College Football"),
    "ncaaf": ("football", "college-football", "College Football"),
    "mlb": ("baseball", "mlb", "MLB"),
    "nhl": ("hockey", "nhl", "NHL"),
    "ufc": ("mma", "ufc", "UFC"),
    "mma": ("mma", "ufc", "UFC"),
    "epl": ("soccer", "eng.1", "Premier League"),
    "laliga": ("soccer", "esp.1", "La Liga"),
    "seriea": ("soccer", "ita.1", "Serie A"),
    "bundesliga": ("soccer", "ger.1", "Bundesliga"),
    "ligue1": ("soccer", "fra.1", "Ligue 1"),
    "ucl": ("soccer", "uefa.champions", "Champions League"),
}

# Keywords in question text -> (sport, league)
_QUESTION_KEYWORDS = {
    "ncaa": ("basketball", "mens-college-basketball"),
    "march madness": ("basketball", "mens-college-basketball"),
    "college basketball": ("basketball", "mens-college-basketball"),
    "nba": ("basketball", "nba"),
    "nfl": ("football", "nfl"),
    "super bowl": ("football", "nfl"),
    "mlb": ("baseball", "mlb"),
    "nhl": ("hockey", "nhl"),
    "premier league": ("soccer", "eng.1"),
    "la liga": ("soccer", "esp.1"),
    "serie a": ("soccer", "ita.1"),
    "bundesliga": ("soccer", "ger.1"),
    "champions league": ("soccer", "uefa.champions"),
    "ufc": ("mma", "ufc"),
}


class SportsDataClient:
    """Fetches team stats and recent results from ESPN (free, no API key)."""

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 1800  # 30 min
        self._last_call: float = 0.0

    def _rate_limit(self) -> None:
        """Gentle rate limit: 1 req/sec."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_call = time.monotonic()

    def _get(self, url: str) -> Optional[dict]:
        """GET request with caching."""
        cached = self._cache.get(url)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        self._rate_limit()
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            record_call("espn")
            data = resp.json()
            self._cache[url] = (data, time.monotonic())
            return data
        except requests.RequestException as e:
            logger.warning("ESPN API error: %s", e)
            return None

    def detect_sport(self, question: str, slug: str, tags: List[str]) -> Optional[Tuple[str, str]]:
        """Detect sport/league from market data. Returns (sport, league) or None."""
        # Check slug prefix first (most reliable)
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_LEAGUES:
            sport, league, _ = _SPORT_LEAGUES[slug_prefix]
            return (sport, league)

        # Check question text
        q_lower = question.lower()
        for keyword, (sport, league) in _QUESTION_KEYWORDS.items():
            if keyword in q_lower:
                return (sport, league)

        # Check tags
        tags_lower = " ".join(t.lower() for t in tags)
        for keyword, (sport, league) in _QUESTION_KEYWORDS.items():
            if keyword in tags_lower:
                return (sport, league)

        return None

    def _search_team(self, sport: str, league: str, team_name: str) -> Optional[dict]:
        """Search for a team by name in ESPN's team list."""
        url = f"{ESPN_BASE}/{sport}/{league}/teams?limit=500"
        data = self._get(url)
        if not data:
            return None

        teams = []
        for group in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
            team = group.get("team", {})
            if team:
                teams.append(team)

        if not teams:
            return None

        name_lower = team_name.lower().strip()
        best_match = None
        best_score = 0.0

        for team in teams:
            full_name = team.get("displayName", "").lower()
            short_name = team.get("shortDisplayName", "").lower()
            abbrev = team.get("abbreviation", "").lower()
            nickname = team.get("nickname", "").lower()
            location = team.get("location", "").lower()

            # Exact matches
            if name_lower in (full_name, short_name, abbrev, nickname, location):
                return team

            # Check if search term is contained in any name
            if name_lower in full_name or full_name in name_lower:
                return team

            # Fuzzy match
            for candidate in [full_name, short_name, nickname, location]:
                if not candidate:
                    continue
                score = SequenceMatcher(None, name_lower, candidate).ratio()
                if score > best_score:
                    best_score = score
                    best_match = team

        if best_score >= 0.55:
            return best_match
        return None

    def get_team_record(self, sport: str, league: str, team_name: str) -> Optional[Dict]:
        """Get team's season record and recent results.

        Returns dict with: team_name, record, recent_games, standing
        """
        team = self._search_team(sport, league, team_name)
        if not team:
            logger.debug("Could not find team '%s' in ESPN %s/%s", team_name, sport, league)
            return None

        team_id = team.get("id")
        official_name = team.get("displayName", team_name)

        # Get record + standing from team detail endpoint
        record_str = ""
        standing = ""
        detail_url = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}"
        team_detail = self._get(detail_url)
        if team_detail:
            team_data = team_detail.get("team", {})
            record_items = team_data.get("record", {}).get("items", [])
            if record_items:
                record_str = record_items[0].get("summary", "")
            if team_data.get("rank"):
                standing = f"Seed #{team_data['rank']}"
            stand_summary = team_data.get("standingSummary", "")
            if stand_summary:
                standing = stand_summary

        # Get recent games from schedule (seasontype=2 for regular season)
        recent_games = []
        schedule_url = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/schedule?seasontype=2"
        schedule_data = self._get(schedule_url)
        if schedule_data:
            events = schedule_data.get("events", [])
            completed = [
                e for e in events
                if e.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed", False)
            ]
            for event in completed[-10:]:
                game_info = self._parse_game(event, str(team_id))
                if game_info:
                    recent_games.append(game_info)
        # Also check postseason (seasontype=3) for tournament games
        post_url = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/schedule?seasontype=3"
        post_data = self._get(post_url)
        if post_data:
            for event in post_data.get("events", []):
                if event.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed", False):
                    game_info = self._parse_game(event, str(team_id))
                    if game_info:
                        recent_games.append(game_info)

        return {
            "team_name": official_name,
            "record": record_str,
            "standing": standing,
            "recent_games": recent_games,
        }

    def _parse_game(self, event: dict, team_id: str) -> Optional[Dict]:
        """Parse a single game event into a result dict."""
        try:
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) != 2:
                return None

            team_comp = None
            opp_comp = None
            for c in competitors:
                if str(c.get("id", "")) == str(team_id):
                    team_comp = c
                else:
                    opp_comp = c

            if not team_comp or not opp_comp:
                return None

            team_score = int(team_comp.get("score", {}).get("value", 0)
                           if isinstance(team_comp.get("score"), dict)
                           else team_comp.get("score", 0))
            opp_score = int(opp_comp.get("score", {}).get("value", 0)
                          if isinstance(opp_comp.get("score"), dict)
                          else opp_comp.get("score", 0))

            won = team_comp.get("winner", False)
            opp_name = opp_comp.get("team", {}).get("displayName", "Unknown")
            home_away = "H" if team_comp.get("homeAway") == "home" else "A"
            date = event.get("date", "")[:10]

            return {
                "opponent": opp_name,
                "won": won,
                "score": f"{team_score}-{opp_score}",
                "home_away": home_away,
                "date": date,
            }
        except (ValueError, TypeError, KeyError):
            return None

    def _extract_teams_from_question(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from 'Team A vs Team B' style question."""
        q = question.strip()
        # Try "vs" split
        for sep in [" vs. ", " vs ", " versus "]:
            if sep in q.lower():
                idx = q.lower().index(sep)
                team_a = q[:idx].strip()
                team_b = q[idx + len(sep):].strip()
                # Remove trailing stuff like "(Match)", " - Tournament", ": O/U 238.5"
                for char in ["(", " -", ":"]:
                    if char in team_a:
                        team_a = team_a[:team_a.index(char)].strip()
                    if char in team_b:
                        team_b = team_b[:team_b.index(char)].strip()
                # Remove "Will " prefix
                if team_a.lower().startswith("will "):
                    team_a = team_a[5:].strip()
                return team_a, team_b
        return None, None

    def _extract_teams_from_slug(self, slug: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team abbreviations from slug like 'cbb-missr-mia-2026-03-20'."""
        parts = slug.split("-")
        if len(parts) < 3:
            return None, None
        # Skip prefix (cbb, nba, etc.) and date parts at the end
        # Date parts are 4-digit year, 2-digit month/day
        non_date = []
        _SLUG_STOP = {"total", "over", "under", "spread", "ml", "moneyline", "pt5", "pts"}
        for p in parts[1:]:
            if len(p) == 4 and p.isdigit():
                break  # hit the date
            if p.lower() in _SLUG_STOP:
                break  # hit O/U or spread suffix
            non_date.append(p)
        if len(non_date) >= 2:
            return non_date[0], non_date[1]
        return None, None

    def get_match_context(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Build structured context string for AI analyst.

        Returns None if not a traditional sport or no data available.
        """
        sport_league = self.detect_sport(question, slug, tags)
        if not sport_league:
            return None

        sport, league = sport_league
        league_name = ""
        for prefix, (s, l, name) in _SPORT_LEAGUES.items():
            if s == sport and l == league:
                league_name = name
                break

        # Try question first for full team names, fall back to slug abbreviations
        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)

        # Use slug abbreviations as backup search terms
        if not team_a_name and slug_a:
            team_a_name = slug_a
        if not team_b_name and slug_b:
            team_b_name = slug_b

        if not team_a_name or not team_b_name:
            logger.debug("Could not extract team names from: %s / %s", question[:60], slug)
            return None

        logger.info("Fetching ESPN data: %s vs %s (%s)", team_a_name, team_b_name, league_name)

        team_a = self.get_team_record(sport, league, team_a_name)
        team_b = self.get_team_record(sport, league, team_b_name)

        if not team_a and not team_b:
            # Try slug abbreviations if question names failed
            if slug_a and slug_a != team_a_name:
                team_a = self.get_team_record(sport, league, slug_a)
            if slug_b and slug_b != team_b_name:
                team_b = self.get_team_record(sport, league, slug_b)

        if not team_a and not team_b:
            return None

        parts = [f"=== SPORTS DATA (ESPN) — {league_name} ==="]

        for label, stats in [("TEAM A", team_a), ("TEAM B", team_b)]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue

            header = f"\n{label}: {stats['team_name']}"
            if stats["record"]:
                header += f" ({stats['record']})"
            if stats["standing"]:
                header += f" — {stats['standing']}"
            parts.append(header)

            if stats["recent_games"]:
                # Calculate recent form
                recent_5 = stats["recent_games"][-5:]
                wins = sum(1 for g in recent_5 if g["won"])
                parts.append(f"  Last 5: {wins}W-{5-wins}L")
                parts.append("  Recent games:")
                for g in stats["recent_games"][-5:]:
                    result = "W" if g["won"] else "L"
                    parts.append(
                        f"    [{result}] {g['home_away']} vs {g['opponent']} "
                        f"{g['score']} ({g['date']})"
                    )

        parts.append("\nUse team records, recent form, and seeding to inform your estimate. "
                     "Weight recent form and home/away performance.")
        return "\n".join(parts)
