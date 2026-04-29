"""Tennis paper observer — read-only hook into exit pipeline for Phase 0.

Observes existing tennis positions (or potential entries from scanner),
runs Magnus prediction, and logs would-be decisions. NEVER places trades
or modifies real position state during Phase 0.

Wired into ExitProcessor.run_light() via observe_position() after existing
exit evaluation. Skips silently for non-tennis markets and when phase is
disabled.
"""
from __future__ import annotations

import logging
from typing import Any

from src.orchestration.tennis_paper_logger import (
    InMatchSnapshot,
    TennisPaperLogger,
)


logger = logging.getLogger(__name__)


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
    ) -> None:
        self._paper_logger = paper_logger
        self._predictor = magnus_predictor
        self._phase = phase

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
