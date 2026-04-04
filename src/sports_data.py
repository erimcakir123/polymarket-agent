"""ESPN API client for traditional sports data (NBA, NCAA, NFL, MLB, NHL, soccer)."""
from __future__ import annotations
import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call
from src.matching.pair_matcher import match_team

logger = logging.getLogger(__name__)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

# Slug prefix → (sport, league, label) for fast sport detection.
# Sources: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/
_SPORT_LEAGUES: dict = {
    # ── Basketball (basketball.md) ─────────────────────────────────────────
    "nba": ("basketball", "nba", "NBA"),
    "wnba": ("basketball", "wnba", "WNBA"),
    "cbb": ("basketball", "mens-college-basketball", "CBB"),
    "cwbb": ("basketball", "womens-college-basketball", "WCBB"),
    "gleague": ("basketball", "nba-development", "G-League"),
    "fiba": ("basketball", "fiba", "FIBA"),
    "nbl": ("basketball", "nbl", "NBL Australia"),
    # ── Hockey (hockey.md) ─────────────────────────────────────────────────
    "nhl": ("hockey", "nhl", "NHL"),
    "nchm": ("hockey", "mens-college-hockey", "NCAA Hockey"),
    "nchw": ("hockey", "womens-college-hockey", "NCAA W Hockey"),
    # ── American Football (football.md) ────────────────────────────────────
    "nfl": ("football", "nfl", "NFL"),
    "cfb": ("football", "college-football", "CFB"),
    "cfl": ("football", "cfl", "CFL"),
    "ufl": ("football", "ufl", "UFL"),
    "xfl": ("football", "xfl", "XFL"),
    # ── Baseball (baseball.md) ─────────────────────────────────────────────
    "mlb": ("baseball", "mlb", "MLB"),
    "cbase": ("baseball", "college-baseball", "College Baseball"),
    "wbc": ("baseball", "world-baseball-classic", "WBC"),
    # ── Soccer — England ───────────────────────────────────────────────────
    "epl": ("soccer", "eng.1", "EPL"),
    "eng2": ("soccer", "eng.2", "Championship"),
    "facup": ("soccer", "eng.fa", "FA Cup"),
    # ── Soccer — Spain ─────────────────────────────────────────────────────
    "lal": ("soccer", "esp.1", "La Liga"),
    "esp2": ("soccer", "esp.2", "La Liga 2"),
    "copdr": ("soccer", "esp.copa_del_rey", "Copa del Rey"),
    # ── Soccer — Germany ───────────────────────────────────────────────────
    "bun": ("soccer", "ger.1", "Bundesliga"),
    "ger2": ("soccer", "ger.2", "2. Bundesliga"),
    "dfbp": ("soccer", "ger.dfb_pokal", "DFB Pokal"),
    # ── Soccer — Italy ─────────────────────────────────────────────────────
    "ser": ("soccer", "ita.1", "Serie A"),
    "sea": ("soccer", "ita.1", "Serie A"),      # Polymarket slug prefix
    "ita2": ("soccer", "ita.2", "Serie B"),
    "copit": ("soccer", "ita.coppa_italia", "Coppa Italia"),
    # ── Soccer — France ────────────────────────────────────────────────────
    "lig": ("soccer", "fra.1", "Ligue 1"),
    "fl1": ("soccer", "fra.1", "Ligue 1"),      # Polymarket slug prefix
    "fra2": ("soccer", "fra.2", "Ligue 2"),
    "coudf": ("soccer", "fra.coupe_de_france", "Coupe de France"),
    # ── Soccer — Other European ────────────────────────────────────────────
    "tur": ("soccer", "tur.1", "Super Lig"),
    "ned": ("soccer", "ned.1", "Eredivisie"),
    "ere": ("soccer", "ned.1", "Eredivisie"),    # Polymarket slug prefix
    "ned2": ("soccer", "ned.2", "Eerste Divisie"),
    "por": ("soccer", "por.1", "Primeira Liga"),
    "bel": ("soccer", "bel.1", "Pro League"),
    "aut": ("soccer", "aut.1", "Bundesliga AT"),
    "gre": ("soccer", "gre.1", "Super League"),
    "den": ("soccer", "den.1", "Superliga"),
    "nor": ("soccer", "nor.1", "Eliteserien"),
    "swe": ("soccer", "swe.1", "Allsvenskan"),
    "rus": ("soccer", "rus.1", "Russian Premier"),
    "cze1": ("soccer", "cze.1", "Czech First League"),
    "rou1": ("soccer", "rou.1", "Liga I Romania"),
    "ukr1": ("soccer", "ukr.1", "Ukrainian Premier"),
    "hr1": ("soccer", "cro.1", "Croatian First"),
    "svk1": ("soccer", "svk.1", "Slovak Super Liga"),
    "sco": ("soccer", "sco.1", "Scottish Premiership"),
    # ── Soccer — Americas ──────────────────────────────────────────────────
    "mls": ("soccer", "usa.1", "MLS"),
    "nwsl": ("soccer", "usa.nwsl", "NWSL"),
    "arg": ("soccer", "arg.1", "Liga Profesional"),
    "bra": ("soccer", "bra.1", "Brasileirao"),
    "bra2": ("soccer", "bra.2", "Brasileirao B"),
    "mex": ("soccer", "mex.1", "Liga MX"),
    "col": ("soccer", "col.1", "Liga BetPlay"),
    "col1": ("soccer", "col.1", "Liga BetPlay"),
    "chi": ("soccer", "chi.1", "Primera Chile"),
    "chi1": ("soccer", "chi.1", "Primera Chile"),
    "per1": ("soccer", "per.1", "Liga 1 Peru"),
    "bol1": ("soccer", "bol.1", "Division Profesional"),
    # ── Soccer — Asia/Oceania/Africa ───────────────────────────────────────
    "spl": ("soccer", "sau.1", "Saudi Pro League"),  # Polymarket slug prefix
    "kor": ("soccer", "kor.1", "K League 1"),
    "jpn": ("soccer", "jpn.1", "J1 League"),
    "chn": ("soccer", "chn.1", "CSL"),
    "ind": ("soccer", "ind.1", "ISL"),
    "aus": ("soccer", "aus.1", "A-League"),
    "rsa": ("soccer", "rsa.1", "PSL"),
    "egy1": ("soccer", "egy.1", "Egyptian Premier"),
    "mar1": ("soccer", "mar.1", "Botola Pro"),
    # ── Soccer — Cups & International ──────────────────────────────────────
    "ucl": ("soccer", "uefa.champions", "Champions League"),
    "uel": ("soccer", "uefa.europa", "Europa League"),
    "uecl": ("soccer", "uefa.europa.conf", "Conference League"),
    "efa": ("soccer", "eng.fa", "FA Cup"),           # Polymarket alias
    "efl": ("soccer", "eng.2", "Championship"),      # Polymarket alias
    "dfb": ("soccer", "ger.dfb_pokal", "DFB Pokal"), # Polymarket alias
    "cde": ("soccer", "esp.copa_del_rey", "Copa del Rey"),
    "cdr": ("soccer", "esp.copa_del_rey", "Copa del Rey"),
    "lib": ("soccer", "conmebol.libertadores", "Libertadores"),
    "sud": ("soccer", "conmebol.sudamericana", "Sudamericana"),
    "wcup": ("soccer", "fifa.world", "World Cup"),
    "euro": ("soccer", "uefa.euro", "Euro"),
    "copa": ("soccer", "conmebol.libertadores", "Libertadores"),
    "suda": ("soccer", "conmebol.sudamericana", "Sudamericana"),
    "cona": ("soccer", "conmebol.america", "Copa America"),
    "gold": ("soccer", "concacaf.gold", "Gold Cup"),
    "frien": ("soccer", "fifa.friendly", "Friendlies"),
    # ── Tennis (tennis.md) ─────────────────────────────────────────────────
    "atp": ("tennis", "atp", "ATP"),
    "wta": ("tennis", "wta", "WTA"),
    # ── MMA (mma.md) ──────────────────────────────────────────────────────
    "ufc": ("mma", "ufc", "UFC"),
    "bellator": ("mma", "bellator", "Bellator"),
    "pfl": ("mma", "pfl", "PFL"),
    # ── Golf (golf.md) ────────────────────────────────────────────────────
    "pga": ("golf", "pga", "PGA Tour"),
    "lpga": ("golf", "lpga", "LPGA"),
    "liv": ("golf", "liv", "LIV Golf"),
    "dpw": ("golf", "eur", "DP World Tour"),
    "champ": ("golf", "champions-tour", "Champions Tour"),
    # ── Racing (racing.md) ────────────────────────────────────────────────
    "f1": ("racing", "f1", "Formula 1"),
    "irl": ("racing", "irl", "IndyCar"),
    "nascar": ("racing", "nascar-premier", "NASCAR Cup"),
    # ── Rugby (rugby.md) ─────────────────────────────────────────────────
    "rugby": ("rugby", "rugby", "Rugby"),
    # ── Australian Football (australian_football.md) ──────────────────────
    "afl": ("australian-football", "afl", "AFL"),
    # ── Lacrosse (lacrosse.md) ────────────────────────────────────────────
    "nll": ("lacrosse", "nll", "NLL"),
    "pll": ("lacrosse", "pll", "PLL"),
    # ── Volleyball (volleyball.md) ────────────────────────────────────────
    "mcvb": ("volleyball", "mens-college-volleyball", "NCAA M Volleyball"),
    "wcvb": ("volleyball", "womens-college-volleyball", "NCAA W Volleyball"),
    # ── Field Hockey (field_hockey.md) ────────────────────────────────────
    "cfhoc": ("field-hockey", "womens-college-field-hockey", "NCAA Field Hockey"),
    # ── Cricket — ESPN fallback (dedicated cricket_data.py is primary) ────
    "cric": ("cricket", "cricket", "Cricket"),
}

# Map common Gamma seriesSlug values to (sport, league).
# These are the actual tag values seen in Polymarket Gamma API responses.
_SERIES_TO_ESPN: dict = {
    # Soccer
    "super-lig": ("soccer", "tur.1"),
    "la-liga-2": ("soccer", "esp.2"),
    "la-liga": ("soccer", "esp.1"),
    "primeira-divisin-argentina": ("soccer", "arg.1"),
    "brazil-serie-b": ("soccer", "bra.2"),
    "womens-champions-league": ("soccer", "uefa.champions"),
    "fifa-friendly": ("soccer", "fifa.friendly"),
    "champions-league": ("soccer", "uefa.champions"),
    "europa-league": ("soccer", "uefa.europa"),
    "conference-league": ("soccer", "uefa.europa.conf"),
    "premier-league": ("soccer", "eng.1"),
    "bundesliga": ("soccer", "ger.1"),
    "serie-a": ("soccer", "ita.1"),
    "ligue-1": ("soccer", "fra.1"),
    "eredivisie": ("soccer", "ned.1"),
    "primeira-liga": ("soccer", "por.1"),
    "liga-mx": ("soccer", "mex.1"),
    "j1-league": ("soccer", "jpn.1"),
    "a-league": ("soccer", "aus.1"),
    "saudi-professional-league": ("soccer", "sau.1"),
    "ere": ("soccer", "ned.1"),
    "k-league": ("soccer", "kor.1"),
    "mls": ("soccer", "usa.1"),
    "scottish-premiership": ("soccer", "sco.1"),
    "belgian-pro-league": ("soccer", "bel.1"),
    "russian-premier-league": ("soccer", "rus.1"),
    "danish-superliga": ("soccer", "den.1"),
    "eliteserien": ("soccer", "nor.1"),
    "allsvenskan": ("soccer", "swe.1"),
    "greek-super-league": ("soccer", "gre.1"),
    "austrian-bundesliga": ("soccer", "aut.1"),
    "liga-betplay": ("soccer", "col.1"),
    "brasileirao": ("soccer", "bra.1"),
    "copa-libertadores": ("soccer", "conmebol.libertadores"),
    "copa-sudamericana": ("soccer", "conmebol.sudamericana"),
    "fa-cup": ("soccer", "eng.fa"),
    "efl-cup": ("soccer", "eng.league_cup"),
    "dfb-pokal": ("soccer", "ger.dfb_pokal"),
    "copa-del-rey": ("soccer", "esp.copa_del_rey"),
    "coppa-italia": ("soccer", "ita.coppa_italia"),
    "coupe-de-france": ("soccer", "fra.coupe_de_france"),
    # Hockey — SHL/KHL not on ESPN, let dynamic search handle them
    # Basketball — CBA/KBL not on ESPN, let dynamic search handle them
    # Cricket
    "indian-premier-league": ("cricket", "cricket"),
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

    _SKIP_LEAGUES = frozenset()  # All leagues supported
    _SKIP_SPORTS = frozenset()  # No longer skip any sport

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

        # Check tags against known Gamma seriesSlug mappings
        # Strip year suffixes (e.g. "serie-a-2025" -> "serie-a")
        for tag in tags:
            tag_lower = tag.lower().strip()
            tag_stripped = re.sub(r"-\d{4}$", "", tag_lower)
            for variant in (tag_lower, tag_stripped):
                if variant in _SERIES_TO_ESPN:
                    sport, league = _SERIES_TO_ESPN[variant]
                    logger.info("Series slug match: tag='%s' -> %s/%s", tag, sport, league)
                    return (sport, league)
            # Also check if tag matches any _SPORT_LEAGUES label (case-insensitive)
            for key, (s, l, label) in _SPORT_LEAGUES.items():
                if tag_lower == label.lower() or tag_lower == l.lower():
                    return (s, l)

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

    # Sports where injury endpoint returns 500
    _NO_INJURY_SPORTS = frozenset({"tennis", "mma", "golf", "racing", "cricket"})

    def get_team_injuries(self, sport: str, league: str, team_id: str) -> List[Dict]:
        """Fetch injury report for a team from ESPN Site API.

        Returns list of: {player, status, detail, position}
        Skips call for sports where endpoint returns 500.
        """
        if sport in self._NO_INJURY_SPORTS:
            return []

        url = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/injuries"
        data = self._get(url)
        if not data:
            return []

        injuries = []
        for item in data.get("injuries", []):
            athlete = item.get("athlete", {})
            injuries.append({
                "player": athlete.get("displayName", "Unknown"),
                "status": item.get("status", "Unknown"),
                "detail": item.get("detail", ""),
                "position": athlete.get("position", {}).get("abbreviation", ""),
            })
        return injuries

    _STANDINGS_CACHE_TTL = 21600  # 6 hours

    def get_standings_context(self, sport: str, league: str, team_id: str) -> Optional[Dict]:
        """Fetch team's standings data from ESPN.

        Returns: {wins, losses, win_pct, home_record, away_record,
                  streak, last_10, games_behind, conference_rank}
        Uses /apis/v2/ path (not /apis/site/v2/ which returns a stub).
        Cached for 6 hours.
        """
        url = f"https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings"

        # Check 6-hour cache manually (override default 30min)
        cached = self._cache.get(url)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._STANDINGS_CACHE_TTL:
                return self._extract_team_standing(data, team_id)

        data = self._get(url)
        if not data:
            return None

        return self._extract_team_standing(data, team_id)

    def _extract_team_standing(self, data: dict, team_id: str) -> Optional[Dict]:
        """Extract a single team's standing from the full standings response."""
        for group in data.get("children", []):
            for entry in group.get("standings", {}).get("entries", []):
                if str(entry.get("team", {}).get("id", "")) != str(team_id):
                    continue

                stats = {}
                for s in entry.get("stats", []):
                    abbrev = s.get("abbreviation", "")
                    stats[abbrev] = s.get("displayValue", s.get("value", ""))

                return {
                    "wins": int(float(stats.get("W", 0))),
                    "losses": int(float(stats.get("L", 0))),
                    "win_pct": stats.get("PCT", ""),
                    "home_record": stats.get("HOME", ""),
                    "away_record": stats.get("AWAY", ""),
                    "streak": stats.get("STRK", ""),
                    "last_10": stats.get("L10", ""),
                    "games_behind": stats.get("GB", ""),
                    "conference_rank": entry.get("team", {}).get("id", ""),
                }
        return None

    def get_espn_predictor(self, sport: str, league: str, event_id: str, comp_id: str) -> Optional[Dict]:
        """Fetch ESPN BPI/predictor win probability (ESPN's own model, NOT bookmaker odds).

        Tries Core API probabilities endpoint first (lighter response).
        Falls back to summary endpoint and extracts predictor block.
        Returns: {home_win_pct, away_win_pct, tie_pct, source: "espn_bpi"}
        """
        # Option A: probabilities endpoint (preferred)
        prob_url = (
            f"{self._CORE_API}/{sport}/leagues/{league}/events/{event_id}"
            f"/competitions/{comp_id}/probabilities?limit=1"
        )
        data = self._get(prob_url)
        if data:
            items = data.get("items", [])
            if items:
                item = items[0]
                home_pct = item.get("homeWinPercentage")
                away_pct = item.get("awayWinPercentage")
                if home_pct is not None and away_pct is not None:
                    return {
                        "home_win_pct": float(home_pct),
                        "away_win_pct": float(away_pct),
                        "tie_pct": float(item.get("tiePercentage", 0.0)),
                        "source": "espn_bpi",
                    }

        # Option B: summary endpoint fallback
        summary_url = f"{ESPN_BASE}/{sport}/{league}/summary?event={event_id}"
        summary = self._get(summary_url)
        if summary:
            predictor = summary.get("predictor", {})
            home_team = predictor.get("homeTeam", {})
            projection = home_team.get("gameProjection")
            if projection is not None:
                try:
                    home_pct = float(projection) / 100.0
                    return {
                        "home_win_pct": home_pct,
                        "away_win_pct": 1.0 - home_pct,
                        "tie_pct": 0.0,
                        "source": "espn_bpi",
                    }
                except (ValueError, TypeError):
                    pass

        return None

    # Sports with daily schedules where B2B matters
    _DAILY_SPORTS = frozenset({"basketball", "hockey", "baseball"})

    def detect_back_to_back(self, recent_games: List[Dict]) -> bool:
        """Check if team played yesterday (back-to-back).

        Scans recent_games dates. If most recent game was yesterday, return True.
        No API call needed — uses cached schedule data.
        """
        if not recent_games:
            return False

        last_game = recent_games[-1]
        last_date_str = last_game.get("date", "")
        if not last_date_str:
            return False

        try:
            from datetime import timedelta
            last_date = datetime.strptime(last_date_str[:10], "%Y-%m-%d").date()
            yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
            return last_date == yesterday
        except (ValueError, TypeError):
            return False

    def get_head_to_head(
        self, sport: str, league: str, team_a_name: str, team_b_name: str
    ) -> List[Dict]:
        """Find H2H matchups this season from team A's schedule.

        Scans team_a's cached schedule for completed games vs team_b.
        No extra API call needed — reuses get_team_record() cached data.
        """
        team_a_data = self.get_team_record(sport, league, team_a_name)
        if not team_a_data:
            return []

        team_b_lower = team_b_name.lower()
        h2h = []
        for game in team_a_data.get("recent_games", []):
            opp = game.get("opponent", "").lower()
            if team_b_lower in opp or opp in team_b_lower:
                h2h.append(game)
        return h2h

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
    _ATHLETE_SPORTS = frozenset({"tennis", "mma", "golf"})

    # Sports where competitors are event-based (tournaments, races)
    _EVENT_SPORTS = frozenset({"racing"})

    def get_match_context(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Build structured context string for AI analyst.

        Routes to athlete-based context for tennis/MMA/golf, event-based for racing,
        team-based for all others.
        Returns None if not a traditional sport or no data available.
        """
        sport_league = self.detect_sport(question, slug, tags)
        if not sport_league:
            return None

        sport, league = sport_league

        if sport in self._ATHLETE_SPORTS:
            return self._get_athlete_match_context(sport, league, question, slug)

        if sport in self._EVENT_SPORTS:
            return self._get_event_match_context(sport, league, question, slug)

        return self._get_team_match_context(sport, league, question, slug)

    def _get_athlete_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build context for athlete-based sports (tennis, MMA).

        Scans recent ESPN scoreboards to build match/fight history with [W]/[L] markers.
        """
        team_a_name, team_b_name = self._extract_teams_from_question(question)
        slug_a, slug_b = self._extract_teams_from_slug(slug)
        if not team_a_name and slug_a and len(slug_a) >= 4:
            team_a_name = slug_a
        if not team_b_name and slug_b and len(slug_b) >= 4:
            team_b_name = slug_b

        if not team_a_name:
            return None

        # Sport-specific scan window
        days_back = 90 if sport == "mma" else 14

        logger.info("Fetching ESPN %s athlete data: %s vs %s (%s, %dd scan)",
                     sport, team_a_name, team_b_name, league, days_back)

        parts = [f"=== SPORTS DATA (ESPN) -- {sport}/{league} ==="]
        found_any = False

        for label, name in [("PLAYER A", team_a_name), ("PLAYER B", team_b_name)]:
            if not name:
                parts.append(f"\n{label}: No data available")
                continue

            matches = self._scan_scoreboard_for_athlete(sport, league, name, days_back)

            if matches:
                found_any = True
                wins = sum(1 for m in matches if m["won"])
                losses = len(matches) - wins
                parts.append(f"\n{label}: {name}")
                parts.append(f"  Recent form ({len(matches)} matches): {wins}W-{losses}L")
                parts.append("  Recent matches:")
                for m in matches[:5]:
                    result = "W" if m["won"] else "L"
                    score_str = f" {m['score']}" if m.get("score") else ""
                    parts.append(
                        f"    [{result}] vs {m['opponent']}{score_str} "
                        f"({m.get('event', '')}, {m.get('date', '')})"
                    )
            else:
                # Fallback: ESPN search to at least confirm athlete exists
                params = {"query": name, "limit": 5, "type": "player"}
                record_call("espn_search")
                self._rate_limit()
                try:
                    resp = requests.get(self._SEARCH_URL, params=params, timeout=8)
                    data = resp.json() if resp.status_code == 200 else {}
                except (requests.RequestException, ValueError):
                    data = {}
                athlete_info = None
                for item in data.get("items", []):
                    if item.get("sport") == sport:
                        athlete_info = item
                        break
                if athlete_info:
                    found_any = True
                    display = athlete_info.get("displayName", name)
                    parts.append(f"\n{label}: {display} ({league})")
                    parts.append("  No recent match data found on ESPN scoreboard")
                else:
                    parts.append(f"\n{label}: {name} (not found on ESPN)")

        if not found_any:
            return None

        sport_label = {"tennis": "tennis", "mma": "MMA"}.get(sport, sport)
        parts.append(f"\nThis is a {sport_label} match. Use recent form, rankings, "
                     f"surface/venue, and head-to-head to estimate.")
        return "\n".join(parts)

    def _scan_scoreboard_for_athlete(
        self, sport: str, league: str, player_name: str, days_back: int
    ) -> List[Dict]:
        """Scan recent ESPN scoreboards to find an athlete's completed matches.

        Returns list of dicts: {opponent, won, score, event, date}
        """
        from datetime import timedelta as td
        matches = []
        today = datetime.now(timezone.utc).date()

        for i in range(days_back):
            date = today - td(days=i)
            date_str = date.strftime("%Y%m%d")
            url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str}"
            data = self._get(url)
            if not data:
                continue

            for event in data.get("events", []):
                # Tennis/MMA use groupings[].competitions[] instead of
                # top-level competitions[].  Collect from both paths.
                all_comps: list = list(event.get("competitions", []))
                for grp in event.get("groupings", []):
                    all_comps.extend(grp.get("competitions", []))

                for comp in all_comps:
                    status = comp.get("status", {}).get("type", {})
                    if not status.get("completed", False):
                        continue
                    competitors = comp.get("competitors", [])
                    if len(competitors) != 2:
                        continue

                    player_comp = None
                    opp_comp = None
                    for c in competitors:
                        athlete = c.get("athlete", {})
                        c_name = athlete.get("displayName", "")
                        is_match_result, score, _ = match_team(c_name.lower(), player_name.lower())
                        if is_match_result and score >= 0.70:
                            player_comp = c
                        else:
                            opp_comp = c

                    if player_comp and opp_comp:
                        won = player_comp.get("winner", False)
                        opp_name = opp_comp.get("athlete", {}).get("displayName", "Unknown")
                        score_str = self._extract_athlete_score(player_comp, opp_comp, sport)
                        matches.append({
                            "opponent": opp_name,
                            "won": won,
                            "score": score_str,
                            "event": event.get("name", ""),
                            "date": date.isoformat(),
                        })

            # Stop early if we have enough data
            if len(matches) >= 10:
                break

        return matches

    def _extract_athlete_score(self, player_comp: dict, opp_comp: dict, sport: str) -> str:
        """Extract score string from competitor linescores."""
        p_scores = player_comp.get("linescores", [])
        o_scores = opp_comp.get("linescores", [])
        if not p_scores:
            return ""
        if sport == "tennis":
            # Set scores like "6-3 4-6 7-5"
            sets = []
            for p, o in zip(p_scores, o_scores):
                sets.append(f"{int(p.get('value', 0))}-{int(o.get('value', 0))}")
            return " ".join(sets)
        elif sport == "mma":
            return f"R{len(p_scores)}"
        return ""

    def _get_event_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build context for event-based sports (racing).

        Scans recent scoreboards for tournament/race results.
        """
        from datetime import timedelta as td

        logger.info("Fetching ESPN %s event data: %s/%s", sport, league, question[:40])

        today = datetime.now(timezone.utc).date()
        results = []

        for i in range(30):
            date = today - td(days=i)
            date_str = date.strftime("%Y%m%d")
            url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str}"
            data = self._get(url)
            if not data:
                continue
            for event in data.get("events", []):
                for comp in event.get("competitions", []):
                    status = comp.get("status", {}).get("type", {})
                    if not status.get("completed", False):
                        continue
                    competitors = comp.get("competitors", [])
                    if not competitors:
                        continue
                    top = []
                    sorted_comps = sorted(competitors,
                                          key=lambda c: c.get("order", 999))
                    for c in sorted_comps[:3]:
                        athlete = c.get("athlete", {})
                        name = athlete.get("displayName", "Unknown")
                        top.append(name)
                    if top:
                        results.append({
                            "event": event.get("name", ""),
                            "date": date.isoformat(),
                            "top3": top,
                            "winner": top[0] if top else "Unknown",
                        })
            if len(results) >= 5:
                break

        if not results:
            return None

        parts = [f"=== SPORTS DATA (ESPN) -- {sport}/{league} ==="]
        parts.append(f"\nRecent {sport} results:")
        for r in results[:5]:
            parts.append(f"  [{r['date']}] {r['event']}")
            parts.append(f"    [W] {r['winner']}")
            if len(r["top3"]) > 1:
                parts.append(f"    Top 3: {', '.join(r['top3'])}")
        parts.append(f"\nUse recent {sport} form, rankings, and venue to estimate.")
        return "\n".join(parts)

    def _get_team_id(self, sport: str, league: str, team_name: str) -> Optional[str]:
        """Get ESPN team ID from team name. Uses cached team search."""
        team = self._search_team(sport, league, team_name)
        return str(team.get("id", "")) if team else None

    def _get_venue_from_event(self, sport: str, league: str, event_id: str) -> Optional[str]:
        """Extract venue name from event summary."""
        url = f"{ESPN_BASE}/{sport}/{league}/summary?event={event_id}"
        data = self._get(url)
        if not data:
            return None
        venue = data.get("gameInfo", {}).get("venue", {})
        if not venue:
            return None
        name = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        return f"{name}, {city}" if city else name

    def _get_team_match_context(
        self, sport: str, league: str, question: str, slug: str
    ) -> Optional[str]:
        """Build enriched context for team-based sports."""
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

        # Try to find event for BPI predictor + venue
        event_id, comp_id, home_team, away_team, team_a_is_home = (
            self._find_espn_event(sport, league, team_a_name or "", team_b_name or "")
        )

        # BPI Predictor (requires event_id)
        predictor = None
        if event_id and comp_id:
            predictor = self.get_espn_predictor(sport, league, event_id, comp_id)

        parts = [f"=== SPORTS DATA (ESPN) -- {league_name} ==="]

        # BPI Predictor section (top -- most important ESPN-exclusive signal)
        if predictor:
            home_pct = predictor["home_win_pct"] * 100
            away_pct = predictor["away_win_pct"] * 100
            home_label = home_team or "Home"
            away_label = away_team or "Away"
            parts.append(
                f"\n=== ESPN BPI PREDICTOR ===\n"
                f"(ESPN's own win probability model -- independent from bookmaker odds)\n"
                f"  {home_label}: {home_pct:.1f}%\n"
                f"  {away_label}: {away_pct:.1f}%"
            )

        # Venue
        if event_id:
            venue = self._get_venue_from_event(sport, league, event_id)
            if venue:
                parts.append(f"\nVENUE: {venue}")

        for label, stats, name in [
            ("TEAM A", team_a, team_a_name),
            ("TEAM B", team_b, team_b_name),
        ]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue

            team_id = self._get_team_id(sport, league, stats["team_name"])

            header = f"\n{label}: {stats['team_name']}"
            if stats["record"]:
                header += f" ({stats['record']})"
            if stats["standing"]:
                header += f" -- {stats['standing']}"
            parts.append(header)

            # Standings enrichment (home/away, streak, L10)
            if team_id:
                standing = self.get_standings_context(sport, league, team_id)
                if standing:
                    if standing.get("home_record"):
                        parts.append(f"  Home: {standing['home_record']} | Away: {standing.get('away_record', 'N/A')}")
                    if standing.get("last_10"):
                        parts.append(f"  Last 10: {standing['last_10']} | Streak: {standing.get('streak', 'N/A')}")

            # Recent games
            if stats["recent_games"]:
                recent_5 = stats["recent_games"][-5:]
                wins = sum(1 for g in recent_5 if g["won"])
                parts.append(f"  Last 5: {wins}W-{5 - wins}L")
                parts.append("  Recent games:")
                for g in stats["recent_games"][-5:]:
                    result = "W" if g["won"] else "L"
                    parts.append(
                        f"    [{result}] {g['home_away']} vs {g['opponent']} "
                        f"{g['score']} ({g['date']})"
                    )

            # Back-to-back detection
            if sport in self._DAILY_SPORTS and self.detect_back_to_back(stats.get("recent_games", [])):
                parts.append("  ⚠️ SCHEDULE: BACK-TO-BACK")

            # Injuries
            if team_id:
                injuries = self.get_team_injuries(sport, league, team_id)
                if injuries:
                    parts.append("  Injuries:")
                    for inj in injuries[:8]:
                        parts.append(
                            f"    {inj['player']} ({inj['position']}) -- "
                            f"{inj['status']}: {inj['detail']}"
                        )

        # Head-to-head
        if team_a_name and team_b_name:
            h2h = self.get_head_to_head(sport, league, team_a_name, team_b_name)
            if h2h:
                a_wins = sum(1 for g in h2h if g["won"])
                b_wins = len(h2h) - a_wins
                parts.append(f"\nHEAD-TO-HEAD (this season): {team_a_name} {a_wins}-{b_wins} {team_b_name}")
                for g in h2h[-3:]:
                    result = "W" if g["won"] else "L"
                    parts.append(f"  [{result}] {g['home_away']} {g['score']} ({g['date']})")

        parts.append("\nUse team records, recent form, standings, injuries, and BPI predictor "
                     "to inform your estimate. Weight recent form and home/away performance.")
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
        if not team_a_name:
            return None

        # Find matching event on scoreboard (team_b can be None for single-team questions)
        event_id, comp_id, home_team, away_team, team_a_is_home = (
            self._find_espn_event(sport, league, team_a_name, team_b_name or "")
        )
        if not event_id:
            return None

        # Fill in missing team name from scoreboard discovery
        if not team_b_name:
            if team_a_is_home:
                team_b_name = away_team
            else:
                team_b_name = home_team
            logger.debug("Discovered opponent from scoreboard: %s", team_b_name)

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
                if tb:
                    # Both teams known — require both to match
                    if (any(ta in n for n in names_0) and any(tb in n for n in names_1)):
                        matched = True
                    elif (any(ta in n for n in names_1) and any(tb in n for n in names_0)):
                        matched = True
                else:
                    # Single-team lookup — find team_a in either competitor
                    if any(ta in n for n in names_0) or any(ta in n for n in names_1):
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
