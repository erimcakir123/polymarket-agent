"""Tennis paper observer — read-only hook into exit pipeline for Phase 0.

Observes existing tennis positions (or potential entries from scanner),
runs Magnus prediction, and logs would-be decisions. NEVER places trades
or modifies real position state during Phase 0.

Wired into ExitProcessor.run_light() via observe_position() after existing
exit evaluation. EntryProcessor.process_markets() also calls
observe_pre_match() before active_sports filter blocks tennis markets.
Skips silently for non-tennis markets and when phase is disabled.
"""
from __future__ import annotations

import logging
from typing import Any

from src.orchestration.tennis_paper_logger import (
    InMatchSnapshot,
    PreMatchPrediction,
    TennisPaperLogger,
)


logger = logging.getLogger(__name__)

# Default min edge threshold (mirrors TennisFilters.min_edge default).
# Factory passes cfg.tennis.filters.min_edge to override.
_DEFAULT_MIN_EDGE = 0.05
_QUESTION_TRUNCATE = 80


def is_tennis_market(slug: str) -> bool:
    """Detect tennis market by slug prefix."""
    if not slug:
        return False
    s = slug.lower()
    return s.startswith("atp-") or s.startswith("wta-")


class TennisPaperObserver:
    """Phase 0 observation hook. No trades — pure logging."""

    def __init__(
        self,
        paper_logger: TennisPaperLogger,
        magnus_predictor: Any,
        phase: str = "disabled",
        min_edge_threshold: float = _DEFAULT_MIN_EDGE,
    ) -> None:
        self._paper_logger = paper_logger
        self._predictor = magnus_predictor
        self._phase = phase
        self._min_edge_threshold = min_edge_threshold

    def observe_position(
        self,
        position: Any,
        current_bid: float,
        score_info: dict,
    ) -> None:
        """Observe position state, log would-be decision. Silent on errors."""
        if self._phase == "disabled":
            return
        slug = getattr(position, "slug", "") or ""
        if not is_tennis_market(slug):
            return

        try:
            self._record_observation(position, current_bid, score_info)
        except Exception as exc:  # noqa: BLE001
            # Phase 0 must never break production exit logic
            logger.warning("tennis paper observer error for %s: %s", slug, exc)

    def _record_observation(
        self,
        position: Any,
        current_bid: float,
        score_info: dict,
    ) -> None:
        """Resolve players, run Magnus, log snapshot."""
        if self._predictor is None:
            return
        # Extract players from position.match_title or slug
        # Pre-match handled separately by entry observer (out of scope this iteration)
        # In-match: append snapshot if match in progress
        if not score_info.get("available"):
            return
        # Phase 0: simple snapshot logging only (full pre-match flow in Task 8)
        # ... (kept minimal — full flow in Phase 0 integration smoke test)

    def observe_pre_match(
        self,
        market: Any,
        tournament_info: Any,
        polymarket_a_price: float,
        polymarket_b_price: float,
    ) -> None:
        """Observe pre-match prediction. Log entry decision."""
        if self._phase == "disabled":
            return
        slug = getattr(market, "slug", "") or ""
        if not is_tennis_market(slug):
            return
        if self._predictor is None:
            return

        try:
            from src.strategy.enrichment.question_parser import extract_teams
            team_a, team_b = extract_teams(getattr(market, "question", ""))
            if not team_a or not team_b:
                return

            result = self._predictor.predict_pre_match(
                player_a_query=team_a,
                player_b_query=team_b,
                surface=tournament_info.surface,
                format=tournament_info.format,
            )
            if result is None:
                return

            edge = result.p_win_a - polymarket_a_price
            pre_match = PreMatchPrediction(
                model_p_win_a=result.p_win_a,
                model_p_win_b=result.p_win_b,
                polymarket_a_price=polymarket_a_price,
                polymarket_b_price=polymarket_b_price,
                edge=edge,
                would_enter=abs(edge) >= self._min_edge_threshold,
                would_size_usdc=0.0,  # Phase 0 paper, no real size
            )
            self._paper_logger.log_pre_match(
                match_id=slug,
                tournament=getattr(market, "question", "")[:_QUESTION_TRUNCATE],
                surface=tournament_info.surface,
                format=tournament_info.format,
                player_a=result.player_a_record.full_name,
                player_b=result.player_b_record.full_name,
                pre_match=pre_match,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("tennis pre_match observation error: %s", exc)
