"""ESPN enrichment — additional endpoints for richer AI context.

Provides: win probability, standings, athlete overview, splits,
rankings, CDN scoreboard, H2H stats. All endpoints are free (no API key).

Receives SportsDataClient via DI for detect_sport() reuse.
Does NOT import anything from src/ at module level.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

import requests

if TYPE_CHECKING:
    from src.sports_data import SportsDataClient

logger = logging.getLogger(__name__)

_SITE_API = "https://site.api.espn.com/apis/site/v2/sports"
_CORE_API = "https://sports.core.api.espn.com/v2/sports"
_WEB_API = "https://site.web.api.espn.com/apis/common/v3/sports"
_CDN_API = "https://cdn.espn.com/core"
_TIMEOUT = 8


class ESPNEnrichment:
    """Additional ESPN data sources for AI context enrichment."""

    def __init__(self, sports_client: "SportsDataClient") -> None:
        self._client = sports_client
        self._cache: dict[str, dict] = {}
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "PolymarketBot/1.0"

    # ── Cache helpers ──────────────────────────────────────────

    def _get_cached(self, key: str, ttl: int = 300) -> Optional[str]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return entry["data"]
        return None

    def _set_cache(self, key: str, data: str) -> None:
        self._cache[key] = {"data": data, "ts": time.time()}

    # ── Public entry point ─────────────────────────────────────

    def enrich(self, question: str, slug: str, tags: list[str]) -> Optional[str]:
        """Fetch all applicable enrichment data and return formatted context string."""
        sport_league = self._client.detect_sport(question, slug, tags)
        if not sport_league:
            return None
        sport, league = sport_league

        parts: list[str] = []

        # Team sports: standings + win probability
        if sport not in _ATHLETE_SPORTS:
            standing = self.get_league_standing(sport, league, question, slug)
            if standing:
                parts.append(standing)
            win_prob = self.get_win_probability(sport, league, question, slug)
            if win_prob:
                parts.append(win_prob)
        else:
            # Athlete sports: overview + splits + rankings + H2H
            overview = self.get_athlete_overview(sport, league, question, slug)
            if overview:
                parts.append(overview)
            splits = self.get_athlete_splits(sport, league, question, slug)
            if splits:
                parts.append(splits)
            rankings = self.get_rankings(sport, league)
            if rankings:
                parts.append(rankings)
            h2h = self.get_h2h(sport, league, question, slug)
            if h2h:
                parts.append(h2h)

        # CDN scoreboard (all sports)
        cdn = self.get_cdn_scoreboard(sport, league)
        if cdn:
            parts.append(cdn)

        if not parts:
            return None
        return "\n=== ESPN ENRICHMENT ===\n" + "\n".join(parts)

    # ── Endpoint methods ───────────────────────────────────────

    def get_league_standing(self, sport: str, league: str,
                           question: str, slug: str) -> Optional[str]:
        """Fetch league standings and find team's position."""
        cache_key = f"standing:{sport}:{league}"
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return cached

        try:
            url = f"{_SITE_API}/{sport}/{league}/standings"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            entries = []
            rank_counter = 0
            for group in data.get("children", []):
                for standing in group.get("standings", {}).get("entries", []):
                    rank_counter += 1
                    team = standing.get("team", {})
                    stats = {s["abbreviation"]: s["value"]
                             for s in standing.get("stats", [])
                             if "abbreviation" in s and "value" in s}
                    entries.append({
                        "name": team.get("displayName", ""),
                        "abbrev": team.get("abbreviation", ""),
                        "rank": rank_counter,  # Position in standings array
                        "wins": int(stats.get("W", 0)),
                        "losses": int(stats.get("L", 0)),
                        "streak": stats.get("STRK", ""),
                    })
            if not entries:
                return None
            # Find relevant teams from question/slug
            text = self._format_standings(entries, question, slug)
            if text:
                self._set_cache(cache_key, text)
            return text
        except Exception as exc:
            logger.warning("ESPN standings error: %s", exc)
            return None

    def get_win_probability(self, sport: str, league: str,
                            question: str, slug: str) -> Optional[str]:
        """Fetch sportsbook win probability for a specific event."""
        try:
            # Find event via scoreboard
            event_id, comp_id = self._find_event_ids(sport, league, question, slug)
            if not event_id:
                return None

            url = (f"{_CORE_API}/{sport}/leagues/{league}/events/{event_id}"
                   f"/competitions/{comp_id}/odds?limit=10")
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return None

            probs = []
            for item in items:
                provider = item.get("provider", {}).get("name", "Unknown")
                home = item.get("homeTeamOdds", {})
                away = item.get("awayTeamOdds", {})
                h_ml = home.get("moneyLine")
                a_ml = away.get("moneyLine")
                if h_ml is not None and a_ml is not None:
                    probs.append(f"  {provider}: Home {h_ml:+d} / Away {a_ml:+d}")

            if not probs:
                return None
            return "Win Probability (sportsbooks):\n" + "\n".join(probs[:5])
        except Exception as exc:
            logger.warning("ESPN win probability error: %s", exc)
            return None

    def get_athlete_overview(self, sport: str, league: str,
                            question: str, slug: str) -> Optional[str]:
        """Fetch athlete overview (ranking, injury, news)."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids:
                return None

            parts = []
            for aid, name in athlete_ids[:2]:
                url = f"{_WEB_API}/{sport}/{league}/athletes/{aid}/overview"
                resp = self._session.get(url, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                athlete = data.get("athlete", {})
                rank = athlete.get("rank", {}).get("current", {}).get("rank", "N/A")
                injuries = athlete.get("injuries", [])
                injury_status = injuries[0].get("status", "Healthy") if injuries else "Healthy"
                parts.append(f"  {name}: Rank #{rank}, Status: {injury_status}")

            if not parts:
                return None
            return "Athlete Overview:\n" + "\n".join(parts)
        except Exception as exc:
            logger.warning("ESPN athlete overview error: %s", exc)
            return None

    def get_athlete_splits(self, sport: str, league: str,
                           question: str, slug: str) -> Optional[str]:
        """Fetch athlete statistical splits (home/away/surface)."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids:
                return None

            parts = []
            for aid, name in athlete_ids[:2]:
                url = f"{_SITE_API}/{sport}/{league}/athletes/{aid}/splits"
                resp = self._session.get(url, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                categories = data.get("splitCategories", [])
                for cat in categories[:2]:
                    cat_name = cat.get("displayName", "")
                    for split in cat.get("splits", [])[:3]:
                        split_name = split.get("displayName", "")
                        stats_list = split.get("stats", [])
                        record = f"{stats_list[0]}-{stats_list[1]}" if len(stats_list) >= 2 else "N/A"
                        parts.append(f"  {name} ({cat_name}/{split_name}): {record}")

            if not parts:
                return None
            return "Athlete Splits:\n" + "\n".join(parts[:8])
        except Exception as exc:
            logger.warning("ESPN athlete splits error: %s", exc)
            return None

    def get_rankings(self, sport: str, league: str) -> Optional[str]:
        """Fetch current rankings (ATP/WTA/golf)."""
        cache_key = f"rankings:{sport}:{league}"
        cached = self._get_cached(cache_key, ttl=300)
        if cached:
            return cached

        try:
            url = f"{_CORE_API}/{sport}/leagues/{league}/rankings"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            rankings = data.get("rankings", [])
            if not rankings:
                return None

            entries = rankings[0].get("ranks", [])[:20]
            lines = []
            for r in entries:
                athlete = r.get("athlete", {})
                name = athlete.get("displayName", "Unknown")
                rank = r.get("current", "?")
                points = r.get("points", "")
                lines.append(f"  #{rank} {name}" + (f" ({points}pts)" if points else ""))

            if not lines:
                return None
            text = f"Rankings ({league.upper()}):\n" + "\n".join(lines[:10])
            self._set_cache(cache_key, text)
            return text
        except Exception as exc:
            logger.warning("ESPN rankings error: %s", exc)
            return None

    def get_cdn_scoreboard(self, sport: str, league: str) -> Optional[str]:
        """Fetch lightweight CDN scoreboard for live scores."""
        try:
            url = f"{_CDN_API}/{sport}/{league}/scoreboard?xhr=1"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            events = data.get("content", {}).get("sbData", {}).get("events", [])
            if not events:
                return None

            lines = []
            for ev in events[:5]:
                comps = ev.get("competitions", [{}])
                if not comps:
                    continue
                teams = comps[0].get("competitors", [])
                if len(teams) >= 2:
                    t1 = f"{teams[0].get('team', {}).get('abbreviation', '?')} {teams[0].get('score', '?')}"
                    t2 = f"{teams[1].get('team', {}).get('abbreviation', '?')} {teams[1].get('score', '?')}"
                    status = comps[0].get("status", {}).get("type", {}).get("shortDetail", "")
                    lines.append(f"  {t1} vs {t2} ({status})")

            if not lines:
                return None
            return "Live Scoreboard:\n" + "\n".join(lines)
        except Exception as exc:
            logger.warning("ESPN CDN scoreboard error: %s", exc)
            return None

    def get_h2h(self, sport: str, league: str,
                question: str, slug: str) -> Optional[str]:
        """Fetch head-to-head stats between two athletes."""
        try:
            athlete_ids = self._find_athlete_ids(sport, league, question, slug)
            if not athlete_ids or len(athlete_ids) < 2:
                return None

            id_a, name_a = athlete_ids[0]
            id_b, name_b = athlete_ids[1]
            url = f"{_SITE_API}/{sport}/{league}/athletes/{id_a}/vsathlete/{id_b}"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return None
            data = resp.json()
            vs = data.get("vsAthlete", {})
            record = vs.get("record", {})
            wins_a = record.get("wins", 0)
            wins_b = record.get("losses", 0)

            events = vs.get("events", [])
            recent = []
            for ev in events[:5]:
                winner = ev.get("winner", {}).get("displayName", "?")
                date = ev.get("date", "")[:10]
                recent.append(f"    {date}: {winner}")

            result = f"H2H: {name_a} {wins_a}-{wins_b} {name_b}"
            if recent:
                result += "\n  Recent:\n" + "\n".join(recent)
            return result
        except Exception as exc:
            logger.warning("ESPN H2H error: %s", exc)
            return None

    # ── Internal helpers ───────────────────────────────────────

    def _find_event_ids(self, sport: str, league: str,
                        question: str, slug: str) -> tuple[str, str]:
        """Find ESPN event_id and competition_id from scoreboard."""
        try:
            url = f"{_SITE_API}/{sport}/{league}/scoreboard"
            resp = self._session.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return "", ""
            data = resp.json()
            events = data.get("events", [])
            q_lower = question.lower()
            for ev in events:
                ev_name = ev.get("name", "").lower()
                if any(word in ev_name for word in q_lower.split()[:3]):
                    comps = ev.get("competitions", [])
                    if comps:
                        return str(ev.get("id", "")), str(comps[0].get("id", ""))
        except Exception:
            pass
        return "", ""

    def _find_athlete_ids(self, sport: str, league: str,
                          question: str, slug: str) -> list[tuple[str, str]]:
        """Find athlete IDs from question text via ESPN search."""
        results = []
        # Extract potential names from slug: "atp-bolt-wu" → ["bolt", "wu"]
        parts = slug.replace("-", " ").split()
        # Skip sport prefix
        name_parts = [p for p in parts if len(p) > 2 and not p.isdigit()
                      and p not in ("atp", "wta", "ufc", "pga", "lpga")]

        for name in name_parts[:4]:
            try:
                url = f"https://site.web.api.espn.com/apis/common/v3/search"
                resp = self._session.get(url, params={
                    "query": name, "limit": 3, "type": "player",
                }, timeout=_TIMEOUT)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data.get("items", []) or data.get("results", [])
                for item in items:
                    entries = item.get("entries", []) if isinstance(item, dict) else []
                    for entry in entries:
                        aid = entry.get("id", "")
                        display = entry.get("displayName", "")
                        if aid and name.lower() in display.lower():
                            results.append((str(aid), display))
                            break
            except Exception:
                continue

        return results[:2]

    def _format_standing(self, standing: dict, team_name: str) -> str:
        """Format a single team's standing."""
        return (f"  {team_name}: #{standing.get('rank', '?')} "
                f"({standing.get('wins', 0)}W-{standing.get('losses', 0)}L) "
                f"Streak: {standing.get('streak', 'N/A')}")

    def _format_standings(self, entries: list[dict],
                          question: str, slug: str) -> Optional[str]:
        """Find relevant teams and format their standings."""
        q_lower = question.lower()
        slug_parts = set(slug.lower().replace("-", " ").split())
        relevant = []
        for e in entries:
            name_lower = e["name"].lower()
            abbrev_lower = e["abbrev"].lower()
            if (any(word in name_lower for word in slug_parts if len(word) > 2) or
                    abbrev_lower in slug_parts or
                    any(word in q_lower for word in name_lower.split())):
                relevant.append(self._format_standing(e, e["name"]))
        if not relevant:
            return None
        return "League Standings:\n" + "\n".join(relevant[:2])


# Sports where competitors are individual athletes
_ATHLETE_SPORTS = frozenset({"tennis", "mma", "golf"})
