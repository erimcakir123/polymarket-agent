"""Score enricher — ESPN primary + Odds API fallback (SPEC-005 Task 4).

Light cycle içinde periyodik çağrılır (poll_normal_sec / poll_critical_sec).
Sadece maç penceresindeki pozisyonlar için API çağrısı yapar.

Dispatch table:
- score_source="espn": ESPN primary + Odds API fallback (tennis hariç)
- missing: skip silently
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from datetime import datetime, timezone

from src.config.sport_rules import _normalize, get_sport_rule, is_cricket_sport
from src.domain.models.match_clock import build_match_clock
from src.infrastructure.apis.cricket_client import CricketAPIClient, CricketMatchScore
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import fetch_scores
from src.infrastructure.persistence.archive_logger import (
    ArchiveLogger,
    ArchiveMatchResult,
    ArchiveScoreEvent,
)
from src.models.position import Position
from src.orchestration.score_helpers import (
    build_score_info as _build_score_info,
    find_match_via_pair as _find_match_via_pair,
    is_within_match_window as _is_within_match_window,
    resolve_tennis_league as _resolve_tennis_league,
)

logger = logging.getLogger(__name__)

# Odds API key mapping (fallback için)
_ODDS_API_KEY_MAP: dict[str, str] = {
    "nhl": "icehockey_nhl",
    "ahl": "icehockey_ahl",
    "hockey": "icehockey_nhl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nfl": "americanfootball_nfl",
}


class ScoreEnricher:
    """ESPN primary + Odds API fallback ile periyodik skor çekme ve eşleştirme."""

    def __init__(
        self,
        espn_client=None,
        odds_client=None,
        poll_normal_sec: int = 60,
        poll_critical_sec: int = 30,
        critical_price_threshold: float = 0.35,
        match_window_hours: float = 4.0,
        archive_logger: ArchiveLogger | None = None,
        cricket_client: CricketAPIClient | None = None,
        soccer_discovery=None,
    ) -> None:
        self._espn = espn_client
        self._odds = odds_client
        self._poll_normal_sec = poll_normal_sec
        self._poll_critical_sec = poll_critical_sec
        self._critical_threshold = critical_price_threshold
        self._window_hours = match_window_hours
        self._poll_sec: int = poll_normal_sec
        self._last_poll_ts: float = 0.0
        # sport_tag → list (ESPNMatchScore | MatchScore)
        self._cached_espn: dict[str, list[ESPNMatchScore]] = {}
        self._cached_odds: dict[str, list] = {}
        self._archive_logger = archive_logger
        self._cricket_client = cricket_client
        self._cached_cricket: list[CricketMatchScore] = []
        # PLAN-012: soccer runtime league discovery (optional dep; wired in factory.py)
        self._soccer_discovery = soccer_discovery
        # event_id → last known score string (skor degisikligi tespiti icin — SPEC-009)
        self._prev_score_by_event: dict[str, str] = {}
        # event_id set'i — daha once match_result log'landi mi? Startup'ta
        # archive'dan yuklenir (duplicate engellemesi).
        self._logged_match_event_ids: set[str] = (
            archive_logger.load_logged_match_event_ids()
            if archive_logger is not None else set()
        )

    def get_scores_if_due(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Zamanlama uygunsa skor çek, pozisyonlarla eşleştir.

        Returns:
            {condition_id: score_info} dict. Eşleşme yoksa cid dahil olmaz.
        """
        self._update_poll_interval(positions)
        now = time.monotonic()
        if (now - self._last_poll_ts) < self._poll_sec:
            return self._match_cached(positions)

        self._last_poll_ts = now
        self._refresh_scores(positions)
        return self._match_cached(positions)

    # ── Private ───────────────────────────────────────────────────────────────

    def _update_poll_interval(self, positions: dict[str, Position]) -> None:
        """Kritik fiyat varsa poll_critical_sec, yoksa poll_normal_sec kullan."""
        min_price = min(
            (p.current_price for p in positions.values()),
            default=1.0,
        )
        self._poll_sec = (
            self._poll_critical_sec
            if min_price <= self._critical_threshold
            else self._poll_normal_sec
        )

    def _refresh_scores(self, positions: dict[str, Position]) -> None:
        """Maç penceresindeki pozisyonlar için tüm aktif liglerden skor çek."""
        # 1. Benzersiz (tag, sport, league) kombinasyonlarını topla
        unique_espn: set[tuple[str, str, str]] = set()
        tags_requiring_odds: set[str] = set()

        active_positions = [
            p for p in positions.values()
            if _is_within_match_window(p, self._window_hours)
        ]

        for pos in active_positions:
            tag = _normalize(pos.sport_tag)
            if not tag:
                continue

            score_source = get_sport_rule(tag, "score_source")
            if score_source == "espn":
                espn_sport = get_sport_rule(tag, "espn_sport", "")
                espn_league = get_sport_rule(tag, "espn_league", "")

                if tag == "tennis":
                    espn_league = _resolve_tennis_league(pos.slug)
                elif tag == "soccer":
                    if self._soccer_discovery:
                        espn_league = self._soccer_discovery.discover(pos) or ""

                if espn_sport and espn_league:
                    unique_espn.add((tag, espn_sport, espn_league))
            
            tags_requiring_odds.add(tag)

        self._cached_espn.clear()
        self._cached_odds.clear()

        # Cricket (SPEC-011)
        has_cricket = any(is_cricket_sport(p.sport_tag) for p in active_positions)
        if has_cricket and self._cricket_client is not None:
            matches = self._cricket_client.get_current_matches()
            if matches is not None:
                self._cached_cricket = matches

        # 2. ESPN Fetch & Merge
        for tag, sport, league in unique_espn:
            espn_scores = self._fetch_espn(sport, league)
            if espn_scores:
                if tag not in self._cached_espn:
                    self._cached_espn[tag] = []
                self._cached_espn[tag].extend(espn_scores)

        # 3. Odds API Fallback (sadece ESPN bossa ve tennis degilse)
        if self._odds is not None:
            for tag in tags_requiring_odds:
                if tag != "tennis" and not self._cached_espn.get(tag):
                    odds_key = _ODDS_API_KEY_MAP.get(tag, "")
                    if odds_key:
                        odds_scores = fetch_scores(self._odds, odds_key)
                        if odds_scores:
                            self._cached_odds[tag] = odds_scores
                            logger.info("Odds API fallback: %s -> %d events", odds_key, len(odds_scores))

    def _fetch_espn(self, sport: str, league: str) -> list[ESPNMatchScore]:
        """ESPN client çağrısı; hata → boş liste + WARNING log."""
        if self._espn is None or not sport or not league:
            return []
        try:
            scores = self._espn.fetch(sport, league)
            if scores:
                logger.info("ESPN fetch: %s/%s → %d events", sport, league, len(scores))
            return scores
        except Exception as exc:  # noqa: BLE001
            logger.warning("ESPN fetch error [%s/%s]: %s", sport, league, exc)
            return []

    def _match_cached(self, positions: dict[str, Position]) -> dict[str, dict]:
        """Cached skor verisiyle pozisyonları eşleştir."""
        result: dict[str, dict] = {}
        for cid, pos in positions.items():
            tag = _normalize(pos.sport_tag)
            matched_score_obj = None

            espn_scores = self._cached_espn.get(tag, [])
            if espn_scores:
                em = _find_match_via_pair(pos, espn_scores, "home_name", "away_name")
                if em:
                    result[cid] = _build_score_info(pos, em)
                    matched_score_obj = em

            if matched_score_obj is None:
                odds_scores = self._cached_odds.get(tag, [])
                if odds_scores:
                    ms = _find_match_via_pair(pos, odds_scores, "home_team", "away_team")
                    if ms:
                        result[cid] = _build_score_info(pos, ms)
                        matched_score_obj = ms

            # Archive: skor degisikligi + match result (SPEC-009)
            if matched_score_obj is not None:
                pos.match_score = (
                    f"{matched_score_obj.home_score}-{matched_score_obj.away_score}"
                )
                pos.match_period = getattr(matched_score_obj, "period", "") or ""
                self._maybe_log_score_event(pos, matched_score_obj)
                self._maybe_log_match_result(pos, matched_score_obj)

                if cid in result:
                    espn_obj = matched_score_obj if isinstance(matched_score_obj, ESPNMatchScore) else None
                    _sport_cfg = {
                        "match_duration_hours": get_sport_rule(tag, "match_duration_hours", 2.0),
                        "espn_sport": get_sport_rule(tag, "espn_sport", ""),
                    }
                    result[cid]["match_clock"] = build_match_clock(
                        espn_score=espn_obj,
                        match_start_iso=pos.match_start_iso,
                        sport_tag=tag,
                        sport_config=_sport_cfg,
                    )

        return result

    def _maybe_log_score_event(self, pos: Position, ms: object) -> None:
        """Skor degisikligini tespit edip archive'a yaz (SPEC-009)."""
        if self._archive_logger is None:
            return
        event_id = getattr(pos, "event_id", "") or ""
        if not event_id:
            return
        home_score = getattr(ms, "home_score", None)
        away_score = getattr(ms, "away_score", None)
        if home_score is None or away_score is None:
            return
        new_score = f"{home_score}-{away_score}"
        prev_score = self._prev_score_by_event.get(event_id, "")
        if prev_score == "":
            self._prev_score_by_event[event_id] = new_score
            return
        if new_score == prev_score:
            return
        self._archive_logger.log_score_event(ArchiveScoreEvent(
            event_id=event_id,
            slug=pos.slug,
            sport_tag=pos.sport_tag,
            timestamp=datetime.now(timezone.utc).isoformat(),
            prev_score=prev_score,
            new_score=new_score,
            period=getattr(ms, "period", "") or "",
        ))
        self._prev_score_by_event[event_id] = new_score

    def _maybe_log_match_result(self, pos: Position, ms: object) -> None:
        """Mac tamamlandiysa match_result log'la (SPEC-009). Duplicate atma."""
        if self._archive_logger is None:
            return
        is_completed = getattr(ms, "is_completed", False)
        if not is_completed:
            return
        event_id = getattr(pos, "event_id", "") or ""
        if not event_id or event_id in self._logged_match_event_ids:
            return
        home_score = getattr(ms, "home_score", None)
        away_score = getattr(ms, "away_score", None)
        if home_score is None or away_score is None:
            return
        winner_home: bool | None = None
        if home_score > away_score:
            winner_home = True
        elif away_score > home_score:
            winner_home = False

        self._archive_logger.log_match_result(ArchiveMatchResult(
            event_id=event_id,
            slug=pos.slug,
            sport_tag=pos.sport_tag,
            final_score=f"{home_score}-{away_score}",
            winner_home=winner_home,
            completed_timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        self._logged_match_event_ids.add(event_id)
