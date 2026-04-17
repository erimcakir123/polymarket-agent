"""Score enricher — canlı skor verisiyle pozisyon score_info üretir (SPEC-004).

Light cycle içinde periyodik çağrılır (poll_interval_sec, default 120 sn).
Sadece maç penceresindeki pozisyonlar için API çağrısı yapar.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from src.config.sport_rules import _normalize
from src.infrastructure.apis.score_client import MatchScore, fetch_scores
from src.models.position import Position
from src.strategy.enrichment.question_parser import extract_teams

logger = logging.getLogger(__name__)

_HOCKEY_TAG = "nhl"


def _is_within_match_window(pos: Position, window_hours: float) -> bool:
    """Pozisyon maç penceresi içinde mi? (match_start ± window saat)."""
    if not pos.match_start_iso:
        return False
    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    now = datetime.now(timezone.utc)
    diff_hours = abs((now - start).total_seconds()) / 3600.0
    return diff_hours <= window_hours


def _team_match(pos_team: str, api_team: str) -> bool:
    """Polymarket team name ile Odds API team name fuzzy eşleşmesi."""
    if not pos_team or not api_team:
        return False
    p = pos_team.lower().strip()
    a = api_team.lower().strip()
    if p == a:
        return True
    # Substring match: "Rangers" in "New York Rangers"
    if p in a or a in p:
        return True
    # Son kelime eşleşmesi: "New York Rangers" → "Rangers"
    p_last = p.rsplit(maxsplit=1)[-1] if " " in p else p
    a_last = a.rsplit(maxsplit=1)[-1] if " " in a else a
    return p_last == a_last and len(p_last) >= 3


def _find_match(pos: Position, scores: list[MatchScore]) -> MatchScore | None:
    """Pozisyonu skor listesiyle eşleştir (team name matching)."""
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None
    for ms in scores:
        home_a = _team_match(team_a, ms.home_team)
        home_b = _team_match(team_b or "", ms.home_team) if team_b else False
        away_a = _team_match(team_a, ms.away_team)
        away_b = _team_match(team_b or "", ms.away_team) if team_b else False
        if (home_a and away_b) or (home_b and away_a) or (home_a or away_a):
            return ms
    return None


def _build_score_info(pos: Position, ms: MatchScore) -> dict:
    """Eşleşen skor verisinden score_info dict oluştur (direction-aware)."""
    if ms.home_score is None or ms.away_score is None:
        return {"available": False}

    team_a, _ = extract_teams(pos.question)
    # team_a = question'daki ilk takım (YES side)
    # Eşleştirme: team_a home mu away mu?
    a_is_home = _team_match(team_a or "", ms.home_team)

    if a_is_home:
        yes_score, no_score = ms.home_score, ms.away_score
    else:
        yes_score, no_score = ms.away_score, ms.home_score

    # Direction-aware: BUY_YES → YES side bizim; BUY_NO → NO side bizim
    if pos.direction == "BUY_YES":
        our_score, opp_score = yes_score, no_score
    else:
        our_score, opp_score = no_score, yes_score

    deficit = opp_score - our_score  # pozitif = gerideyiz
    return {
        "available": True,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": ms.period,
        "map_diff": -deficit,  # graduated_sl uyumu: pozitif = öndeyiz
    }


class ScoreEnricher:
    """Periyodik skor çekme + pozisyon eşleştirme."""

    def __init__(self, odds_client, poll_interval_sec: int = 120, match_window_hours: float = 4.0) -> None:
        self._client = odds_client
        self._poll_sec = poll_interval_sec
        self._window_hours = match_window_hours
        self._last_poll_ts: float = 0.0
        self._cached_scores: dict[str, list[MatchScore]] = {}  # sport_key → scores

    def get_scores_if_due(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Zamanlama uygunsa skor çek, pozisyonlarla eşleştir.

        Returns:
            {condition_id: score_info} dict. Eşleşme yoksa cid dahil olmaz.
        """
        now = time.monotonic()
        if (now - self._last_poll_ts) < self._poll_sec:
            return self._match_cached(positions)

        self._last_poll_ts = now
        self._refresh_scores(positions)
        return self._match_cached(positions)

    def _refresh_scores(self, positions: dict[str, Position]) -> None:
        """Maç penceresindeki pozisyonlar için sport_key bazında skor çek."""
        sport_keys: set[str] = set()
        for pos in positions.values():
            if not _is_within_match_window(pos, self._window_hours):
                continue
            tag = _normalize(pos.sport_tag)
            if tag:
                sport_keys.add(self._sport_tag_to_api_key(pos.sport_tag))

        self._cached_scores.clear()
        for key in sport_keys:
            scores = fetch_scores(self._client, key)
            if scores:
                self._cached_scores[key] = scores
                logger.info("Score fetch: %s → %d events", key, len(scores))

    def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Cached skor verisiyle pozisyonları eşleştir."""
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            api_key = self._sport_tag_to_api_key(pos.sport_tag)
            scores = self._cached_scores.get(api_key, [])
            if not scores:
                continue
            ms = _find_match(pos, scores)
            if ms:
                result[cid] = _build_score_info(pos, ms)
        return result

    @staticmethod
    def _sport_tag_to_api_key(sport_tag: str) -> str:
        """sport_tag → Odds API sport_key dönüştürme."""
        tag = (sport_tag or "").lower().strip()
        mapping = {
            "nhl": "icehockey_nhl",
            "ahl": "icehockey_ahl",
            "hockey": "icehockey_nhl",
            "liiga": "icehockey_liiga",
            "mestis": "icehockey_mestis",
            "shl": "icehockey_sweden_hockey_league",
        }
        return mapping.get(tag, f"icehockey_{tag}")
