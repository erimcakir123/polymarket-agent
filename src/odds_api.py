"""The Odds API client — bookmaker odds + historical line movement.

Paid plan: 20K credits/month. Used for:
1. Live odds as second opinion on uncertain markets
2. Historical odds for line movement detection (sharp money signals)
3. Score data for live match tracking

Budget strategy (20K credits/month ≈ 650/day):
- Live odds: ~1 credit per request (h2h market, 1 region)
- Historical odds: ~10 credits per request (timestamp lookup)
- Batch by sport: fetch all events for a sport in 1 call, not per-market
- Cache aggressively: 1h for live, 6h for historical
- Only use historical when edge is close to threshold (save credits)
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
    # Basketball
    "cbb": "basketball_ncaab", "ncaab": "basketball_ncaab", "wncaab": "basketball_wncaab",
    "nba": "basketball_nba", "euroleague": "basketball_euroleague",
    # American Football
    "nfl": "americanfootball_nfl", "cfb": "americanfootball_ncaaf", "ncaaf": "americanfootball_ncaaf",
    "ufl": "americanfootball_ufl",
    # Baseball
    "mlb": "baseball_mlb",
    # Ice Hockey
    "nhl": "icehockey_nhl", "ahl": "icehockey_ahl", "shl": "icehockey_sweden_hockey_league",
    # MMA / Boxing
    "ufc": "mma_mixed_martial_arts", "mma": "mma_mixed_martial_arts",
    "boxing": "boxing_boxing",
    # Soccer
    "epl": "soccer_epl", "laliga": "soccer_spain_la_liga", "seriea": "soccer_italy_serie_a",
    "bundesliga": "soccer_germany_bundesliga", "ligue1": "soccer_france_ligue_one",
    "ucl": "soccer_uefa_champs_league", "europa": "soccer_uefa_europa_league",
    "conference": "soccer_uefa_europa_conference_league",
    "mls": "soccer_usa_mls", "eredivisie": "soccer_netherlands_eredivisie",
    "liga-mx": "soccer_mexico_ligamx", "fa-cup": "soccer_fa_cup",
    # Tennis — resolved dynamically via _get_active_tennis_keys()
    # "atp" and "wta" prefixes handled in _detect_sport_key, not here
    # Cricket
    "ipl": "cricket_ipl", "t20": "cricket_international_t20", "psl": "cricket_psl",
    # Rugby
    "nrl": "rugbyleague_nrl",
    # Politics
    "president": "politics_us_presidential_election_winner",
}

# Keywords in question text -> sport key
_QUESTION_SPORT_KEYS = {
    # Basketball
    "ncaa": "basketball_ncaab", "march madness": "basketball_ncaab",
    "nba": "basketball_nba", "euroleague": "basketball_euroleague",
    # American Football
    "nfl": "americanfootball_nfl", "super bowl": "americanfootball_nfl_super_bowl_winner",
    # Baseball
    "mlb": "baseball_mlb", "world series": "baseball_mlb_world_series_winner",
    # Ice Hockey
    "nhl": "icehockey_nhl", "stanley cup": "icehockey_nhl_championship_winner",
    # MMA / Boxing
    "ufc": "mma_mixed_martial_arts", "boxing": "boxing_boxing",
    # Soccer
    "premier league": "soccer_epl", "la liga": "soccer_spain_la_liga",
    "serie a": "soccer_italy_serie_a", "bundesliga": "soccer_germany_bundesliga",
    "champions league": "soccer_uefa_champs_league", "europa league": "soccer_uefa_europa_league",
    "mls": "soccer_usa_mls", "fa cup": "soccer_fa_cup",
    "copa libertadores": "soccer_conmebol_copa_libertadores",
    # Tennis — resolved dynamically, these are fallback markers
    "atp": "_tennis_atp",
    "wta": "_tennis_wta",
    "miami open": "_tennis_atp",
    "french open": "_tennis_atp", "roland garros": "_tennis_atp",
    "wimbledon": "_tennis_atp", "us open tennis": "_tennis_atp",
    "australian open": "_tennis_atp",
    # Cricket
    "ipl": "cricket_ipl", "t20": "cricket_international_t20",
    # Politics
    "presidential": "politics_us_presidential_election_winner",
    "president": "politics_us_presidential_election_winner",
}


class OddsAPIClient:
    """Fetches bookmaker odds + historical line movement from The Odds API.

    Paid plan: 20K credits/month. Budget strategy:
    - Batch per sport (1 call = all events in that sport)
    - Cache live 1h, historical 6h
    - Historical only when edge is borderline (saves ~10 credits/call)
    """

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 3600  # 1 hour cache for live odds
        self._hist_cache_ttl = 21600  # 6 hour cache for historical
        self._requests_used = 0

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_active_tennis_keys(self, gender: str = "atp") -> List[str]:
        """Discover active tennis sport keys from The Odds API /sports endpoint.

        The Odds API has separate keys per tournament (tennis_atp_miami_open, etc.).
        We query /sports to find which ones are currently active.
        """
        cache_key = f"_tennis_sports:{gender}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        prefix = f"tennis_{gender}"
        try:
            sports = self._get("/sports", {"all": "false"})
            if not sports:
                return []
            keys = [s["key"] for s in sports if isinstance(s, dict)
                    and s.get("key", "").startswith(prefix) and s.get("active")]
            self._cache[cache_key] = (keys, time.monotonic())
            if keys:
                logger.info("Active %s tennis keys: %s", gender.upper(), keys)
            return keys
        except Exception:
            return []

    def _detect_sport_key(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Detect The Odds API sport key from market data."""
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        if slug_prefix in _SPORT_KEYS:
            return _SPORT_KEYS[slug_prefix]

        q_lower = question.lower()
        for keyword, sport_key in _QUESTION_SPORT_KEYS.items():
            if keyword in q_lower:
                # Tennis markers → resolve dynamically
                if sport_key == "_tennis_atp":
                    keys = self._get_active_tennis_keys("atp")
                    return keys[0] if keys else None
                if sport_key == "_tennis_wta":
                    keys = self._get_active_tennis_keys("wta")
                    return keys[0] if keys else None
                return sport_key

        # Also check slug for tennis prefixes (atp/wta)
        if slug_prefix in ("atp", "tennis"):
            keys = self._get_active_tennis_keys("atp")
            return keys[0] if keys else None
        if slug_prefix == "wta":
            keys = self._get_active_tennis_keys("wta")
            return keys[0] if keys else None

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

    # ------------------------------------------------------------------
    # Historical Odds + Line Movement (paid plan feature)
    # ------------------------------------------------------------------

    def get_historical_odds(
        self, question: str, slug: str, tags: List[str],
        date_iso: str = "",
    ) -> Optional[Dict]:
        """Fetch historical odds at a specific date (ISO format, e.g. '2026-03-20T12:00:00Z').

        If no date given, defaults to 24h ago (opening line proxy).
        Costs ~10 credits per call — use sparingly.

        Returns same format as get_bookmaker_odds() plus 'timestamp' field.
        """
        sport_key = self._detect_sport_key(question, slug, tags)
        if not sport_key:
            return None

        if not date_iso:
            # Default to 24h ago as opening line proxy
            import datetime as dt
            t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
            date_iso = t.strftime("%Y-%m-%dT%H:%M:%SZ")

        cache_key = f"hist:{sport_key}:{date_iso}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._hist_cache_ttl:
                return self._match_historical(data, question, date_iso)

        data = self._get(f"/historical/sports/{sport_key}/odds", {
            "regions": "us,eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "date": date_iso,
        })
        if not data:
            return None

        # Historical endpoint wraps in {"data": [...], "timestamp": "..."}
        events = data.get("data", []) if isinstance(data, dict) else data
        self._cache[cache_key] = (events, time.monotonic())
        return self._match_historical(events, question, date_iso)

    def _match_historical(self, events: list, question: str, date_iso: str) -> Optional[Dict]:
        """Match a question to historical events and extract odds."""
        team_a_name, team_b_name = self._extract_teams(question)
        if not team_a_name or not team_b_name:
            return None

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
            return None

        # Extract average prob (same logic as get_bookmaker_odds)
        home_team = best_event.get("home_team", "")
        away_team = best_event.get("away_team", "")
        home_is_a = SequenceMatcher(None, team_a_name.lower(), home_team.lower()).ratio() > \
                     SequenceMatcher(None, team_a_name.lower(), away_team.lower()).ratio()

        probs_a, probs_b = [], []
        for bm in best_event.get("bookmakers", []):
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                home_odds = away_odds = None
                for o in mkt.get("outcomes", []):
                    if o.get("name") == home_team:
                        home_odds = o.get("price", 0)
                    elif o.get("name") == away_team:
                        away_odds = o.get("price", 0)
                if home_odds and away_odds and home_odds > 0 and away_odds > 0:
                    hp, ap = 1 / home_odds, 1 / away_odds
                    total = hp + ap
                    hp, ap = hp / total, ap / total
                    if home_is_a:
                        probs_a.append(hp); probs_b.append(ap)
                    else:
                        probs_a.append(ap); probs_b.append(hp)

        if not probs_a:
            return None

        return {
            "team_a": team_a_name, "team_b": team_b_name,
            "bookmaker_prob_a": round(sum(probs_a) / len(probs_a), 3),
            "bookmaker_prob_b": round(sum(probs_b) / len(probs_b), 3),
            "num_bookmakers": len(probs_a),
            "timestamp": date_iso,
        }

    def get_line_movement(
        self, question: str, slug: str, tags: List[str],
    ) -> Optional[Dict]:
        """Compare opening odds (24h ago) vs current odds to detect sharp money movement.

        Returns dict with:
            team_a, team_b, opening_prob_a, current_prob_a,
            movement_a (positive = money moving toward A),
            sharp_signal ("steam_a", "steam_b", "stable", or None)
        """
        current = self.get_bookmaker_odds(question, slug, tags)
        if not current:
            return None

        historical = self.get_historical_odds(question, slug, tags)
        if not historical:
            return None

        open_a = historical["bookmaker_prob_a"]
        curr_a = current["bookmaker_prob_a"]
        movement = curr_a - open_a  # positive = line moving toward team A

        # Sharp money signal: >3% movement is significant
        sharp_signal = "stable"
        if movement > 0.03:
            sharp_signal = "steam_a"  # Sharp money on team A
        elif movement < -0.03:
            sharp_signal = "steam_b"  # Sharp money on team B

        return {
            "team_a": current["team_a"],
            "team_b": current["team_b"],
            "opening_prob_a": open_a,
            "current_prob_a": curr_a,
            "opening_prob_b": historical["bookmaker_prob_b"],
            "current_prob_b": current["bookmaker_prob_b"],
            "movement_a": round(movement, 3),
            "sharp_signal": sharp_signal,
            "num_bookmakers": current["num_bookmakers"],
        }

    def build_line_movement_context(self, lm: Dict) -> str:
        """Build context string for AI from line movement data."""
        arrow = "->" if lm["movement_a"] >= 0 else "<-"
        signal_label = {
            "steam_a": f"SHARP MONEY on {lm['team_a']}",
            "steam_b": f"SHARP MONEY on {lm['team_b']}",
            "stable": "Lines stable (no sharp movement)",
        }.get(lm["sharp_signal"], "Unknown")

        return (
            f"\n=== LINE MOVEMENT (The Odds API) ===\n"
            f"  {lm['team_a']}: {lm['opening_prob_a']:.0%} {arrow} {lm['current_prob_a']:.0%} "
            f"({lm['movement_a']:+.1%})\n"
            f"  {lm['team_b']}: {lm['opening_prob_b']:.0%} {arrow} {lm['current_prob_b']:.0%}\n"
            f"  Signal: {signal_label}\n"
            f"  NOTE: Sharp line movement = professional bettors acting on information."
        )

    # ------------------------------------------------------------------
    # Scores (live match data — free with paid plan)
    # ------------------------------------------------------------------

    def get_live_scores(self, sport_key: str) -> Optional[List[Dict]]:
        """Fetch live scores for a sport. Returns list of score dicts."""
        return self._get(f"/sports/{sport_key}/scores", {"daysFrom": "1"})
