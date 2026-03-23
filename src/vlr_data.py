"""VLR.gg scraper client for Valorant tier-2/3 match data.
Fallback when PandaScore has no data for a Valorant market.
Uses vlrdevapi package (pip install vlrdevapi).
"""
from __future__ import annotations
import logging
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from src.api_usage import record_call

logger = logging.getLogger(__name__)

try:
    import vlrdevapi
    VLR_AVAILABLE = True
except ImportError:
    VLR_AVAILABLE = False
    logger.info("vlrdevapi not installed — VLR fallback disabled")


class VLRDataClient:
    """Fetches Valorant team stats from VLR.gg via vlrdevapi scraper."""

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[object, float]] = {}
        self._cache_ttl = 1800  # 30 min
        self._last_call: float = 0.0
        self._team_id_cache: Dict[str, Optional[int]] = {}  # name -> vlr team id

    @property
    def available(self) -> bool:
        return VLR_AVAILABLE

    def _rate_limit(self) -> None:
        """VLR.gg scraper — be polite, 1 req/3s."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)
        self._last_call = time.monotonic()

    def _cached(self, key: str) -> Optional[object]:
        cached = self._cache.get(key)
        if cached:
            data, ts = cached
            if time.monotonic() - ts < self._cache_ttl:
                return data
        return None

    def _extract_team_names(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract team names from 'Valorant: Team A vs Team B (BO3) - Event' format."""
        q = question.strip()
        for prefix in ["Valorant:", "VALORANT:"]:
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

    def _find_team_id(self, team_name: str) -> Optional[int]:
        """Search VLR.gg for a team and return its ID."""
        if team_name in self._team_id_cache:
            return self._team_id_cache[team_name]

        try:
            self._rate_limit()
            record_call("vlr")
            results = vlrdevapi.search.teams(team_name)
            if not results:
                self._team_id_cache[team_name] = None
                return None

            # Fuzzy match
            name_lower = team_name.lower().strip()
            best_match = None
            best_score = 0.0
            for t in results:
                t_name = (t.name or "").lower()
                if name_lower == t_name:
                    best_match = t
                    break
                score = SequenceMatcher(None, name_lower, t_name).ratio()
                if score > best_score:
                    best_score = score
                    best_match = t

            if best_match and (best_score >= 0.5 or name_lower == (best_match.name or "").lower()):
                tid = best_match.id if hasattr(best_match, 'id') else best_match.team_id
                self._team_id_cache[team_name] = tid
                return tid
        except Exception as e:
            logger.warning("VLR team search error for '%s': %s", team_name, e)

        self._team_id_cache[team_name] = None
        return None

    def get_team_recent_results(self, team_name: str) -> Optional[Dict]:
        """Fetch team's recent completed matches from VLR.gg."""
        cache_key = f"vlr_team:{team_name}"
        cached = self._cached(cache_key)
        if cached:
            return cached

        team_id = self._find_team_id(team_name)
        if not team_id:
            return None

        try:
            self._rate_limit()
            record_call("vlr")
            completed = vlrdevapi.teams.completed_matches(team_id)
            if not completed:
                return None

            wins = 0
            losses = 0
            recent = []
            for m in completed[:15]:
                t1 = m.team1 if hasattr(m, 'team1') else None
                t2 = m.team2 if hasattr(m, 'team2') else None
                if not t1 or not t2:
                    continue

                is_team1 = (t1.id == team_id) if hasattr(t1, 'id') else False
                my_score = t1.score if is_team1 else (t2.score if t2 else None)
                opp_score = t2.score if is_team1 else (t1.score if t1 else None)
                opp_name = (t2.name if is_team1 else t1.name) or "Unknown"

                won = False
                if my_score is not None and opp_score is not None:
                    try:
                        won = int(my_score) > int(opp_score)
                    except (ValueError, TypeError):
                        pass

                if won:
                    wins += 1
                else:
                    losses += 1

                score_str = f"{my_score}-{opp_score}" if my_score is not None else ""
                event_name = ""
                if hasattr(m, 'event'):
                    event_name = m.event if isinstance(m.event, str) else getattr(m.event, 'name', str(m.event))

                recent.append({
                    "opponent": opp_name,
                    "won": won,
                    "score": score_str,
                    "tournament": event_name,
                    "date": getattr(m, 'date', '') or "",
                })

            total = wins + losses
            if total == 0:
                return None

            result = {
                "team_name": team_name,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / total, 2) if total > 0 else 0.0,
                "recent_matches": recent[:10],
            }
            self._cache[cache_key] = (result, time.monotonic())
            return result

        except Exception as e:
            logger.warning("VLR completed matches error for team %s: %s", team_id, e)
            return None

    def get_match_context(self, question: str, tags: List[str]) -> Optional[str]:
        """Build context string for AI. Only for Valorant markets."""
        if not self.available:
            return None

        # Check if this is a Valorant market
        q_lower = question.lower()
        tags_lower = [t.lower() for t in tags]
        is_valorant = "valorant" in q_lower or any("valorant" in t for t in tags_lower)
        if not is_valorant:
            return None

        team_a_name, team_b_name = self._extract_team_names(question)
        if not team_a_name or not team_b_name:
            return None

        logger.info("VLR fallback: fetching %s vs %s", team_a_name, team_b_name)

        team_a = self.get_team_recent_results(team_a_name)
        team_b = self.get_team_recent_results(team_b_name)

        if not team_a and not team_b:
            return None

        parts = ["=== VALORANT MATCH DATA (VLR.gg) ==="]

        for label, stats in [("TEAM A", team_a), ("TEAM B", team_b)]:
            if not stats:
                parts.append(f"\n{label}: No data available")
                continue
            total = stats["wins"] + stats["losses"]
            parts.append(
                f"\n{label}: {stats['team_name']}\n"
                f"  Record (last {total} matches): {stats['wins']}W - {stats['losses']}L "
                f"(win rate: {stats['win_rate']:.0%})"
            )
            if stats["recent_matches"]:
                parts.append("  Recent matches:")
                for m in stats["recent_matches"][:5]:
                    result = "W" if m["won"] else "L"
                    parts.append(
                        f"    [{result}] vs {m['opponent']} {m['score']} "
                        f"({m['tournament']}, {m['date']})"
                    )

        # Head-to-head
        if team_a and team_b:
            h2h_a, h2h_b = 0, 0
            for m in (team_a.get("recent_matches") or []):
                if team_b and m["opponent"].lower() == team_b["team_name"].lower():
                    h2h_a += 1 if m["won"] else 0
                    h2h_b += 0 if m["won"] else 1
            if h2h_a + h2h_b > 0:
                parts.append(
                    f"\nHEAD-TO-HEAD (recent): "
                    f"{team_a['team_name']} {h2h_a} - {h2h_b} {team_b['team_name']}"
                )

        parts.append("\nSource: VLR.gg (covers tier-2/3 Valorant tournaments)")
        return "\n".join(parts)
