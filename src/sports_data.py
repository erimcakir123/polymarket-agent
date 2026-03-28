"""ESPN API client for traditional sports data (NBA, NCAA, NFL, MLB, NHL, soccer)."""
from __future__ import annotations
import logging
import time
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call
from src.team_matcher import match_team

logger = logging.getLogger(__name__)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

# Dynamic discovery replaces hardcoded mappings.
# ESPN search endpoint finds sport/league for any team name.
_SPORT_LEAGUES: dict = {}

# Dynamic discovery replaces hardcoded keyword mappings.
_QUESTION_KEYWORDS: dict = {}


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

    # ESPN search endpoint — free, no API key needed
    _SEARCH_URL = "https://site.web.api.espn.com/apis/common/v3/search"

    # Leagues to skip — women's leagues, cricket, rugby return wrong context
    _SKIP_LEAGUES = frozenset({
        "eng.w.fa", "eng.w.1", "eng.w.2",  # English women's
        "usa.w.1",  # NWSL
        "fifa.w.worldcup", "uefa.w.euro",   # Women's international
    })
    _SKIP_SPORTS = frozenset({"cricket", "rugby"})

    def search_team(self, team_name: str) -> Optional[Tuple[str, str]]:
        """Search ESPN for a team by name. Returns (sport, league) or None.

        Uses ESPN's free search endpoint to dynamically discover which
        sport/league a team belongs to, eliminating hardcoded mappings.
        Skips women's leagues, cricket, rugby. Prefers exact name matches.
        """
        if not team_name or len(team_name) < 2:
            return None

        cache_key = f"search:{team_name.lower().strip()}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        self._rate_limit()
        try:
            resp = requests.get(
                self._SEARCH_URL,
                params={"query": team_name, "limit": "10", "type": "team"},
                timeout=10,
            )
            resp.raise_for_status()
            record_call("espn")
            data = resp.json()

            query_lower = team_name.lower().strip()

            # Two-pass: first exact name matches, then any match
            # This prevents "York City" matching "New York City FC"
            for strict in (True, False):
                for item in data.get("items", []):
                    if item.get("type") != "team":
                        continue
                    sport = item.get("sport", "")
                    league = item.get("league", "") or item.get("defaultLeagueSlug", "")
                    if not sport or not league:
                        continue

                    # Skip women's leagues, cricket, rugby
                    if league in self._SKIP_LEAGUES:
                        continue
                    if sport in self._SKIP_SPORTS:
                        continue

                    # Strict pass: display name must match query
                    if strict:
                        display = item.get("displayName", "").lower()
                        if query_lower != display and query_lower not in display:
                            continue
                        # Reject if display has extra prefix (New York City FC vs York City)
                        if display != query_lower and not display.startswith(query_lower):
                            continue

                    result = (sport, league)
                    self._cache[cache_key] = (result, time.monotonic())
                    logger.info("ESPN search: '%s' -> %s/%s", team_name, sport, league)
                    return result

            # No results found
            self._cache[cache_key] = (None, time.monotonic())
            return None

        except requests.RequestException as e:
            logger.debug("ESPN search failed for '%s': %s", team_name, e)
            return None

    def detect_sport(self, question: str, slug: str, tags: List[str]) -> Optional[Tuple[str, str]]:
        """Detect sport/league from market data. Returns (sport, league) or None.

        Primary: ESPN search endpoint (dynamic discovery).
        Fallback: slug prefix or question keyword lookup (if any mappings exist).
        """
        # Try hardcoded lookups first (fast path — empty by default after refactor)
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_LEAGUES:
            sport, league, _ = _SPORT_LEAGUES[slug_prefix]
            return (sport, league)

        q_lower = question.lower()
        for keyword, (sport, league) in _QUESTION_KEYWORDS.items():
            if keyword in q_lower:
                return (sport, league)

        # Check tags (kept for backwards compatibility)
        tags_lower = " ".join(t.lower() for t in tags)
        for keyword, (sport, league) in _QUESTION_KEYWORDS.items():
            if keyword in tags_lower:
                return (sport, league)

        # Dynamic discovery via ESPN search
        team_a, team_b = self._extract_teams_from_question(question)

        # Only fall back to slug if question gave us nothing
        if not team_a and not team_b:
            team_a, team_b = self._extract_teams_from_slug(slug)
            # Slug abbreviations < 4 chars are too ambiguous (e.g. "bri" → NCAA)
            if team_a and len(team_a) < 4:
                team_a = None
            if team_b and len(team_b) < 4:
                team_b = None

        # Search with team names (prefer longer/more specific first)
        names = sorted([n for n in [team_a, team_b] if n], key=len, reverse=True)
        for name in names:
            result = self.search_team(name)
            if result:
                return result

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

            # Centralized team matcher (threshold 0.80, 3-stage matching)
            for candidate in [full_name, short_name, nickname, location]:
                if not candidate:
                    continue
                is_match, score, method = match_team(name_lower, candidate)
                if is_match and score > best_score:
                    best_score = score
                    best_match = team

        if best_score >= 0.80:
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

        # Get recent games from schedule
        # Soccer leagues don't support seasontype param — returns 0 events.
        # Try without seasontype first (works for soccer), then with seasontype=2 (works for NBA etc.)
        recent_games = []
        base_schedule = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/schedule"
        for sched_url in [base_schedule, f"{base_schedule}?seasontype=2", f"{base_schedule}?seasontype=3"]:
            sched_data = self._get(sched_url)
            if not sched_data:
                continue
            for event in sched_data.get("events", []):
                if event.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed", False):
                    game_info = self._parse_game(event, str(team_id))
                    if game_info and game_info not in recent_games:
                        recent_games.append(game_info)
        # Keep only last 10
        recent_games = recent_games[-10:]

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
        """Extract team names from various question formats.

        Handles: 'NBA: Team A vs Team B', 'Will Team A beat Team B?',
        'Team A vs Team B: Who will win?', 'Will Team A win on DATE?', etc.
        """
        import re
        q = question.strip()

        # Strip common prefixes like "NBA: ", "MLB: ", "KHL: ", "ELH: "
        q = re.sub(r'^[A-Za-z]{2,10}:\s*', '', q)

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
                # Remove question mark
                team_b = team_b.rstrip("?").strip()
                # Remove "Will " prefix
                if team_a.lower().startswith("will "):
                    team_a = team_a[5:].strip()
                return self._clean_team_name(team_a), self._clean_team_name(team_b)

        # Try "beat" / "win against" pattern: "Will Team A beat Team B?"
        beat_match = re.search(
            r'[Ww]ill\s+(?:the\s+)?(.+?)\s+(?:beat|defeat|win against)\s+(?:the\s+)?(.+?)[\s?]*$',
            q,
        )
        if beat_match:
            return self._clean_team_name(beat_match.group(1).strip()), self._clean_team_name(beat_match.group(2).rstrip("?").strip())

        # Single-team pattern: "Will Team A win on DATE?" / "Will Team A win?"
        win_match = re.search(
            r'[Ww]ill\s+(?:the\s+)?(.+?)\s+win\b',
            q,
        )
        if win_match:
            team = self._clean_team_name(win_match.group(1).strip())
            if len(team) >= 3:
                return team, None

        return None, None

    @staticmethod
    def _clean_team_name(name: str) -> str:
        """Strip suffixes that hurt ESPN search (FC, SC, CF, AFC etc.)."""
        import re
        # Remove trailing FC/SC/CF/AFC/SFC — ESPN search works better without
        cleaned = re.sub(r'\s+(?:A?FC|SC|CF|SFC|AC)\s*$', '', name, flags=re.IGNORECASE)
        return cleaned.strip() or name

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
        league_name = league  # Use league slug as display name (e.g. "eng.1", "nba")

        # Try question first for full team names, fall back to slug abbreviations
        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)

        # Use slug abbreviations as backup ONLY if question gave nothing
        # and slug parts are long enough (≥4 chars) to avoid ambiguity
        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b

        # Single-team markets ("Will X win?") are valid — only need team_a
        if not team_a_name:
            logger.debug("Could not extract team names from: %s / %s", question[:60], slug)
            return None

        logger.info("Fetching ESPN data: %s vs %s (%s)", team_a_name, team_b_name, league_name)

        team_a = self.get_team_record(sport, league, team_a_name)
        team_b = self.get_team_record(sport, league, team_b_name) if team_b_name else None

        if not team_a and not team_b:
            # Try slug abbreviations if question names failed
            if slug_a and len(slug_a) >= 4 and slug_a != team_a_name:
                team_a = self.get_team_record(sport, league, slug_a)
            if slug_b and len(slug_b) >= 4 and slug_b != team_b_name:
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

    def get_upcoming_match_info(
        self, question: str, slug: str, tags: List[str]
    ) -> Optional[Dict]:
        """Check ESPN scoreboard for match start time and status.

        Returns dict with:
            match_start_iso: str  — actual scheduled start (ISO 8601)
            status: str           — "scheduled" | "in_progress" | "completed" | "postponed"
            completed: bool
        or None if not found.
        """
        sport_league = self.detect_sport(question, slug, tags)
        if not sport_league:
            return None

        sport, league = sport_league

        # Extract team names for matching
        team_a, team_b = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)
        if not team_a and slug_a:
            team_a = slug_a
        if not team_b and slug_b:
            team_b = slug_b
        if not team_a or not team_b:
            return None

        search_terms = [t.lower() for t in [team_a, team_b] if t]

        # Check today's and yesterday's scoreboard (covers timezone edge cases)
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        dates_to_check = [
            now.strftime("%Y%m%d"),
            (now - timedelta(days=1)).strftime("%Y%m%d"),
        ]

        for date_str in dates_to_check:
            url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str}"
            data = self._get(url)
            if not data:
                continue

            for event in data.get("events", []):
                event_name = event.get("name", "").lower()
                short_name = event.get("shortName", "").lower()

                # Match: both team names/abbreviations appear in event
                matched = 0
                for term in search_terms:
                    if term in event_name or term in short_name:
                        matched += 1
                    else:
                        # Check competitor abbreviations and short names
                        for comp in event.get("competitions", [{}])[0].get("competitors", []):
                            team_data = comp.get("team", {})
                            abbr = team_data.get("abbreviation", "").lower()
                            display = team_data.get("displayName", "").lower()
                            short = team_data.get("shortDisplayName", "").lower()
                            if term in abbr or term in display or term in short:
                                matched += 1
                                break

                if matched < 2:
                    continue

                # Found the match — extract info
                competition = event.get("competitions", [{}])[0]
                status_obj = competition.get("status", {})
                status_type = status_obj.get("type", {})

                state = status_type.get("state", "pre")  # pre, in, post
                completed = status_type.get("completed", False)

                if state == "pre":
                    status = "scheduled"
                elif state == "in":
                    status = "in_progress"
                elif state == "post":
                    status = "completed"
                else:
                    status = state

                start_iso = event.get("date", "")  # ISO 8601

                logger.info("ESPN match info: %s — status=%s, start=%s",
                            event.get("shortName", "?"), status, start_iso[:16])

                return {
                    "match_start_iso": start_iso,
                    "status": status,
                    "completed": completed,
                }
