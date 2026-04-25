"""Edge enricher — injury + back-to-back context for NBA entry decisions."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.models.market import MarketData
    from src.infrastructure.apis.espn_injury_client import InjuryEvent

logger = logging.getLogger(__name__)


@dataclass
class EdgeContext:
    has_recent_injury: bool = False
    injured_starter_name: str | None = None
    injury_reported_at: datetime | None = None
    injury_team_id: str | None = None   # Which team has injury
    is_opponent_back_to_back: bool = False
    is_our_back_to_back: bool = False


class EdgeEnricher:
    """Computes injury + back-to-back context for a market.

    Injected clients allow full mock coverage in tests without HTTP calls.
    """

    def __init__(
        self,
        injury_client: Any,
        schedule_client: Any,
        injury_window_hours: int = 2,
    ) -> None:
        self._injury_client = injury_client
        self._schedule_client = schedule_client
        self._injury_window_hours = injury_window_hours

    # ── Public API ──────────────────────────────────────────────────────────

    def enrich(
        self,
        market: MarketData,
        our_team_id: str,
        opp_team_id: str,
    ) -> EdgeContext:
        """Compute injury + B2B context for a market.

        our_team_id: ESPN team ID for the team we're betting on (BUY_YES = favorite)
        opp_team_id: ESPN team ID for the opponent
        Empty string team IDs → skip that check gracefully.
        """
        ctx = EdgeContext()

        game_date = self._parse_game_date(market.match_start_iso)
        season = self._nba_season(game_date)

        self._apply_injury_context(ctx, our_team_id, opp_team_id)
        self._apply_b2b_context(ctx, our_team_id, opp_team_id, game_date, season)

        return ctx

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_game_date(match_start_iso: str) -> datetime:
        """Parse ISO 8601 string; fall back to now(UTC) on any failure."""
        if match_start_iso:
            try:
                return datetime.fromisoformat(
                    match_start_iso.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError) as exc:
                logger.warning("EdgeEnricher: game date parse failed (%r): %s", match_start_iso, exc)
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def _nba_season(game_date: datetime) -> int:
        """NBA season year: Oct+ games belong to the *next* calendar year's season.

        e.g. Oct 2025 → season 2026  (the 2025-26 season)
             Apr 2026 → season 2026
        """
        return game_date.year + (1 if game_date.month >= 10 else 0)

    def _apply_injury_context(
        self,
        ctx: EdgeContext,
        our_team_id: str,
        opp_team_id: str,
    ) -> None:
        """Fetch recent injuries and populate ctx if significant injury found."""
        if not our_team_id and not opp_team_id:
            return  # No team IDs to check
        injuries_by_team: dict[str, list[InjuryEvent]] = (
            self._injury_client.get_recent_injuries(hours=self._injury_window_hours)
        )

        # Check our team first, then opponent — stop at first match.
        for team_id in (our_team_id, opp_team_id):
            if not team_id:
                continue
            team_injuries = injuries_by_team.get(team_id) or []
            inj = self._find_injury(team_injuries)
            if inj is not None:
                ctx.has_recent_injury = True
                ctx.injured_starter_name = inj.athlete_name
                ctx.injury_reported_at = inj.reported_at
                ctx.injury_team_id = inj.team_id
                return   # one injury context per call

    def _apply_b2b_context(
        self,
        ctx: EdgeContext,
        our_team_id: str,
        opp_team_id: str,
        game_date: datetime,
        season: int,
    ) -> None:
        """Query schedule client for B2B status; log + default on failure."""
        if our_team_id:
            try:
                ctx.is_our_back_to_back = self._schedule_client.is_back_to_back(
                    our_team_id, game_date, season
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "EdgeEnricher: B2B check failed for our_team=%s: %s",
                    our_team_id,
                    exc,
                )

        if opp_team_id:
            try:
                ctx.is_opponent_back_to_back = self._schedule_client.is_back_to_back(
                    opp_team_id, game_date, season
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "EdgeEnricher: B2B check failed for opp_team=%s: %s",
                    opp_team_id,
                    exc,
                )

    @staticmethod
    def _find_injury(injuries: list[InjuryEvent]) -> InjuryEvent | None:
        """Select the most significant injury from a list.

        Priority:
          1st — Out + is_starter
          2nd — Doubtful + is_starter
          3rd — any Out or Doubtful (non-starter)
          None if nothing qualifies.
        """
        out_starters = [i for i in injuries if i.status == "Out" and i.is_starter]
        if out_starters:
            return out_starters[0]

        doubtful_starters = [i for i in injuries if i.status == "Doubtful" and i.is_starter]
        if doubtful_starters:
            return doubtful_starters[0]

        # Priority 3: Out non-starter
        out_non_starters = [i for i in injuries if i.status == "Out" and not i.is_starter]
        if out_non_starters:
            return out_non_starters[0]

        # Priority 4: Doubtful non-starter
        doubtful_non_starters = [i for i in injuries if i.status == "Doubtful" and not i.is_starter]
        if doubtful_non_starters:
            return doubtful_non_starters[0]

        return None
