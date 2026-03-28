"""Pre-game scout scheduler — fetches match calendars and pre-analyzes before bets appear.

Runs 4x daily (00, 06, 12, 18 UTC). Looks 24 hours ahead for upcoming matches
via ESPN (traditional sports) and PandaScore (esports). Runs AI analysis once per
match and saves results to scout_queue.json. The main loop checks this queue each
cycle and enters immediately when matching Polymarket bets appear.
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
from src.api_usage import record_call

logger = logging.getLogger(__name__)

SCOUT_QUEUE_FILE = Path("logs/scout_queue.json")
SCOUT_MARKER_FILE = Path("logs/.last_scout")

# ESPN scoreboard endpoints return today's + upcoming games
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports"

# Leagues to scout (sport, league, display_name)
_SCOUT_LEAGUES = [
    # North America
    ("basketball", "nba", "NBA"),
    ("basketball", "mens-college-basketball", "NCAA Basketball"),
    ("football", "nfl", "NFL"),
    ("baseball", "mlb", "MLB"),
    ("hockey", "nhl", "NHL"),
    ("soccer", "usa.1", "MLS"),
    # European Soccer
    ("soccer", "eng.1", "Premier League"),
    ("soccer", "eng.2", "EFL Championship"),
    ("soccer", "esp.1", "La Liga"),
    ("soccer", "ita.1", "Serie A"),
    ("soccer", "ger.1", "Bundesliga"),
    ("soccer", "fra.1", "Ligue 1"),
    ("soccer", "ned.1", "Eredivisie"),
    ("soccer", "por.1", "Primeira Liga"),
    ("soccer", "tur.1", "Super Lig"),
    ("soccer", "sco.1", "Scottish Premiership"),
    # UEFA Competitions
    ("soccer", "uefa.champions", "Champions League"),
    ("soccer", "uefa.europa", "Europa League"),
    # South America
    ("soccer", "bra.1", "Brasileirao"),
    ("soccer", "arg.1", "Liga Argentina"),
    # Mexico
    ("soccer", "mex.1", "Liga MX"),
    # Asia
    ("soccer", "jpn.1", "J-League"),
    ("soccer", "chn.1", "Chinese Super League"),
    # Combat Sports
    ("mma", "ufc", "UFC"),
    # Tennis
    ("tennis", "atp", "ATP Tennis"),
    ("tennis", "wta", "WTA Tennis"),
]

# PandaScore games to scout
_ESPORT_GAMES = ["cs2", "lol", "dota2", "valorant"]

class ScoutScheduler:
    """Fetches upcoming match schedules and pre-analyzes them for early entry."""

    def __init__(self, sports: SportsDataClient, esports: EsportsDataClient) -> None:
        self.sports = sports
        self.esports = esports
        self._queue: Dict[str, dict] = {}
        self._last_run_ts: float = 0.0          # in-memory cooldown timestamp
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

    def run_scout(self) -> int:
        """Run the scout: fetch upcoming match calendars and sports data.

        AI analysis is deferred until a matching Polymarket bet appears (saves budget).
        Returns number of new matches scouted.
        """
        # In-memory cooldown: never run twice within 4 hours
        _COOLDOWN_SECS = 4 * 3600
        if time.time() - self._last_run_ts < _COOLDOWN_SECS:
            logger.debug("Scout cooldown active — skipping (%.1fh since last run)",
                         (time.time() - self._last_run_ts) / 3600)
            return 0

        logger.info("=== SCOUT RUN START ===")
        now = datetime.now(timezone.utc)
        new_count = 0

        # 1. Fetch upcoming traditional sports matches
        sports_matches = self._fetch_espn_upcoming()
        logger.info("ESPN: found %d upcoming matches", len(sports_matches))

        # 2. Fetch upcoming esports matches
        esports_matches = self._fetch_esports_upcoming()
        logger.info("PandaScore: found %d upcoming matches", len(esports_matches))

        all_matches = sports_matches + esports_matches

        # 3. Save match calendar to queue (NO AI calls — save budget)
        # AI analysis happens later, only when a Polymarket bet actually appears
        # Sports data (ESPN/PandaScore) is free, so we pre-fetch that
        for match in all_matches:
            scout_key = match["scout_key"]
            if scout_key in self._queue:
                logger.debug("Already scouted: %s", scout_key)
                continue

            # Pre-fetch sports context (free APIs, no budget impact)
            context_parts = []
            if match.get("sport") and match.get("league"):
                espn_ctx = self.sports.get_match_context(
                    match["question"], match.get("slug_hint", ""), []
                )
                if espn_ctx:
                    context_parts.append(espn_ctx)
            elif match.get("is_esports") and self.esports.available:
                panda_ctx = self.esports.get_match_context(
                    match["question"], match.get("tags", [])
                )
                if panda_ctx:
                    context_parts.append(panda_ctx)

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
                "sports_context": "\n".join(context_parts) if context_parts else "",
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

    def match_market(self, question: str, slug: str) -> Optional[dict]:
        """Try to match a Polymarket market to a scouted match.

        Returns the scout entry if matched, None otherwise.
        """
        q_lower = question.lower()
        slug_lower = slug.lower()

        for key, entry in self._queue.items():
            if entry.get("entered"):
                continue  # Already used this scout

            team_a = entry["team_a"].lower()
            team_b = entry["team_b"].lower()

            # Check if both team names appear in question or slug
            a_in = team_a in q_lower or team_a in slug_lower
            b_in = team_b in q_lower or team_b in slug_lower

            if a_in and b_in:
                entry["matched"] = True
                self._save_queue()
                logger.info("Scout match found: %s ↔ %s", key, slug[:40])
                return entry

            # Try abbreviated matching (first 3+ chars of each team)
            if len(team_a) >= 3 and len(team_b) >= 3:
                a_short = team_a[:4]
                b_short = team_b[:4]
                if a_short in slug_lower and b_short in slug_lower:
                    entry["matched"] = True
                    self._save_queue()
                    logger.info("Scout match (abbrev): %s ↔ %s", key, slug[:40])
                    return entry

        return None

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
                # ESPN scoreboard returns today's games by default
                # Use dates param for tomorrow too
                for day_offset in range(3):  # Today, tomorrow, day after
                    date_str = (now + timedelta(days=day_offset)).strftime("%Y%m%d")
                    url = f"{ESPN_SCOREBOARD}/{sport}/{league}/scoreboard?dates={date_str}"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()

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

                        # Only future games within 48h window
                        if event_dt < now or event_dt > cutoff:
                            continue

                        # Skip already started/completed
                        status = event.get("status", {}).get("type", {}).get("state", "")
                        if status in ("in", "post"):
                            continue

                        competitors = event.get("competitions", [{}])[0].get("competitors", [])
                        if len(competitors) != 2:
                            continue

                        team_a = competitors[0].get("team", {}).get("displayName", "")
                        team_b = competitors[1].get("team", {}).get("displayName", "")
                        if not team_a or not team_b:
                            continue

                        # Build slug hint for matching
                        slug_hint = f"{sport[:3]}-{team_a[:4].lower()}-{team_b[:4].lower()}"

                        scout_key = f"{sport}_{league}_{team_a}_{team_b}_{date_str}"
                        matches.append({
                            "scout_key": scout_key,
                            "team_a": team_a,
                            "team_b": team_b,
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
                resp = requests.get(
                    url,
                    params={"per_page": 100, "sort": "begin_at"},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                record_call("pandascore")
                if resp.status_code != 200:
                    continue

                for match in resp.json():
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

                    scout_key = f"esports_{game}_{team_a}_{team_b}_{match_dt.strftime('%Y%m%d')}"
                    matches.append({
                        "scout_key": scout_key,
                        "team_a": team_a,
                        "team_b": team_b,
                        "question": f"{team_a} vs {team_b}: Who will win? ({game.upper()})",
                        "match_time": match_dt.isoformat(),
                        "sport": "",
                        "league": "",
                        "league_name": game.upper(),
                        "slug_hint": f"{game}-{team_a[:4].lower()}-{team_b[:4].lower()}",
                        "tags": ["esports", game],
                        "is_esports": True,
                    })

                time.sleep(0.5)
            except requests.RequestException as e:
                logger.warning("PandaScore upcoming error for %s: %s", game, e)
                continue

        return matches

