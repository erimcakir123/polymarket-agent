"""Pre-game scout scheduler -- fetches match calendars for chronological entry selection.

Daily listing at 00:01 UTC catalogs ALL upcoming matches (no enrichment).
Light refreshes at 06/12/18 UTC catch late additions.
Entry gate queries get_window() each heavy cycle for chronological selection.
Enrichment is deferred to entry_gate via discovery.resolve() (single owner).
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

from src.sports_data import SportsDataClient
from src.esports_data import EsportsDataClient
from src.cricket_data import CricketDataClient
from src.api_usage import record_call

logger = logging.getLogger(__name__)

SCOUT_QUEUE_FILE = Path("logs/scout_queue.json")
SCOUT_MARKER_FILE = Path("logs/.last_scout")

# ESPN scoreboard endpoints return today's + upcoming games
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports"

# Multi-day tournament sports — event status check skipped (see line ~489)
_TOURNAMENT_SPORTS = frozenset({"tennis", "golf"})

# Leagues to scout (sport, league, display_name)
_SCOUT_LEAGUES = [
    # === North America ===
    ("basketball", "nba", "NBA"),
    ("basketball", "wnba", "WNBA"),
    ("basketball", "mens-college-basketball", "NCAA Basketball"),
    ("football", "nfl", "NFL"),
    ("football", "college-football", "NCAA Football"),
    ("baseball", "mlb", "MLB"),
    ("hockey", "nhl", "NHL"),
    ("soccer", "usa.1", "MLS"),
    # === England (all tiers on Polymarket) ===
    ("soccer", "eng.1", "Premier League"),
    ("soccer", "eng.2", "EFL Championship"),
    ("soccer", "eng.3", "EFL League One"),
    ("soccer", "eng.4", "EFL League Two"),
    ("soccer", "eng.5", "National League"),
    ("soccer", "eng.fa", "FA Cup"),
    ("soccer", "eng.league_cup", "EFL Cup"),
    # === Top European Leagues ===
    ("soccer", "esp.1", "La Liga"),
    ("soccer", "esp.2", "La Liga 2"),
    ("soccer", "ita.1", "Serie A"),
    ("soccer", "ita.2", "Serie B"),
    ("soccer", "ger.1", "Bundesliga"),
    ("soccer", "ger.2", "2. Bundesliga"),
    ("soccer", "fra.1", "Ligue 1"),
    ("soccer", "fra.2", "Ligue 2"),
    ("soccer", "ned.1", "Eredivisie"),
    ("soccer", "por.1", "Primeira Liga"),
    ("soccer", "tur.1", "Super Lig"),
    ("soccer", "sco.1", "Scottish Premiership"),
    ("soccer", "bel.1", "Belgian Pro League"),
    ("soccer", "aut.1", "Austrian Bundesliga"),
    ("soccer", "gre.1", "Greek Super League"),
    ("soccer", "den.1", "Danish Superliga"),
    ("soccer", "nor.1", "Norwegian Eliteserien"),
    ("soccer", "swe.1", "Swedish Allsvenskan"),
    # === UEFA Competitions ===
    ("soccer", "uefa.champions", "Champions League"),
    ("soccer", "uefa.europa", "Europa League"),
    ("soccer", "uefa.europa.conf", "Europa Conference League"),
    # === South America ===
    ("soccer", "bra.1", "Brasileirao"),
    ("soccer", "bra.2", "Brasileirao Serie B"),
    ("soccer", "arg.1", "Liga Argentina"),
    ("soccer", "col.1", "Colombian Liga"),
    ("soccer", "chi.1", "Chilean Liga"),
    ("soccer", "conmebol.libertadores", "Copa Libertadores"),
    ("soccer", "conmebol.sudamericana", "Copa Sudamericana"),
    # === Mexico ===
    ("soccer", "mex.1", "Liga MX"),
    # === Asia & Middle East ===
    ("soccer", "jpn.1", "J-League"),
    ("soccer", "chn.1", "Chinese Super League"),
    ("soccer", "ksa.1", "Saudi Pro League"),
    ("soccer", "ind.1", "Indian Super League"),
    ("soccer", "aus.1", "A-League"),
    # === Additional South America (Polymarket active) ===
    ("soccer", "per.1", "Peruvian Liga 1"),
    ("soccer", "bol.1", "Bolivian Liga"),
    ("soccer", "uru.1", "Uruguayan Liga"),
    ("soccer", "ecu.1", "Ecuadorian LigaPro"),
    ("soccer", "par.1", "Paraguayan Liga"),
    ("soccer", "ven.1", "Venezuelan Liga"),
    # === Additional Europe (Polymarket active, ESPN verified) ===
    ("soccer", "cze.1", "Czech First League"),
    ("soccer", "rou.1", "Romanian Liga I"),
    ("soccer", "irl.1", "Irish Premier Division"),
    ("soccer", "cyp.1", "Cypriot First Division"),
    # === Africa ===
    ("soccer", "rsa.1", "South African Premiership"),
    # === Women's Soccer ===
    ("soccer", "usa.nwsl", "NWSL"),
    # === International ===
    ("soccer", "fifa.friendly", "International Friendly"),
    ("soccer", "fifa.worldq", "FIFA World Cup Qualifiers"),
    ("soccer", "fifa.world", "FIFA World Cup"),
    # === Rugby (ESPN uses numeric league IDs) ===
    ("rugby", "242041", "Super Rugby Pacific"),
    ("rugby", "267979", "Premiership Rugby"),
    ("rugby", "289262", "Major League Rugby"),
    # === Rugby League ===
    ("rugby-league", "3", "NRL/Super League"),
    # === Combat Sports ===
    ("mma", "ufc", "UFC"),
    # === Tennis ===
    ("tennis", "atp", "ATP Tennis"),
    ("tennis", "wta", "WTA Tennis"),
    # NOTE: F1 excluded -- multi-competitor events, not moneyline head-to-head
    # === Golf ===
    ("golf", "pga", "PGA Tour"),
    ("golf", "lpga", "LPGA Tour"),
    # === Lacrosse (Polymarket has pll, wll slug codes) ===
    ("lacrosse", "pll", "PLL"),
    ("lacrosse", "nll", "NLL"),
    # NOTE: Cricket is scouted via CricketData API, not ESPN (ESPN 404s for cricket)
    # NOTE: Slovak, Croatian, Egyptian, Ukrainian, Korean leagues — ESPN 400, no endpoint
    # NOTE: KBO (Korean baseball), J2 League — ESPN 400, no endpoint
    # NOTE: F1/NASCAR excluded — multi-competitor events, not moneyline head-to-head
    # NOTE: AFL (Australian football) excluded — no Polymarket slug codes
]

# Estimated match duration in minutes per ESPN sport (for live <50% filter)
_LIVE_DURATION: dict[str, int] = {
    "basketball": 150, "football": 195, "baseball": 180, "hockey": 150,
    "soccer": 95, "mma": 75, "tennis": 120, "golf": 300,
    "rugby": 100, "rugby-league": 100, "lacrosse": 90,
}

# PandaScore games to scout
# PandaScore games to scout (all games with Polymarket slug codes)
# Full stats: csgo, lol, dota2, valorant, ow
# Fixtures: r6siege, mlbb, rl, codmw, pubg, starcraft-2, starcraft-brood-war, kog, lol-wild-rift, fifa
_ESPORT_GAMES = [
    "csgo", "lol", "dota2", "valorant", "ow",
    "r6siege", "mlbb", "rl", "codmw", "pubg",
    "starcraft-2", "starcraft-brood-war",
    "kog", "lol-wild-rift", "fifa",
]

class ScoutScheduler:
    """Fetches upcoming match schedules and pre-analyzes them for early entry."""

    def __init__(self, sports: SportsDataClient, esports: EsportsDataClient,
                 cricket: Optional[CricketDataClient] = None) -> None:
        self.sports = sports
        self.esports = esports
        self.cricket = cricket or CricketDataClient()
        self._queue: Dict[str, dict] = {}
        self._last_run_ts: float = 0.0          # in-memory cooldown timestamp
        self._last_daily_ts: float = 0.0         # separate cooldown for daily listing
        self._load_queue()

    def _load_queue(self) -> None:
        """Load existing scout queue from disk."""
        if SCOUT_QUEUE_FILE.exists():
            try:
                self._queue = json.loads(SCOUT_QUEUE_FILE.read_text(encoding="utf-8"))
                # Prune expired entries (match time passed)
                now = datetime.now(timezone.utc)
                expired = [
                    k for k, v in self._queue.items()
                    if v.get("match_time") and
                    datetime.fromisoformat(v["match_time"]).replace(tzinfo=timezone.utc) < now - timedelta(hours=4)
                ]
                for k in expired:
                    del self._queue[k]
                if expired:
                    self._save_queue()
                    logger.info("Pruned %d expired scout entries", len(expired))
                if self._queue:
                    logger.info("Loaded %d scout entries from disk", len(self._queue))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load scout queue: %s", e)
                self._queue = {}

    def _save_queue(self) -> None:
        """Persist scout queue to disk."""
        SCOUT_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SCOUT_QUEUE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._queue, indent=2, default=str), encoding="utf-8")
        tmp.replace(SCOUT_QUEUE_FILE)

    def should_run_scout(self) -> bool:
        """Check if it's time for a scout run (4x daily: 00, 06, 12, 18 UTC)."""
        # Cold start: if queue is empty, run immediately
        if not self._queue:
            return True
        now = datetime.now(timezone.utc)
        current_hour = now.hour

        # Scout windows: every 6 hours
        if current_hour not in (0, 6, 12, 18):
            return False

        # Check if we already scouted in this window
        if SCOUT_MARKER_FILE.exists():
            try:
                last = datetime.fromisoformat(SCOUT_MARKER_FILE.read_text().strip())
                hours_since = (now - last).total_seconds() / 3600
                if hours_since < 5:  # Don't run again within 5 hours
                    return False
            except (ValueError, OSError):
                pass

        return True

    def is_daily_listing_time(self) -> bool:
        """Returns True only when UTC hour == 0 (daily listing window)."""
        return datetime.now(timezone.utc).hour == 0

    def run_daily_listing(self) -> int:
        """Full daily scan at 00:01 UTC — lists all upcoming matches, NO enrichment.

        Identical to run_scout() except: no sports.get_match_context or
        esports.get_match_context calls. Every entry gets sports_context="".
        Returns count of new entries added.
        """
        # Same cooldown logic as run_scout()
        _COOLDOWN_SECS = 4 * 3600
        if time.time() - self._last_daily_ts < _COOLDOWN_SECS:
            logger.debug("Daily listing cooldown active -- skipping (%.1fh since last run)",
                         (time.time() - self._last_daily_ts) / 3600)
            return 0

        logger.info("=== DAILY LISTING START ===")
        now = datetime.now(timezone.utc)
        new_count = 0

        sports_matches = self._fetch_espn_upcoming()
        logger.info("ESPN: found %d upcoming matches", len(sports_matches))

        esports_matches = self._fetch_esports_upcoming()
        logger.info("PandaScore: found %d upcoming matches", len(esports_matches))

        cricket_matches = self._fetch_cricket_upcoming()
        logger.info("CricketData: found %d upcoming matches", len(cricket_matches))

        all_matches = sports_matches + esports_matches + cricket_matches

        for match in all_matches:
            scout_key = match["scout_key"]
            if scout_key in self._queue:
                continue

            entry = {
                "scout_key": scout_key,
                "team_a": match["team_a"],
                "team_b": match["team_b"],
                "question": match["question"],
                "match_time": match.get("match_time", ""),
                "sport": match.get("sport", ""),
                "league": match.get("league", ""),
                "league_name": match.get("league_name", ""),
                "is_esports": match.get("is_esports", False),
                "slug_hint": match.get("slug_hint", ""),
                "tags": match.get("tags", []),
                "abbrev_a": match.get("abbrev_a", ""),
                "abbrev_b": match.get("abbrev_b", ""),
                "short_a": match.get("short_a", ""),
                "short_b": match.get("short_b", ""),
                "sports_context": "",
                "scouted_at": now.isoformat(),
                "matched": False,
                "entered": False,
            }

            self._queue[scout_key] = entry
            new_count += 1
            logger.info("Listed: %s vs %s (%s) @ %s",
                        match["team_a"], match["team_b"],
                        match.get("league_name", "esports"),
                        match.get("match_time", "?")[:16])

        self._save_queue()

        SCOUT_MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCOUT_MARKER_FILE.write_text(now.isoformat(), encoding="utf-8")

        self._last_daily_ts = time.time()
        logger.info("=== DAILY LISTING COMPLETE: %d new, %d total in queue ===", new_count, len(self._queue))
        return new_count

    def get_window(self, hours_ahead: float) -> List[dict]:
        """Return scout queue entries within the time window.

        Includes matches that started up to 2h ago (still tradeable if
        <50% elapsed — downstream filters enforce that) plus matches
        starting within the next *hours_ahead* hours.
        Sorted by match_time ascending. Skips entries where entered=True.
        Each returned dict includes 'scout_key' field.
        """
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=2)
        cutoff = now + timedelta(hours=hours_ahead)
        results = []

        for key, entry in self._queue.items():
            if entry.get("entered"):
                continue
            mt_str = entry.get("match_time", "")
            if not mt_str:
                continue
            try:
                mt = datetime.fromisoformat(mt_str)
                if mt.tzinfo is None:
                    mt = mt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if lookback <= mt <= cutoff:
                result = dict(entry)
                result["scout_key"] = key
                results.append((mt, result))

        results.sort(key=lambda x: x[0])
        return [r for _, r in results]

    def run_scout(self) -> int:
        """Run the scout: fetch upcoming match calendars and sports data.

        AI analysis is deferred until a matching Polymarket bet appears (saves budget).
        Returns number of new matches scouted.
        """
        # In-memory cooldown: never run twice within 4 hours
        _COOLDOWN_SECS = 4 * 3600
        if time.time() - self._last_run_ts < _COOLDOWN_SECS:
            logger.debug("Scout cooldown active -- skipping (%.1fh since last run)",
                         (time.time() - self._last_run_ts) / 3600)
            return 0

        logger.info("=== SCOUT RUN START ===")
        now = datetime.now(timezone.utc)
        new_count = 0

        # 1. Fetch upcoming traditional sports matches
        sports_matches = self._fetch_espn_upcoming()
        logger.info("ESPN: found %d upcoming matches", len(sports_matches))

        # 2. Fetch upcoming esports matches (disabled: 0W/5L, -$21, no odds data)
        # Re-enable with damage-ladder exit strategy — see plans/nifty-snacking-hearth.md
        esports_matches: list[dict] = []
        # esports_matches = self._fetch_esports_upcoming()
        logger.info("PandaScore: SKIPPED (esports disabled)")

        # 3. Fetch upcoming cricket matches
        cricket_matches = self._fetch_cricket_upcoming()
        logger.info("CricketData: found %d upcoming matches", len(cricket_matches))

        all_matches = sports_matches + esports_matches + cricket_matches

        # 4. Save match calendar to queue (NO AI calls -- save budget)
        # AI analysis happens later, only when a Polymarket bet actually appears
        # Sports data (ESPN/PandaScore) is free, so we pre-fetch that
        for match in all_matches:
            scout_key = match["scout_key"]
            if scout_key in self._queue:
                logger.debug("Already scouted: %s", scout_key)
                continue

            entry = {
                "scout_key": scout_key,
                "team_a": match["team_a"],
                "team_b": match["team_b"],
                "question": match["question"],
                "match_time": match.get("match_time", ""),
                "sport": match.get("sport", ""),
                "league": match.get("league", ""),
                "league_name": match.get("league_name", ""),
                "is_esports": match.get("is_esports", False),
                "slug_hint": match.get("slug_hint", ""),
                "tags": match.get("tags", []),
                "abbrev_a": match.get("abbrev_a", ""),
                "abbrev_b": match.get("abbrev_b", ""),
                "short_a": match.get("short_a", ""),
                "short_b": match.get("short_b", ""),
                "sports_context": "",
                "scouted_at": now.isoformat(),
                "matched": False,  # Set True when matched to Polymarket bet
                "entered": False,  # Set True when position opened
            }

            self._queue[scout_key] = entry
            new_count += 1
            logger.info("Scouted: %s vs %s (%s) @ %s",
                        match["team_a"], match["team_b"],
                        match.get("league_name", "esports"),
                        match.get("match_time", "?")[:16])

        self._save_queue()

        # Mark scout run
        SCOUT_MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCOUT_MARKER_FILE.write_text(now.isoformat(), encoding="utf-8")

        self._last_run_ts = time.time()   # update cooldown timestamp
        logger.info("=== SCOUT COMPLETE: %d new, %d total in queue ===", new_count, len(self._queue))
        return new_count

    def mark_entered(self, scout_key: str) -> None:
        """Mark a scout entry as entered (position opened)."""
        if scout_key in self._queue:
            self._queue[scout_key]["entered"] = True
            self._save_queue()

    def get_upcoming_match_times(self) -> List[datetime]:
        """Return match times for all unmatched scout entries (for polling speedup)."""
        times = []
        for entry in self._queue.values():
            if entry.get("entered") or not entry.get("match_time"):
                continue
            try:
                mt = datetime.fromisoformat(entry["match_time"])
                times.append(mt)
            except (ValueError, TypeError):
                pass
        return times

    def _fetch_espn_upcoming(self) -> List[dict]:
        """Fetch upcoming matches from ESPN scoreboard (next 24 hours)."""
        matches = []
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=24)

        for sport, league, display_name in _SCOUT_LEAGUES:
            try:
                # Yesterday (-1) catches US prime-time games that fall on previous UTC day
                # (we're UTC+3, so 21:00 ET = 01:00 UTC next day, but ESPN dates by ET)
                for day_offset in range(-1, 3):  # Yesterday, today, tomorrow, day after
                    date_str = (now + timedelta(days=day_offset)).strftime("%Y%m%d")
                    url = f"{ESPN_SCOREBOARD}/{sport}/{league}/scoreboard?dates={date_str}"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    time.sleep(0.2)  # ESPN rate limiting

                    for event in data.get("events", []):
                        event_date_str = event.get("date", "")
                        if not event_date_str:
                            continue

                        try:
                            event_dt = datetime.fromisoformat(
                                event_date_str.replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            continue

                        # Only games within window: up to 24h ahead, or live (<50% elapsed)
                        # Tournament sports (tennis, golf): event_date is tournament
                        # start, not individual match time — skip this check so
                        # comp-level dates are used instead.
                        status = event.get("status", {}).get("type", {}).get("state", "")

                        if sport not in _TOURNAMENT_SPORTS:
                            if status == "post":
                                continue  # Finished — skip
                            if status == "in":
                                # Live game: allow if <50% of estimated duration elapsed
                                est_min = _LIVE_DURATION.get(sport, 90)
                                elapsed_min = (now - event_dt).total_seconds() / 60
                                if elapsed_min > est_min * 0.5:
                                    continue  # Past halfway — skip
                                # else: live but <50% elapsed, keep it
                            elif event_dt < now - timedelta(hours=4) or event_dt > cutoff:
                                continue  # Too old or too far out

                        # --- Sport-specific parsers ---
                        # Each sport has different ESPN response structures.

                        # TENNIS: tournament/groupings with athlete (not team)
                        if sport == "tennis":
                            for grouping in event.get("groupings", []):
                                group_name = grouping.get("grouping", {}).get("displayName", "")
                                if "double" in group_name.lower() or "mixed" in group_name.lower():
                                    continue
                                for comp in grouping.get("competitions", []):
                                    comp_status = comp.get("status", {}).get("type", {}).get("state", "")
                                    if comp_status in ("in", "post"):
                                        continue
                                    competitors = comp.get("competitors", [])
                                    if len(competitors) != 2:
                                        continue
                                    player_a = competitors[0].get("athlete", {}).get("displayName", "")
                                    player_b = competitors[1].get("athlete", {}).get("displayName", "")
                                    if not player_a or not player_b:
                                        continue
                                    comp_date = comp.get("date", event_date_str)
                                    try:
                                        comp_dt = datetime.fromisoformat(comp_date.replace("Z", "+00:00"))
                                    except (ValueError, TypeError):
                                        comp_dt = event_dt
                                    # Skip comps outside the 48h window
                                    if comp_dt < now or comp_dt > cutoff:
                                        continue
                                    abbrev_a = competitors[0].get("athlete", {}).get("shortName", player_a)
                                    abbrev_b = competitors[1].get("athlete", {}).get("shortName", player_b)
                                    slug_hint = f"ten-{player_a[:4].lower()}-{player_b[:4].lower()}"
                                    scout_key = f"{sport}_{league}_{player_a}_{player_b}_{date_str}"
                                    matches.append({
                                        "scout_key": scout_key,
                                        "team_a": player_a,
                                        "team_b": player_b,
                                        "abbrev_a": abbrev_a,
                                        "abbrev_b": abbrev_b,
                                        "espn_event_id": event.get("id", ""),
                                        "question": f"{player_a} vs {player_b}: Who will win?",
                                        "match_time": comp_dt.isoformat(),
                                        "sport": sport,
                                        "league": league,
                                        "league_name": display_name,
                                        "slug_hint": slug_hint,
                                        "tags": ["sports", display_name.lower()],
                                        "is_esports": False,
                                    })
                            continue

                        # MMA: flat competitions[], each fight = 1 competition with 2 athlete competitors
                        if sport == "mma":
                            for comp in event.get("competitions", []):
                                comp_status = comp.get("status", {}).get("type", {}).get("state", "")
                                if comp_status in ("in", "post"):
                                    continue
                                competitors = comp.get("competitors", [])
                                if len(competitors) != 2:
                                    continue
                                fighter_a = competitors[0].get("athlete", {}).get("displayName", "")
                                fighter_b = competitors[1].get("athlete", {}).get("displayName", "")
                                if not fighter_a or not fighter_b:
                                    continue
                                abbrev_a = competitors[0].get("athlete", {}).get("shortName", fighter_a)
                                abbrev_b = competitors[1].get("athlete", {}).get("shortName", fighter_b)
                                slug_hint = f"mma-{fighter_a[:4].lower()}-{fighter_b[:4].lower()}"
                                scout_key = f"{sport}_{league}_{fighter_a}_{fighter_b}_{date_str}"
                                matches.append({
                                    "scout_key": scout_key,
                                    "team_a": fighter_a,
                                    "team_b": fighter_b,
                                    "abbrev_a": abbrev_a,
                                    "abbrev_b": abbrev_b,
                                    "espn_event_id": event.get("id", ""),
                                    "question": f"{fighter_a} vs {fighter_b}: Who will win?",
                                    "match_time": event_dt.isoformat(),
                                    "sport": sport,
                                    "league": league,
                                    "league_name": display_name,
                                    "slug_hint": slug_hint,
                                    "tags": ["sports", display_name.lower()],
                                    "is_esports": False,
                                })
                            continue

                        # STANDARD (soccer, basketball, football, baseball, hockey):
                        # flat competitions[] with team.displayName
                        competitors = event.get("competitions", [{}])[0].get("competitors", [])
                        if len(competitors) != 2:
                            continue

                        team_a = competitors[0].get("team", {}).get("displayName", "")
                        team_b = competitors[1].get("team", {}).get("displayName", "")
                        if not team_a or not team_b:
                            continue

                        abbrev_a = competitors[0].get("team", {}).get("abbreviation", "")
                        abbrev_b = competitors[1].get("team", {}).get("abbreviation", "")
                        short_a = competitors[0].get("team", {}).get("shortDisplayName", "")
                        short_b = competitors[1].get("team", {}).get("shortDisplayName", "")
                        slug_hint = f"{sport[:3]}-{team_a[:4].lower()}-{team_b[:4].lower()}"
                        scout_key = f"{sport}_{league}_{team_a}_{team_b}_{date_str}"
                        matches.append({
                            "scout_key": scout_key,
                            "team_a": team_a,
                            "team_b": team_b,
                            "abbrev_a": abbrev_a,
                            "abbrev_b": abbrev_b,
                            "short_a": short_a,
                            "short_b": short_b,
                            "espn_event_id": event.get("id", ""),
                            "question": f"{team_a} vs {team_b}: Who will win?",
                            "match_time": event_dt.isoformat(),
                            "sport": sport,
                            "league": league,
                            "league_name": display_name,
                            "slug_hint": slug_hint,
                            "tags": ["sports", display_name.lower()],
                            "is_esports": False,
                        })

                time.sleep(0.5)  # Be gentle with ESPN
            except requests.RequestException as e:
                logger.warning("ESPN scoreboard error for %s/%s: %s", sport, league, e)
                continue

        return matches

    def _fetch_esports_upcoming(self) -> List[dict]:
        """Fetch upcoming esports matches from PandaScore (next 24 hours)."""
        if not self.esports.available:
            return []

        matches = []
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=24)

        for game in _ESPORT_GAMES:
            try:
                api_key = self.esports.api_key
                url = f"https://api.pandascore.co/{game}/matches/upcoming"
                page = 1

                while True:
                    resp = requests.get(
                        url,
                        params={"page[size]": 100, "sort": "begin_at", "page[number]": page},
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10,
                    )
                    record_call("pandascore")
                    if resp.status_code != 200:
                        break

                    page_results = resp.json()

                    for match in page_results:
                        begin_at = match.get("begin_at", "")
                        if not begin_at:
                            continue

                        try:
                            match_dt = datetime.fromisoformat(begin_at.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            continue

                        if match_dt < now or match_dt > cutoff:
                            continue

                        opponents = match.get("opponents", [])
                        if len(opponents) != 2:
                            continue

                        team_a = opponents[0].get("opponent", {}).get("name", "")
                        team_b = opponents[1].get("opponent", {}).get("name", "")
                        if not team_a or not team_b:
                            continue

                        abbrev_a = opponents[0].get("opponent", {}).get("acronym", "") or ""
                        abbrev_b = opponents[1].get("opponent", {}).get("acronym", "") or ""
                        scout_key = f"esports_{game}_{team_a}_{team_b}_{match_dt.strftime('%Y%m%d')}"
                        matches.append({
                            "scout_key": scout_key,
                            "team_a": team_a,
                            "team_b": team_b,
                            "abbrev_a": abbrev_a,
                            "abbrev_b": abbrev_b,
                            "pandascore_match_id": match.get("id"),
                            "question": f"{team_a} vs {team_b}: Who will win? ({game.upper()})",
                            "match_time": match_dt.isoformat(),
                            "sport": "",
                            "league": "",
                            "league_name": game.upper(),
                            "slug_hint": f"{game}-{team_a[:4].lower()}-{team_b[:4].lower()}",
                            "tags": ["esports", game],
                            "is_esports": True,
                        })

                    # Pagination: if page returned 100 results, there may be more
                    if len(page_results) >= 100:
                        page += 1
                        time.sleep(0.3)  # Rate limit between pages
                    else:
                        break

                time.sleep(0.5)
            except requests.RequestException as e:
                logger.warning("PandaScore upcoming error for %s: %s", game, e)
                continue

        return matches

    def _fetch_cricket_upcoming(self) -> List[dict]:
        """Fetch upcoming/live cricket matches from CricketData.org API."""
        if not self.cricket.available:
            return []

        current = self.cricket.get_current_matches()
        if not current:
            return []

        matches = []
        now = datetime.now(timezone.utc)

        _type_map = {
            "t20": "T20", "odi": "ODI", "test": "Test",
            "t20i": "T20 International",
        }

        for m in current:
            if m.get("ended"):
                continue

            teams = m.get("teams", [])
            if len(teams) < 2:
                continue

            team_a, team_b = teams[0], teams[1]
            if not team_a or not team_b:
                continue

            match_type = m.get("match_type", "").lower()
            match_name = m.get("name", "")
            match_date = m.get("date", "")

            match_dt = None
            if match_date:
                try:
                    match_dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            if not match_dt:
                match_dt = now

            league_name = _type_map.get(match_type, "Cricket")
            if "ipl" in match_name.lower():
                league_name = "IPL"
            elif "psl" in match_name.lower():
                league_name = "PSL"

            shortnames = m.get("shortnames", {})
            abbrev_a = shortnames.get(team_a, "")
            abbrev_b = shortnames.get(team_b, "")

            date_str = match_dt.strftime("%Y-%m-%d")
            scout_key = f"cricket_{team_a}_{team_b}_{date_str}"
            slug_hint = f"cric-{team_a[:4].lower()}-{team_b[:4].lower()}"

            matches.append({
                "scout_key": scout_key,
                "team_a": team_a,
                "team_b": team_b,
                "abbrev_a": abbrev_a,
                "abbrev_b": abbrev_b,
                "question": f"{team_a} vs {team_b}: Who will win? (Cricket {league_name})",
                "match_time": match_dt.isoformat(),
                "sport": "cricket",
                "league": match_type,
                "league_name": league_name,
                "slug_hint": slug_hint,
                "tags": ["cricket", league_name.lower()],
                "is_esports": False,
            })

        return matches
