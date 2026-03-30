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

# Slug prefix → (sport, league, label) for fast sport detection.
# ESPN search is fallback; this prevents Hurricanes→college-football bugs.
_SPORT_LEAGUES: dict = {
    "nba": ("basketball", "nba", "NBA"),
    "nhl": ("hockey", "nhl", "NHL"),
    "nfl": ("football", "nfl", "NFL"),
    "mlb": ("baseball", "mlb", "MLB"),
    "cbb": ("basketball", "mens-college-basketball", "CBB"),
    "cwbb": ("basketball", "womens-college-basketball", "WCBB"),
    "cfb": ("football", "college-football", "CFB"),
    "mls": ("soccer", "usa.1", "MLS"),
    "epl": ("soccer", "eng.1", "EPL"),
    "lal": ("soccer", "esp.1", "La Liga"),
    "ser": ("soccer", "ita.1", "Serie A"),
    "bun": ("soccer", "ger.1", "Bundesliga"),
    "lig": ("soccer", "fra.1", "Ligue 1"),
    "atp": ("tennis", "atp", "ATP"),
    "wta": ("tennis", "wta", "WTA"),
    "ufc": ("mma", "ufc", "UFC"),
}

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

    # ESPN search endpoint -- free, no API key needed
    _SEARCH_URL = "https://site.web.api.espn.com/apis/common/v3/search"

    # Leagues to skip -- women's leagues, cricket, rugby return wrong context
    _SKIP_LEAGUES = frozenset({
        "eng.w.fa", "eng.w.1", "eng.w.2",  # English women's
        "usa.w.1",  # NWSL
        "fifa.w.worldcup", "uefa.w.euro",   # Women's international
    })
    _SKIP_SPORTS = frozenset({"cricket"})

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
        # Try hardcoded lookups first (fast path -- empty by default after refactor)
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
            # Slug abbreviations < 4 chars are too ambiguous (e.g. "bri" -> NCAA)
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
        # Soccer leagues don't support seasontype param -- returns 0 events.
        # Try bare URL first (works for soccer); skip seasontype=2 if bare returned data (overlap).
        recent_games = []
        base_schedule = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/schedule"
        bare_data = self._get(base_schedule)
        bare_found = False
        if bare_data:
            for event in bare_data.get("events", []):
                if event.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed", False):
                    game_info = self._parse_game(event, str(team_id))
                    if game_info and game_info not in recent_games:
                        recent_games.append(game_info)
            bare_found = len(recent_games) > 0
        # Only try seasontype variants if bare URL returned nothing (non-soccer sports)
        if not bare_found:
            for st in [2, 3]:
                sched_data = self._get(f"{base_schedule}?seasontype={st}")
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

        # Try "beat" / "win against" / "over" pattern
        beat_match = re.search(
            r'[Ww]ill\s+(?:the\s+)?(.+?)\s+(?:beat|defeat|win against|win over)\s+(?:the\s+)?(.+?)[\s?]*$',
            q,
        )
        if beat_match:
            return self._clean_team_name(beat_match.group(1).strip()), self._clean_team_name(beat_match.group(2).rstrip("?").strip())

        # "Team A to beat/defeat Team B" (no "Will")
        to_beat_match = re.search(
            r'(?:the\s+)?(.+?)\s+to\s+(?:beat|defeat|win against|win over)\s+(?:the\s+)?(.+?)[\s?]*$',
            q,
        )
        if to_beat_match:
            return self._clean_team_name(to_beat_match.group(1).strip()), self._clean_team_name(to_beat_match.group(2).rstrip("?").strip())

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
        # Remove trailing FC/SC/CF/AFC/SFC -- ESPN search works better without
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
        _SLUG_STOP = {
            "total", "over", "under", "spread", "ml", "moneyline", "pt5", "pts",
            "will", "win", "beat", "defeat", "lose", "match", "game", "series",
            "friendly", "qualifier", "qualifying", "cup", "league",
        }
        for p in parts[1:]:
            if len(p) == 4 and p.isdigit():
                break  # hit the date
            if p.lower() in _SLUG_STOP:
                break  # hit O/U or spread suffix
            non_date.append(p)
        if len(non_date) >= 2:
            return non_date[0], non_date[1]
        return None, None

    # Sports where competitors are individual athletes, not teams
    _ATHLETE_SPORTS = frozenset({"tennis", "mma"})

    def get_match_context(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Build structured context string for AI analyst.

        Routes to athlete-based context for tennis/MMA, team-based for others.
        Returns None if not a traditional sport or no data available.
        """
        sport_league = self.detect_sport(question, slug, tags)
        if not sport_league:
            return None

        sport, league = sport_league

        # Athlete-based sports (tennis, MMA) use different ESPN endpoints
        if sport in self._ATHLETE_SPORTS:
            return self._get_athlete_match_context(sport, league, question, slug)

        return self._get_team_match_context(sport, league, question, slug)

    def _get_athlete_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build context for athlete-based sports (tennis, MMA).

        Uses ESPN search to confirm athletes and scoreboard for match data.
        """
        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)
        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b

        if not team_a_name:
            return None

        logger.info("Fetching ESPN athlete data: %s vs %s (%s/%s)",
                     team_a_name, team_b_name, sport, league)

        parts = [f"=== SPORTS DATA (ESPN) -- {sport}/{league} ==="]
        found_any = False

        for label, name in [("PLAYER A", team_a_name), ("PLAYER B", team_b_name)]:
            if not name:
                parts.append(f"\n{label}: No data available")
                continue

            # Search ESPN for this athlete
            params = {"query": name, "limit": 5, "type": "player"}
            record_call("espn_search")
            self._rate_limit()
            try:
                resp = requests.get(self._SEARCH_URL, params=params, timeout=8)
                data = resp.json() if resp.status_code == 200 else {}
            except (requests.RequestException, ValueError):
                data = {}

            # Find matching athlete in our sport
            athlete_info = None
            for item in data.get("items", []):
                if item.get("sport") == sport:
                    athlete_info = item
                    break

            if athlete_info:
                found_any = True
                display = athlete_info.get("displayName", name)
                athlete_league = athlete_info.get("league", league)
                parts.append(f"\n{label}: {display} ({athlete_league})")
            else:
                parts.append(f"\n{label}: {name} (not found on ESPN)")

        if not found_any:
            return None

        sport_label = "tennis" if sport == "tennis" else "MMA"
        parts.append(f"\nThis is a {sport_label} match. Use your knowledge of current "
                     f"rankings, recent form, surface/venue, and head-to-head to estimate.")
        return "\n".join(parts)

    def _get_team_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build context for team-based sports (soccer, NBA, NFL, MLB, NHL, etc.)."""
        league_name = league

        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)

        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b

        if not team_a_name:
            logger.debug("Could not extract team names from: %s / %s", question[:60], slug)
            return None

        logger.info("Fetching ESPN data: %s vs %s (%s)", team_a_name, team_b_name, league_name)

        team_a = self.get_team_record(sport, league, team_a_name)
        team_b = self.get_team_record(sport, league, team_b_name) if team_b_name else None

        if not team_a and not team_b:
            if slug_a and len(slug_a) >= 4 and slug_a != team_a_name:
                team_a = self.get_team_record(sport, league, slug_a)
            if slug_b and len(slug_b) >= 4 and slug_b != team_b_name:
                team_b = self.get_team_record(sport, league, slug_b)

        if not team_a and not team_b:
            return None

        parts = [f"=== SPORTS DATA (ESPN) -- {league_name} ==="]

        for label, stats in [("TEAM A", team_a), ("TEAM B", team_b)]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue

            header = f"\n{label}: {stats['team_name']}"
            if stats["record"]:
                header += f" ({stats['record']})"
            if stats["standing"]:
                header += f" -- {stats['standing']}"
            parts.append(header)

            if stats["recent_games"]:
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

    # ── ESPN Core API odds ─────────────────────────────────────────────────

    _CORE_API = "https://sports.core.api.espn.com/v2/sports"

    def get_espn_odds(
        self, question: str, slug: str, tags: List[str]
    ) -> Optional[Dict]:
        """Fetch betting odds from ESPN Core API (free, no key needed).

        Finds the matching event on ESPN scoreboard, then queries the Core API
        odds endpoint. Returns dict compatible with Odds API format:
            team_a, team_b, bookmaker_prob_a, bookmaker_prob_b,
            num_bookmakers, bookmakers
        """
        sport_league = self.detect_sport(question, slug, tags)
        if not sport_league:
            return None

        sport, league = sport_league

        # Extract team names
        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)
        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b
        if not team_a_name or not team_b_name:
            return None

        # Find matching event on scoreboard
        event_id, comp_id, home_team, away_team, team_a_is_home = (
            self._find_espn_event(sport, league, team_a_name, team_b_name)
        )
        if not event_id:
            return None

        # Fetch odds from Core API
        odds_url = (
            f"{self._CORE_API}/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/odds?limit=100"
        )
        self._rate_limit()
        try:
            resp = requests.get(odds_url, timeout=10)
            record_call("espn_odds")
            if resp.status_code != 200:
                logger.debug("ESPN odds not available for %s/%s event %s", sport, league, event_id)
                return None
            odds_data = resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.debug("ESPN odds fetch error: %s", e)
            return None

        # Parse odds from all providers
        probs_a: list[float] = []
        probs_b: list[float] = []
        provider_names: list[str] = []

        for item in odds_data.get("items", []):
            provider_name = item.get("provider", {}).get("name", "ESPN")
            home_odds = away_odds = None

            # Try DraftKings-style structure (current.moneyLine.decimal)
            home_block = item.get("homeTeamOdds", {})
            away_block = item.get("awayTeamOdds", {})

            current_home = home_block.get("current", {}).get("moneyLine", {})
            current_away = away_block.get("current", {}).get("moneyLine", {})

            if current_home.get("decimal") and current_away.get("decimal"):
                home_odds = float(current_home["decimal"])
                away_odds = float(current_away["decimal"])
            else:
                # Bet365-style: odds.value in awayTeamOdds/homeTeamOdds
                h_odds_block = home_block.get("odds", {})
                a_odds_block = away_block.get("odds", {})
                if h_odds_block.get("value") and a_odds_block.get("value"):
                    home_odds = float(h_odds_block["value"])
                    away_odds = float(a_odds_block["value"])

            if not home_odds or not away_odds or home_odds <= 1.0 or away_odds <= 1.0:
                continue

            # Convert decimal odds to implied probability (remove vig)
            home_prob = 1.0 / home_odds
            away_prob = 1.0 / away_odds
            total = home_prob + away_prob
            home_prob /= total
            away_prob /= total

            if team_a_is_home:
                probs_a.append(home_prob)
                probs_b.append(away_prob)
            else:
                probs_a.append(away_prob)
                probs_b.append(home_prob)
            provider_names.append(provider_name)

        if not probs_a:
            return None

        avg_a = sum(probs_a) / len(probs_a)
        avg_b = sum(probs_b) / len(probs_b)

        logger.info("ESPN odds: %s %.0f%% vs %s %.0f%% (%d providers: %s)",
                     team_a_name, avg_a * 100, team_b_name, avg_b * 100,
                     len(probs_a), ", ".join(provider_names))

        return {
            "team_a": team_a_name,
            "team_b": team_b_name,
            "bookmaker_prob_a": round(avg_a, 3),
            "bookmaker_prob_b": round(avg_b, 3),
            "num_bookmakers": len(probs_a),
            "bookmakers": provider_names[:5],
            "source": "espn",
        }

    def _find_espn_event(
        self, sport: str, league: str, team_a: str, team_b: str
    ) -> tuple:
        """Find a matching event on ESPN scoreboard.

        Returns (event_id, comp_id, home_team, away_team, team_a_is_home)
        or (None, None, None, None, None) if not found.
        """
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        search_lower = [team_a.lower(), team_b.lower()]

        for day_offset in range(2):  # Today + tomorrow
            date_str = (now + timedelta(days=day_offset)).strftime("%Y%m%d")
            url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str}"
            data = self._get(url)
            if not data:
                continue

            for event in data.get("events", []):
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                if len(competitors) != 2:
                    continue

                # Match team_a to one competitor, team_b to the other
                names_0 = self._competitor_names(competitors[0])
                names_1 = self._competitor_names(competitors[1])
                ta = team_a.lower()
                tb = team_b.lower()

                # Try both orderings: (a->0, b->1) and (a->1, b->0)
                matched = False
                if (any(ta in n for n in names_0) and any(tb in n for n in names_1)):
                    matched = True
                elif (any(ta in n for n in names_1) and any(tb in n for n in names_0)):
                    matched = True

                if not matched:
                    continue

                # Determine actual home/away from ESPN homeAway field
                actual_home = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
                actual_away = competitors[0] if competitors[0].get("homeAway") == "away" else competitors[1]
                actual_home_name = actual_home.get("team", {}).get("displayName", "")
                actual_away_name = actual_away.get("team", {}).get("displayName", "")

                # Is team_a the home team?
                a_is_home = any(ta in n for n in self._competitor_names(actual_home))

                event_id = event.get("id", "")
                comp_id = comp.get("id", event_id)

                return event_id, comp_id, actual_home_name, actual_away_name, a_is_home

        return None, None, None, None, None

    @staticmethod
    def _competitor_names(competitor: dict) -> list[str]:
        """Extract all searchable name variants from an ESPN competitor."""
        team = competitor.get("team", {})
        names = [
            team.get("displayName", "").lower(),
            team.get("shortDisplayName", "").lower(),
            team.get("abbreviation", "").lower(),
            team.get("nickname", "").lower(),
            team.get("location", "").lower(),
        ]
        # Also check athlete (for tennis/MMA)
        athlete = competitor.get("athlete", {})
        if athlete:
            names.append(athlete.get("displayName", "").lower())
        return [n for n in names if n]
