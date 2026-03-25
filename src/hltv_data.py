"""HLTV scraper client for CS2 tier-2/3 match data.
Fallback when PandaScore has no data for a CS2 market.
Uses hltv-async-api package (pip install hltv-async-api).

NOTE: HLTV has Cloudflare protection — may need proxy config.
Set HLTV_PROXY env var if needed (e.g., http://user:pass@proxy:port).
"""
from __future__ import annotations
import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from src.api_usage import record_call

logger = logging.getLogger(__name__)

try:
    from hltv_async_api import Hltv
    HLTV_AVAILABLE = True
except ImportError:
    HLTV_AVAILABLE = False
    logger.info("hltv-async-api not installed — HLTV fallback disabled")


class HLTVDataClient:
    """Fetches CS2 team stats from HLTV.org via hltv-async-api scraper."""

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 1800  # 30 min
        self._hltv: Optional[object] = None
        self._proxy = os.getenv("HLTV_PROXY", "")
        self._init_failed = False

    @property
    def available(self) -> bool:
        return HLTV_AVAILABLE and not self._init_failed

    def _cached(self, key: str) -> Optional[object]:
        cached = self._cache.get(key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data
        return None

    def _get_hltv(self) -> object:
        if self._hltv is None:
            kwargs = {"min_delay": 3, "max_delay": 8}
            if self._proxy:
                kwargs["proxy"] = self._proxy
            self._hltv = Hltv(**kwargs)
        return self._hltv

    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def _extract_team_names(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from 'Counter-Strike: Team A vs Team B (BO3) - Event' format."""
        q = question.strip()
        for prefix in ["Counter-Strike:", "CS2:", "CS:GO:"]:
            if q.startswith(prefix):
                q = q[len(prefix):].strip()

        for sep in [" vs. ", " vs ", " versus "]:
            if sep in q.lower():
                idx = q.lower().index(sep)
                team_a = q[:idx].strip()
                team_b = q[idx + len(sep):].strip()
                if "(" in team_a:
                    team_a = team_a[:team_a.index("(")].strip()
                if "(" in team_b:
                    team_b = team_b[:team_b.index("(")].strip()
                if " - " in team_b:
                    team_b = team_b[:team_b.index(" - ")].strip()
                return team_a, team_b
        return None, None

    async def _get_team_info_async(self, team_name: str) -> Optional[Dict]:
        """Search HLTV for team info via recent results (get_team_info needs team_id)."""
        hltv = self._get_hltv()
        try:
            # get_team_info(team_id, title) requires numeric ID we don't have.
            # Instead, fetch recent results and filter for this team.
            results = await hltv.get_results(days=3, min_rating=1, max=30)
            record_call("hltv")
            if not results:
                return None

            # Filter matches involving this team
            team_lower = team_name.lower()
            team_matches = []
            for match in results:
                t1 = (match.get("team1") or "").lower()
                t2 = (match.get("team2") or "").lower()
                if team_lower in t1 or team_lower in t2 or t1 in team_lower or t2 in team_lower:
                    team_matches.append(match)

            if not team_matches:
                return None

            return {
                "team_name": team_name,
                "recent_results": [
                    f"{m.get('team1', '?')} {m.get('score1', '?')}-{m.get('score2', '?')} {m.get('team2', '?')}"
                    for m in team_matches[:5]
                ],
            }
        except Exception as e:
            logger.warning("HLTV team search error for '%s': %s", team_name, e)
            if "403" in str(e) or "Connection failed" in str(e):
                self._init_failed = True
                logger.warning("HLTV blocked by Cloudflare — disabling HLTV fallback")
            return None
        finally:
            try:
                await hltv.close()
                self._hltv = None
            except Exception:
                pass

    def get_team_recent_results(self, team_name: str) -> Optional[Dict]:
        """Fetch team's recent match results from HLTV."""
        cache_key = f"hltv_team:{team_name}"
        cached = self._cached(cache_key)
        if cached:
            return cached

        if self._init_failed:
            return None

        try:
            result = self._run_async(self._get_team_info_async(team_name))
            if result:
                self._cache[cache_key] = (result, time.monotonic())
            return result
        except Exception as e:
            logger.warning("HLTV async error: %s", e)
            return None

    def get_match_context(self, question: str, tags: List[str]) -> Optional[str]:
        """Build context string for AI. Only for CS2 markets."""
        if not self.available:
            return None

        q_lower = question.lower()
        tags_lower = [t.lower() for t in tags]
        is_cs2 = any(kw in q_lower for kw in ["counter-strike", "cs2", "csgo"]) or \
                 any(any(kw in t for kw in ["counter-strike", "cs2", "csgo"]) for t in tags_lower)
        if not is_cs2:
            return None

        team_a_name, team_b_name = self._extract_team_names(question)
        if not team_a_name or not team_b_name:
            return None

        logger.info("HLTV fallback: fetching %s vs %s", team_a_name, team_b_name)

        team_a = self.get_team_recent_results(team_a_name)
        team_b = self.get_team_recent_results(team_b_name)

        if not team_a and not team_b:
            return None

        parts = ["=== CS2 MATCH DATA (HLTV.org) ==="]

        for label, stats in [("TEAM A", team_a), ("TEAM B", team_b)]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue
            # HLTV returns varying formats — adapt
            if isinstance(stats, dict):
                name = stats.get("name") or stats.get("team_name") or team_a_name
                parts.append(f"\n{label}: {name}")
                if "ranking" in stats:
                    parts.append(f"  HLTV Ranking: #{stats['ranking']}")
                if "recent_results" in stats:
                    parts.append("  Recent matches:")
                    for m in stats["recent_results"][:5]:
                        parts.append(f"    {m}")
            else:
                parts.append(f"\n{label}: {stats}")

        parts.append("\nSource: HLTV.org (covers all CS2 tournaments)")
        return "\n".join(parts)
