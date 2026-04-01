"""PandaScore API client for esports match data (CS2, LoL, Dota2, Valorant)."""
from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from src.team_matcher import match_team

from src.api_usage import record_call

logger = logging.getLogger(__name__)

PANDASCORE_BASE = "https://api.pandascore.co"

# Map Polymarket tags + PandaScore videogame.slug → valid API path slug.
# PandaScore API endpoints use: /csgo/, /lol/, /dota2/, /valorant/, /ow/, /r6-siege/ etc.
# Polymarket tags use: "counter-strike", "league-of-legends", "dota-2", etc.
# PandaScore videogame.slug returns: "cs-go", "league-of-legends", "dota-2", etc.
_GAME_SLUGS = {
    # CS2 — Polymarket tag "counter-strike", PandaScore returns "cs-go"
    "cs2": "csgo", "csgo": "csgo", "counter-strike": "csgo", "cs-go": "csgo",
    # LoL — Polymarket tag "league-of-legends"
    "lol": "lol", "league-of-legends": "lol",
    # Dota 2 — Polymarket tag "dota-2"
    "dota2": "dota2", "dota-2": "dota2",
    # Valorant
    "valorant": "valorant",
    # R6 Siege — PandaScore returns "r6-siege"
    "r6-siege": "r6-siege",
    # Overwatch — PandaScore returns "ow"
    "ow": "ow", "overwatch": "ow",
    # Mobile Legends
    "mobile-legends": "mobile-legends-bang-bang",
    # StarCraft 2
    "starcraft-2": "starcraft-2", "starcraft": "starcraft-2",
}

# Team aliases moved to centralized src/team_matcher.py


class EsportsDataClient:
    """Fetches team stats and match history from PandaScore free tier."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or os.getenv("PANDASCORE_API_KEY", "")
        self._last_call: float = 0.0
        self._cache: Dict[str, Tuple[object, float]] = {}  # key -> (data, timestamp)
        self._cache_ttl = 1800  # 30 min cache
        self._session = requests.Session()

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
        """Make authenticated GET request to PandaScore with retry on 500/timeout."""
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

        last_err = None
        for attempt in range(2):  # 1 try + 1 retry
            try:
                resp = self._session.get(
                    f"{PANDASCORE_BASE}{endpoint}",
                    headers=headers,
                    params=params or {},
                    timeout=5,
                )
                resp.raise_for_status()
                record_call("pandascore")
                data = resp.json()
                self._cache[cache_key] = (data, time.monotonic())
                return data
            except requests.RequestException as e:
                last_err = e
                if attempt == 0:
                    logger.info("PandaScore retry after error: %s", e)
                    time.sleep(2)
                    continue

        logger.warning("PandaScore API error (after retry): %s", last_err)
        return None

    def detect_game(self, question: str, tags: List[str]) -> Optional[str]:
        """Detect which esports game a market is about. Returns PandaScore slug."""
        q_lower = question.lower()
        tags_lower = [t.lower() for t in tags]

        # Check tags first (fast path)
        for tag in tags_lower:
            for keyword, slug in _GAME_SLUGS.items():
                if keyword in tag:
                    return slug

        # Check question text
        for keyword, slug in _GAME_SLUGS.items():
            if keyword in q_lower:
                return slug

        # Dynamic: search PandaScore for team name
        team_a, _ = self._extract_team_names(question)
        if team_a:
            match = self.search_match(team_a)
            if match:
                videogame = match.get("videogame", {})
                raw_slug = videogame.get("slug", "")
                if raw_slug:
                    # Normalize PandaScore slug (e.g. "cs-go" → "csgo")
                    slug = _GAME_SLUGS.get(raw_slug, raw_slug)
                    logger.info("PandaScore search: '%s' -> game=%s (raw=%s)", team_a, slug, raw_slug)
                    return slug

        return None

    def search_match(self, team_name: str) -> Optional[dict]:
        """Search PandaScore for an upcoming match by team name.

        Uses the search[name] parameter on /matches/upcoming endpoint.
        Returns the first matching match dict, or None.
        """
        if not self.available or not team_name:
            return None

        cache_key = f"search_match:{team_name.lower().strip()}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data

        matches = self._get("/matches/upcoming", {
            "search[name]": team_name,
            "filter[status]": "not_started,running",
            "per_page": 10,
            "sort": "begin_at",
        })

        if matches and isinstance(matches, list):
            # Client-side tier filter: skip D/C tier (manipulation-prone)
            for m in matches:
                tier = (m.get("tournament", {}).get("tier") or "").lower()
                if tier in ("d", "c"):
                    continue
                self._cache[cache_key] = (m, time.monotonic())
                return m

        self._cache[cache_key] = (None, time.monotonic())
        return None

    def _get_upcoming_match(
        self, game_slug: str, team_a: str, team_b: str,
    ) -> Optional[dict]:
        """Find the upcoming match between two teams. Returns full match dict with
        tournament, tier, detailed_stats, scheduled_at, status, etc."""
        matches = self._get(f"/{game_slug}/matches/upcoming", {
            "search[name]": team_a,
            "filter[status]": "not_started,running",
            "per_page": 10,
            "sort": "begin_at",
        })
        if not matches:
            return None

        # Find the match that also contains team_b (client-side tier filter)
        b_lower = team_b.lower()
        for m in matches:
            # Skip D/C tier tournaments (manipulation-prone)
            tier = (m.get("tournament", {}).get("tier") or "").lower()
            if tier in ("d", "c"):
                continue
            name = (m.get("name") or "").lower()
            opponents = m.get("opponents", [])
            opp_names = [
                (opp.get("opponent", {}).get("name") or "").lower()
                for opp in opponents
            ]
            if b_lower in name or any(b_lower in n for n in opp_names):
                return m
            # Also check acronyms
            opp_acronyms = [
                (opp.get("opponent", {}).get("acronym") or "").lower()
                for opp in opponents
            ]
            if any(b_lower in a for a in opp_acronyms if a):
                return m

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
                if "(" in team_a:
                    team_a = team_a[:team_a.index("(")].strip()
                if "(" in team_b:
                    team_b = team_b[:team_b.index("(")].strip()
                # Clean up trailing tournament info after " - "
                if " - " in team_b:
                    team_b = team_b[:team_b.index(" - ")].strip()
                return team_a, team_b

        return None, None

    def _fuzzy_match_team(self, name: str, candidates: List[dict]) -> Optional[dict]:
        """Find best matching team from PandaScore results using centralized team matcher."""
        best_match = None
        best_score = 0.0

        for team in candidates:
            team_name = team.get("name", "")
            team_acronym = team.get("acronym") or ""
            team_slug = team.get("slug", "")

            # Try all candidate fields through centralized matcher
            for candidate in [team_name, team_acronym, team_slug]:
                if not candidate:
                    continue
                is_match, score, method = match_team(name, candidate)
                if is_match and score > best_score:
                    best_score = score
                    best_match = team

        if best_score >= 0.80:
            return best_match
        return None

    # ------------------------------------------------------------------
    # Roster cache for change detection
    # ------------------------------------------------------------------
    _ROSTER_CACHE_PATH = Path("logs/roster_cache.json")
    _ROSTER_CACHE_TTL_H = 24
    _ROSTER_CACHE_MAX_AGE_DAYS = 30

    def _load_roster_cache(self) -> Dict:
        """Load roster cache from disk. Returns {} on any failure."""
        try:
            if self._ROSTER_CACHE_PATH.exists():
                data = json.loads(self._ROSTER_CACHE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, OSError, ValueError):
            logger.debug("Roster cache load failed — treating as empty")
        return {}

    def _save_roster_cache(self, cache: Dict) -> None:
        """Atomic write roster cache to disk with 30-day auto-prune."""
        try:
            # Prune entries older than 30 days
            cutoff = datetime.now(timezone.utc).timestamp() - (self._ROSTER_CACHE_MAX_AGE_DAYS * 86400)
            pruned = {}
            for k, v in cache.items():
                updated = v.get("updated_at", "")
                try:
                    ts = datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp()
                    if ts > cutoff:
                        pruned[k] = v
                except (ValueError, TypeError):
                    pruned[k] = v  # Keep if can't parse date
            # Atomic write
            self._ROSTER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._ROSTER_CACHE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(pruned, indent=2), encoding="utf-8")
            tmp.replace(self._ROSTER_CACHE_PATH)
        except OSError as e:
            logger.warning("Roster cache save failed: %s", e)

    def detect_roster_changes(
        self, team_id: int, team_name: str, current_roster: List[str],
    ) -> Optional[Dict]:
        """Detect roster changes by comparing current roster vs cached snapshot.

        Returns {new_players: [...], departed_players: [...]} or None if no change / first run.
        """
        if not current_roster:
            return None

        cache = self._load_roster_cache()
        key = f"team_{team_id}"
        entry = cache.get(key)
        current_set = set(current_roster)
        result = None

        if entry:
            # TTL debounce: skip comparison if cached entry is fresh (<TTL hours)
            # Prevents false alerts from transient PandaScore partial responses
            updated_str = entry.get("updated_at", "")
            try:
                updated_ts = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - updated_ts).total_seconds() / 3600
                if age_hours < self._ROSTER_CACHE_TTL_H:
                    return None  # Too fresh to re-compare
            except (ValueError, TypeError):
                pass  # Can't parse date — proceed with comparison

            cached_players = set(entry.get("players", []))
            new_players = sorted(current_set - cached_players)
            departed_players = sorted(cached_players - current_set)
            if new_players or departed_players:
                result = {"new_players": new_players, "departed_players": departed_players}

        # Update cache (keeps updated_at fresh for prune logic)
        cache[key] = {
            "name": team_name,
            "players": sorted(current_set),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_roster_cache(cache)
        return result

    # ------------------------------------------------------------------
    # Enrichment helpers
    # ------------------------------------------------------------------

    def _enrich_team_data(
        self, result: Dict, team: Dict, matches: List[Dict], team_id: int,
    ) -> None:
        """Add roster, location, tier records, LAN/online records, game duration
        to an existing team result dict. Mutates result in-place.
        Designed to be called inside try/except — any failure is non-fatal.
        """
        # --- Roster & location from team object ---
        result["location"] = team.get("location") or None
        players_raw = team.get("players") or []
        roster = [p.get("name", "") for p in players_raw if p.get("active", True) and p.get("name")]
        result["roster"] = roster

        # --- Roster change detection ---
        roster_change = self.detect_roster_changes(team_id, result["team_name"], roster)
        if roster_change:
            result["roster_change"] = roster_change

        # --- Tier & LAN records from match history ---
        tier_records: Dict[str, Dict[str, int]] = {}  # tier -> {w, l}
        lan_w, lan_l, online_w, online_l = 0, 0, 0, 0

        for m in matches:
            winner = m.get("winner", {})
            won = bool(winner and winner.get("id") == team_id)
            tourn = m.get("tournament") or {}
            tier = (tourn.get("tier") or "").lower()
            tourn_type = (tourn.get("type") or "").lower()

            # Tier record
            if tier:
                key = f"tier_{tier}"
                if key not in tier_records:
                    tier_records[key] = {"w": 0, "l": 0}
                if won:
                    tier_records[key]["w"] += 1
                else:
                    tier_records[key]["l"] += 1

            # LAN/online record
            if tourn_type == "offline":
                if won:
                    lan_w += 1
                else:
                    lan_l += 1
            elif tourn_type == "online":
                if won:
                    online_w += 1
                else:
                    online_l += 1

        for tier_key, record in tier_records.items():
            result[f"{tier_key}_record"] = record
        if lan_w + lan_l > 0:
            result["lan_record"] = {"w": lan_w, "l": lan_l}
        if online_w + online_l > 0:
            result["online_record"] = {"w": online_w, "l": online_l}

        # --- Per-match enrichment: tier, LAN, game duration ---
        for rm, m in zip(result.get("recent_matches", []), matches):
            tourn = m.get("tournament") or {}
            rm["tier"] = (tourn.get("tier") or "").lower() or None
            rm["is_lan"] = (tourn.get("type") or "").lower() == "offline"
            rm["prizepool"] = tourn.get("prizepool") or None

            # Average game duration from games[].length
            games = m.get("games") or []
            durations = [g.get("length", 0) for g in games if g.get("length")]
            if durations:
                avg_sec = sum(durations) / len(durations)
                rm["avg_game_length_min"] = round(avg_sec / 60)
            else:
                rm["avg_game_length_min"] = None

            # Game-level score detail (which team won each game)
            game_wins_team = sum(
                1 for g in games
                if g.get("winner", {}).get("id") == team_id
            )
            game_wins_opp = len([g for g in games if g.get("status") == "finished"]) - game_wins_team
            if game_wins_team + game_wins_opp > 0:
                rm["game_detail"] = f"{game_wins_team}-{max(0, game_wins_opp)}"

    def get_team_recent_results(
        self, game_slug: str, team_name: str, limit: int = 20
    ) -> Optional[Dict]:
        """Fetch a team's recent match results from PandaScore.

        Returns dict with: team_name, wins, losses, win_rate, recent_matches
        + enriched fields: roster, location, tier records, LAN/online records, game duration
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
            {"filter[opponent_id]": team_id,
             "per_page": limit, "sort": "-scheduled_at"},
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
        result = {
            "team_name": official_name,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total, 2) if total > 0 else 0.0,
            "recent_matches": recent[:10],  # Last 10 for context
        }

        # Enrichment wrapper — on failure, returns base result unchanged
        try:
            self._enrich_team_data(result, team, matches, team_id)
        except Exception as e:
            logger.warning("Team enrichment failed (graceful skip): %s", e)

        return result

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

        # Fetch upcoming match metadata (tier, detailed_stats, scheduled_at)
        upcoming = self._get_upcoming_match(game_slug, team_a_name, team_b_name)

        # Guard: skip matches that started too long ago (likely finished)
        # PandaScore may still report "running" hours after a match ends
        _MAX_MATCH_HOURS = 4  # BO5 can go ~4h max; anything beyond = stale
        if upcoming:
            _sched = upcoming.get("scheduled_at") or ""
            _status = upcoming.get("status", "")
            if _sched and _status == "running":
                try:
                    _start = datetime.fromisoformat(_sched.replace("Z", "+00:00"))
                    _elapsed_h = (datetime.now(timezone.utc) - _start).total_seconds() / 3600
                    if _elapsed_h > _MAX_MATCH_HOURS:
                        logger.warning(
                            "SKIP stale esports match: %s vs %s started %.1fh ago (max %dh)",
                            team_a_name, team_b_name, _elapsed_h, _MAX_MATCH_HOURS,
                        )
                        return None
                except (ValueError, TypeError):
                    pass

        team_a = self.get_team_recent_results(game_slug, team_a_name)
        team_b = self.get_team_recent_results(game_slug, team_b_name)

        if not team_a and not team_b:
            return None

        parts = [f"=== ESPORTS MATCH DATA (PandaScore) ==="]

        # --- Tournament block ---
        if upcoming:
            self._build_tournament_block(parts, upcoming)

        # --- Team blocks ---
        for label, stats in [("TEAM A", team_a), ("TEAM B", team_b)]:
            self._build_team_block(parts, label, stats)

        # --- H2H block ---
        self._build_h2h_block(parts, team_a, team_b)

        # --- Prompt guidance ---
        parts.append(
            "\nUse this data to inform your probability estimate. "
            "Weight recent form, tier performance, and LAN/online split. "
            "Roster changes are a strong signal — new players = unstable form."
        )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Context string builders (called by get_match_context)
    # ------------------------------------------------------------------

    def _build_tournament_block(self, parts: List[str], upcoming: Dict) -> None:
        """Append tournament metadata to context parts."""
        tourn = upcoming.get("tournament") or {}
        tier = (tourn.get("tier") or "").upper()
        tourn_name = tourn.get("name", "")
        league_name = upcoming.get("league", {}).get("name", "")
        has_stats = upcoming.get("detailed_stats", False)
        scheduled = (upcoming.get("scheduled_at") or "")[:16]
        status = upcoming.get("status", "")
        match_format = upcoming.get("match_type", "")
        num_games = upcoming.get("number_of_games", 0)

        meta_line = f"Tournament: {league_name} - {tourn_name}"
        if tier:
            meta_line += f" (Tier {tier})"
        parts.append(meta_line)

        # Enriched: prizepool, LAN/online, country
        prizepool = tourn.get("prizepool")
        tourn_type = (tourn.get("type") or "").lower()
        country = tourn.get("country")
        enriched_parts = []
        if tourn_type:
            enriched_parts.append(f"LAN/Online: {'LAN' if tourn_type == 'offline' else 'Online'}")
        if prizepool:
            enriched_parts.append(f"Prizepool: {prizepool}")
        if country:
            enriched_parts.append(f"Country: {country}")
        if enriched_parts:
            parts.append("  " + " | ".join(enriched_parts))

        if match_format and num_games:
            parts.append(f"Format: {match_format} {num_games}")
        if scheduled:
            parts.append(f"Scheduled: {scheduled} UTC")
        if status and status != "not_started":
            parts.append(f"Status: {status}")
        if has_stats:
            parts.append("Detailed stats: available")

    def _build_team_block(self, parts: List[str], label: str, stats: Optional[Dict]) -> None:
        """Append team data block to context parts."""
        if not stats:
            parts.append(f"\n{label}: No data available")
            return

        total = stats["wins"] + stats["losses"]
        header = (
            f"\n{label}: {stats['team_name']}"
        )
        # Enriched: location
        location = stats.get("location")
        if location:
            header += f" ({location})"
        parts.append(header)

        parts.append(
            f"  Record (last {total} matches): {stats['wins']}W - {stats['losses']}L "
            f"(win rate: {stats['win_rate']:.0%})"
        )

        # Enriched: tier records
        for tier_key in ("tier_s", "tier_a", "tier_b"):
            rec = stats.get(f"{tier_key}_record")
            if rec and (rec["w"] + rec["l"]) > 0:
                parts.append(f"  {tier_key.replace('_', ' ').title()} record: {rec['w']}W-{rec['l']}L")

        # Enriched: LAN/online records
        lan = stats.get("lan_record")
        online = stats.get("online_record")
        if lan:
            parts.append(f"  LAN record: {lan['w']}W-{lan['l']}L")
        if online:
            parts.append(f"  Online record: {online['w']}W-{online['l']}L")

        # Enriched: roster
        roster = stats.get("roster")
        if roster:
            parts.append(f"  Roster: {', '.join(roster)}")

        # Enriched: roster change alert
        rc = stats.get("roster_change")
        if rc:
            if rc.get("new_players"):
                parts.append(f"  ⚠ NEW PLAYERS: {', '.join(rc['new_players'])} (possible stand-in)")
            if rc.get("departed_players"):
                parts.append(f"  ⚠ DEPARTED: {', '.join(rc['departed_players'])}")

        # Recent matches
        if stats.get("recent_matches"):
            parts.append("  Recent matches:")
            for m in stats["recent_matches"][:5]:
                result_tag = "W" if m["won"] else "L"
                line = f"    [{result_tag}] vs {m['opponent']} {m['score']}"
                # Enriched: tier, LAN tag, duration
                extras = []
                if m.get("tier"):
                    extras.append(f"T-{m['tier'].upper()}")
                if m.get("is_lan"):
                    extras.append("LAN")
                if m.get("avg_game_length_min"):
                    extras.append(f"~{m['avg_game_length_min']}min")
                suffix = f" [{'/'.join(extras)}]" if extras else ""
                line += f" ({m['tournament']}, {m['date']}){suffix}"
                parts.append(line)

    def _build_h2h_block(
        self, parts: List[str], team_a: Optional[Dict], team_b: Optional[Dict],
    ) -> None:
        """Append head-to-head block to context parts."""
        if not team_a or not team_b:
            return

        h2h_a = 0
        h2h_b = 0
        h2h_lan = 0
        h2h_online = 0
        for m in (team_a.get("recent_matches") or []):
            if m["opponent"].lower() == team_b["team_name"].lower():
                if m["won"]:
                    h2h_a += 1
                else:
                    h2h_b += 1
                # Enriched: LAN/online H2H context (only count when explicitly set)
                if "is_lan" in m:
                    if m["is_lan"]:
                        h2h_lan += 1
                    else:
                        h2h_online += 1

        if h2h_a + h2h_b > 0:
            h2h_line = (
                f"\nHEAD-TO-HEAD (recent): "
                f"{team_a['team_name']} {h2h_a} - {h2h_b} {team_b['team_name']}"
            )
            if h2h_lan or h2h_online:
                h2h_line += f" (LAN: {h2h_lan}, Online: {h2h_online})"
            parts.append(h2h_line)

    # ------------------------------------------------------------------
    # Live match state (PandaScore running matches endpoint)
    # ------------------------------------------------------------------

    def _get_live(self, endpoint: str, params: dict = None, cache_ttl: int = 60) -> Optional[list]:
        """GET with short cache TTL for live data (default 60s)."""
        if not self.available:
            return None
        cache_key = f"live:{endpoint}:{params}"
        cached = self._cache.get(cache_key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < cache_ttl:
                return data

        self._rate_limit()
        headers = {"Authorization": f"Bearer {self.api_key}"}

        last_err = None
        for attempt in range(2):  # 1 try + 1 retry
            try:
                resp = self._session.get(
                    f"{PANDASCORE_BASE}{endpoint}",
                    headers=headers,
                    params=params or {},
                    timeout=5,
                )
                resp.raise_for_status()
                record_call("pandascore")
                data = resp.json()
                self._cache[cache_key] = (data, time.monotonic())
                return data
            except requests.RequestException as e:
                last_err = e
                if attempt == 0:
                    logger.info("PandaScore live retry after error: %s", e)
                    time.sleep(2)
                    continue

        logger.warning("PandaScore live API error (after retry): %s", last_err)
        return None

    def get_running_matches(self, game_slug: str) -> Optional[List[dict]]:
        """Fetch currently running matches for a game.

        Returns list of match dicts with: id, name, status, games (maps),
        opponents, results, scheduled_at, etc.
        """
        return self._get_live(
            f"/{game_slug}/matches/running",
            {"per_page": 50},
            cache_ttl=45,
        )

    def get_live_match_state(
        self, game_slug: str, team_a_name: str, team_b_name: str
    ) -> Optional[Dict]:
        """Get live match state for a specific matchup.

        Returns dict with:
            match_id: int
            status: str ("running", "not_started", "finished")
            map_number: int (current map/game number, 1-indexed)
            total_maps: int (best-of format: 1, 3, or 5)
            map_score: str (e.g. "1-0", "2-1")
            is_break: bool (True if between maps)
            break_type: str ("map_break", "half_time", "")
            current_game_status: str ("running", "finished", "not_started")
            team_a: str (official name)
            team_b: str (official name)
            team_a_score: int (maps won)
            team_b_score: int (maps won)
        """
        matches = self.get_running_matches(game_slug)
        if not matches:
            return None

        # Find the match that contains both teams
        for match in matches:
            opponents = match.get("opponents", [])
            if len(opponents) < 2:
                continue

            opp_names = []
            for opp in opponents:
                opp_team = opp.get("opponent", {})
                opp_names.append({
                    "name": opp_team.get("name", ""),
                    "acronym": (opp_team.get("acronym") or "").lower(),
                    "slug": opp_team.get("slug", "").lower(),
                })

            # Check if both teams match
            a_match = self._name_matches(team_a_name, opp_names)
            b_match = self._name_matches(team_b_name, opp_names)
            if a_match is None or b_match is None or a_match == b_match:
                continue

            # Found our match -- parse state
            return self._parse_match_state(match, opp_names[0]["name"], opp_names[1]["name"])

        return None

    def _name_matches(self, query: str, opp_names: List[dict]) -> Optional[int]:
        """Check if query matches any opponent. Returns index or None."""
        for i, opp in enumerate(opp_names):
            for candidate in [opp.get("name", ""), opp.get("acronym", ""), opp.get("slug", "")]:
                if not candidate:
                    continue
                is_match, score, method = match_team(query, candidate)
                if is_match:
                    return i
        return None

    def _parse_match_state(self, match: dict, team_a: str, team_b: str) -> Dict:
        """Parse PandaScore match data into a structured match state."""
        games = match.get("games", [])
        results = match.get("results", [])
        number_of_games = match.get("number_of_games", 0)
        status = match.get("status", "unknown")

        # Map scores from results
        team_a_score = 0
        team_b_score = 0
        if len(results) >= 2:
            team_a_score = results[0].get("score", 0)
            team_b_score = results[1].get("score", 0)

        # Determine current map/game state
        current_map = 0
        current_game_status = ""
        is_break = False

        if games:
            # Sort by position to get them in order
            sorted_games = sorted(games, key=lambda g: g.get("position", 0))

            # Find the current game (running or last finished)
            running_game = None
            last_finished_idx = -1
            for i, g in enumerate(sorted_games):
                g_status = g.get("status", "")
                if g_status == "running":
                    running_game = g
                    current_map = i + 1
                    current_game_status = "running"
                    break
                elif g_status == "finished":
                    last_finished_idx = i

            if running_game is None:
                if last_finished_idx >= 0:
                    # No running game, last one finished
                    maps_played = last_finished_idx + 1
                    total_needed = (number_of_games // 2) + 1  # maps needed to win
                    if team_a_score >= total_needed or team_b_score >= total_needed:
                        # Match is over
                        current_map = maps_played
                        current_game_status = "finished"
                    else:
                        # Between maps -- this is a break!
                        current_map = maps_played + 1
                        current_game_status = "not_started"
                        is_break = True
                else:
                    current_map = 1
                    current_game_status = "not_started"
        else:
            # No games data -- infer from results
            current_map = team_a_score + team_b_score + 1

        map_score = f"{team_a_score}-{team_b_score}"
        break_type = "map_break" if is_break else ""

        state = {
            "match_id": match.get("id"),
            "status": status,
            "map_number": current_map,
            "total_maps": number_of_games or 1,
            "map_score": map_score,
            "is_break": is_break,
            "break_type": break_type,
            "current_game_status": current_game_status,
            "team_a": team_a,
            "team_b": team_b,
            "team_a_score": team_a_score,
            "team_b_score": team_b_score,
        }

        logger.info("Live match state: %s vs %s | Map %d/%d | Score %s | break=%s",
                     team_a, team_b, current_map, number_of_games or 1,
                     map_score, is_break)

        return state
