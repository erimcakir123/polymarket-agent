"""The Odds API client -- bookmaker odds + historical line movement.

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
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from src.api_usage import record_call
from src.matching.odds_sport_keys import resolve_odds_key
from src.matching.pair_matcher import find_best_event_match, match_team

logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"


class OddsAPIClient:
    """Fetches bookmaker odds + historical line movement from The Odds API.

    Paid plan: 20K credits/month. Budget strategy:
    - Batch per sport (1 call = all events in that sport)
    - Cache live 1h, historical 6h
    - Historical only when edge is borderline (saves ~10 credits/call)
    """

    _REFRESH_INTERVAL_HOURS = 2  # Every 2h (12x/day). Budget: 10,800/month of 20K.

    _CACHE_FILE = Path("logs/odds_cache.json")

    # Dynamic sport discovery replaces hardcoded lists.
    # /v4/sports/?all=false returns only active/in-season sports (FREE, 0 quota).
    _ACTIVE_SPORTS_CACHE_TTL = 3600  # Re-discover every 1h

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        self._backup_key = os.getenv("ODDS_API_KEY_BACKUP", "")
        self._using_backup = False
        self._cache: Dict[str, Tuple[object, float]] = {}  # key -> (data, wall_clock_ts)
        self._cache_ttl = 28800  # 8h fallback TTL (tennis keys, etc.)
        self._hist_cache_ttl = 28800  # 8 hour cache for historical
        self._requests_used = 0
        self._notified_80 = False
        self._notified_95 = False
        self._notifier = None
        self._load_cache()  # Persist across restarts -- no cold start on cycle 1

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def set_notifier(self, notifier):
        """Set Telegram notifier for quota alerts."""
        self._notifier = notifier

    def _load_cache(self) -> None:
        """Load persisted odds cache from disk -- no cold start on bot restart."""
        try:
            if not self._CACHE_FILE.exists():
                return
            raw = json.loads(self._CACHE_FILE.read_text(encoding="utf-8"))
            self._cache = {k: (v[0], v[1]) for k, v in raw.items()}
            logger.info("Odds cache loaded: %d entries from disk", len(self._cache))
        except Exception as e:
            logger.debug("Could not load odds cache: %s", e)
            self._cache = {}

    def _save_cache(self) -> None:
        """Persist odds cache to disk so it survives bot restarts and resets."""
        try:
            self._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            serializable = {k: [v[0], v[1]] for k, v in self._cache.items()}
            tmp = self._CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(serializable, default=str), encoding="utf-8")
            tmp.replace(self._CACHE_FILE)
        except Exception as e:
            logger.debug("Could not save odds cache: %s", e)

    def _get_active_tennis_keys(self, gender: str = "atp") -> List[str]:
        """Discover active tennis sport keys from The Odds API /sports endpoint.

        The Odds API has separate keys per tournament (tennis_atp_miami_open, etc.).
        We query /sports to find which ones are currently active.
        """
        cache_key = f"_tennis_sports:{gender}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.time() - ts < self._cache_ttl:
                return data

        prefix = f"tennis_{gender}"
        try:
            sports = self._get("/sports", {"all": "false"})
            if not sports:
                return []
            keys = [s["key"] for s in sports if isinstance(s, dict)
                    and s.get("key", "").startswith(prefix) and s.get("active")]
            self._cache[cache_key] = (keys, time.time())
            if keys:
                logger.info("Active %s tennis keys: %s", gender.upper(), keys)
            return keys
        except Exception:
            return []

    @staticmethod
    def _is_wta_market(q_lower: str, slug: str) -> bool:
        """Detect if a tennis market is WTA (women's) based on question/slug cues."""
        _WTA_SIGNALS = ("wta", "women", "ladies")
        slug_lower = slug.lower() if slug else ""
        return any(s in q_lower or s in slug_lower for s in _WTA_SIGNALS)

    def _detect_sport_key(self, question: str, slug: str, tags: List[str]) -> Optional[str]:
        """Detect The Odds API sport key from market data.

        Priority: static mapping (fast) -> tennis dynamic -> discovery fallback.
        """
        # 1. Static mapping from slug prefix + tags (covers 95% of markets)
        static = resolve_odds_key(slug, tags)
        if static:
            return static

        # 2. Tennis: dynamic tournament key matching
        slug_prefix = slug.split("-")[0].lower() if slug else ""
        q_lower = question.lower()
        if slug_prefix in ("atp", "tennis"):
            return self._match_tennis_key("atp", q_lower, slug)
        if slug_prefix == "wta":
            return self._match_tennis_key("wta", q_lower, slug)
        if "wta" in q_lower or "women" in q_lower:
            return self._match_tennis_key("wta", q_lower, slug)
        if "atp" in q_lower or "tennis" in q_lower:
            return self._match_tennis_key("atp", q_lower, slug)

        # 3. Dynamic discovery (expensive — last resort)
        team_a, team_b = self._extract_teams(question)
        return self._discover_sport_key(team_a, team_b)

    def _match_tennis_key(self, gender: str, q_lower: str, slug: str) -> Optional[str]:
        """Match the best tennis tournament key from slug/question context.

        Instead of blindly returning keys[0], tries to match tournament name
        from the slug/question against active keys. Saves 5 credits vs fetching all.
        E.g. slug 'atp-miami-sinner' -> matches 'tennis_atp_miami_open'.
        """
        keys = self._get_active_tennis_keys(gender)
        if not keys:
            return None
        if len(keys) == 1:
            return keys[0]

        # Try to match tournament name from slug or question
        slug_lower = slug.lower() if slug else ""
        combined = f"{q_lower} {slug_lower}"

        # Generic words that appear in many tournament names -- skip these
        _GENERIC = {"open", "grand", "prix", "cup", "championship", "masters", "series"}

        # Score each key by how many SPECIFIC parts match the combined text
        best_key = None
        best_score = 0
        for key in keys:
            # key format: tennis_atp_miami_open -> extract ["miami", "open"]
            parts = key.split("_")[2:]
            specific = [p for p in parts if len(p) > 2 and p not in _GENERIC]
            score = sum(1 for p in specific if p in combined)
            if score > best_score:
                best_score = score
                best_key = key

        if best_key:
            return best_key

        # No specific match -> try full tournament name (e.g. "french open" in text)
        for key in keys:
            tourney = " ".join(key.split("_")[2:])  # "miami open", "french open"
            if tourney and tourney in combined:
                return key

        # Fallback: return first key
        return keys[0]

    def _discover_sport_key(self, team_a: str, team_b: str) -> Optional[str]:
        """Dynamically find the sport key for a team pair using FREE endpoints.

        1. GET /v4/sports?all=false -> all active sport keys (FREE, 0 credits)
        2. For each sport key, GET /v4/sports/{key}/events -> match team names (FREE)
        """
        if not team_a and not team_b:
            return None

        # Get active sports (cached 1h)
        cache_key = "_active_sports"
        cached = self._cache.get(cache_key)
        active_keys = None
        if cached:
            data, ts = cached
            if time.time() - ts < self._ACTIVE_SPORTS_CACHE_TTL:
                active_keys = data

        if active_keys is None:
            sports_data = self._get("/sports", {"all": "false"})
            if not sports_data:
                return None
            active_keys = [s["key"] for s in sports_data
                          if isinstance(s, dict) and s.get("key") and s.get("active")]
            self._cache[cache_key] = (active_keys, time.time())

        # Search through cached events — require BOTH teams to match
        team_a_lower = team_a.lower() if team_a else ""
        team_b_lower = team_b.lower() if team_b else ""

        best_key = None
        best_match_count = 0

        for sk in active_keys:
            events_cache_key = f"events:{sk}"
            cached_events = self._cache.get(events_cache_key)
            events = None
            if cached_events:
                data, ts = cached_events
                if time.time() - ts < self._REFRESH_INTERVAL_HOURS * 3600:
                    events = data

            if events is None:
                events = self._get(f"/sports/{sk}/events", {})
                if events and isinstance(events, list):
                    self._cache[events_cache_key] = (events, time.time())
                else:
                    continue

            for event in events:
                home = (event.get("home_team") or "").lower()
                away = (event.get("away_team") or "").lower()
                if not home or not away:
                    continue

                a_match = (team_a_lower and (
                    team_a_lower in home or home in team_a_lower or
                    team_a_lower in away or away in team_a_lower
                ))
                b_match = (team_b_lower and (
                    team_b_lower in home or home in team_b_lower or
                    team_b_lower in away or away in team_b_lower
                ))

                match_count = int(bool(a_match)) + int(bool(b_match))

                if match_count == 2:
                    logger.info("Odds API discovery: '%s/%s' -> %s (both teams)", team_a, team_b, sk)
                    return sk

                if match_count == 1 and match_count > best_match_count:
                    best_match_count = match_count
                    best_key = sk

        if best_key:
            logger.info("Odds API discovery: '%s/%s' -> %s (single team fallback)", team_a, team_b, best_key)
        return best_key

    def _past_refresh_boundary(self, cached_wall_ts: float) -> bool:
        """Check if enough time has passed since last fetch.

        Uses a simple interval (every 2h) instead of fixed UTC hours.
        """
        return (time.time() - cached_wall_ts) >= self._REFRESH_INTERVAL_HOURS * 3600

    def _api_request(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Shared HTTP layer -- makes authenticated GET to The Odds API.

        Handles: auth, quota tracking, notifications, backup key switch.
        Does NOT handle caching -- callers (_get) own their cache strategy.
        """
        if not self.available:
            return None

        params_with_key = {**params, "apiKey": self.api_key}
        try:
            resp = requests.get(f"{ODDS_API_BASE}{endpoint}", params=params_with_key, timeout=10)
            resp.raise_for_status()

            # Track remaining quota from headers
            remaining_str = resp.headers.get("x-requests-remaining", "?")
            used = resp.headers.get("x-requests-used", "?")
            logger.info("Odds API quota: %s used, %s remaining", used, remaining_str)
            self._requests_used += 1
            record_call("odds_api")

            # Quota threshold notifications
            remaining = int(remaining_str) if remaining_str != "?" else -1
            if remaining >= 0:
                total = remaining + self._requests_used
                if total > 0:
                    usage_pct = self._requests_used / total
                    if usage_pct >= 0.95 and not self._notified_95:
                        msg = "\u26a0\ufe0f Odds API %95 kullan\u0131ld\u0131 \u2014 backup key'e ge\u00e7i\u015f yak\u0131n"
                        logger.warning(msg)
                        if self._notifier:
                            self._notifier.send(msg)
                        self._notified_95 = True
                    elif usage_pct >= 0.80 and not self._notified_80:
                        msg = "\ud83d\udcca Odds API %80 kullan\u0131ld\u0131"
                        logger.warning(msg)
                        if self._notifier:
                            self._notifier.send(msg)
                        self._notified_80 = True

            return resp.json()
        except requests.RequestException as e:
            logger.warning("Odds API error: %s", e)
            if "401" in str(e) or "429" in str(e):
                if not self._using_backup and self._backup_key:
                    logger.warning("ODDS_API: Primary key exhausted, switching to backup")
                    self.api_key = self._backup_key
                    self._using_backup = True
                    return self._api_request(endpoint, params)
                logger.warning("Odds API key invalid/expired -- disabling for this session")
                self.api_key = ""
            return None

    def _get(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Make authenticated GET with scheduled refresh-boundary caching."""
        if not self.available:
            return None

        cache_key = f"{endpoint}:{sorted(params.items())}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if not self._past_refresh_boundary(ts):
                return data

        data = self._api_request(endpoint, params)
        if data is not None:
            self._cache[cache_key] = (data, time.time())
            self._save_cache()
        return data

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
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "decimal",
        })
        if not events:
            return None

        # Extract team names from question
        team_a_name, team_b_name = self._extract_teams(question)
        if not team_a_name or not team_b_name:
            return None

        # Find matching event using centralized team matcher (threshold 0.80)
        result = find_best_event_match(team_a_name, team_b_name, events)
        if not result:
            # Log available events for debugging match failures
            event_names = [(e.get("home_team", "?"), e.get("away_team", "?")) for e in events[:5]]
            logger.info("No Odds API match for '%s vs %s' in %d events. Sample: %s",
                        team_a_name, team_b_name, len(events), event_names)
            return None

        best_event, match_conf = result

        # Calculate average implied probability across bookmakers
        home_team = best_event.get("home_team", "")
        away_team = best_event.get("away_team", "")

        # Figure out which Polymarket team maps to home/away
        home_is_a, _, _ = match_team(team_a_name, home_team)

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

    def _extract_teams(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from question."""
        q = question.strip()
        # Strip sport/tour prefixes common in Polymarket questions
        _PREFIXES = [
            "ATP:", "WTA:", "Counter-Strike:", "CS2:", "CS:GO:",
            "Valorant:", "VALORANT:", "Dota 2:", "LoL:", "League of Legends:",
            "MLB:", "NBA:", "NHL:", "NFL:", "MMA:", "UFC:", "Boxing:",
            "Cricket:", "Rugby:", "Will",
        ]
        for pfx in _PREFIXES:
            if q.startswith(pfx):
                q = q[len(pfx):].strip()
                break
            if q.lower().startswith(pfx.lower()):
                q = q[len(pfx):].strip()
                break
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

