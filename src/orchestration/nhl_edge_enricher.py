"""NHL edge enricher — goalie + back-to-back context for NHL entry decisions."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NHLEdgeContext:
    starting_goalie_home: str | None = None    # ESPN player ID
    starting_goalie_away: str | None = None    # ESPN player ID
    goalie_status_home: str = "unknown"        # confirmed | expected | unknown
    goalie_status_away: str = "unknown"
    is_opponent_back_to_back: bool = False
    is_our_back_to_back: bool = False
    raw_probables: list[dict] = field(default_factory=list)
    we_are_home: bool = True


class NHLEdgeEnricher:
    """Computes goalie + back-to-back context for NHL markets.

    Probables (ESPN scoreboard) are passed directly to enrich() — caller
    is responsible for fetching. Schedule client injected for B2B checks.
    """

    def __init__(self, schedule_client: Any) -> None:
        self._schedule_client = schedule_client

    def enrich(
        self,
        *,
        our_team_id: str,
        opp_team_id: str,
        game_date: datetime,
        probables_home: dict | None,
        probables_away: dict | None,
        we_are_home: bool,
    ) -> NHLEdgeContext:
        """Compute goalie + B2B context for an NHL market."""
        ctx = NHLEdgeContext()

        home_id, home_status = self._extract_goalie(probables_home)
        away_id, away_status = self._extract_goalie(probables_away)

        ctx.starting_goalie_home = home_id
        ctx.starting_goalie_away = away_id
        ctx.goalie_status_home = home_status
        ctx.goalie_status_away = away_status
        ctx.we_are_home = we_are_home

        for p in (probables_home, probables_away):
            if p is not None:
                ctx.raw_probables.append(p)

        self._apply_b2b_context(ctx, our_team_id, opp_team_id, game_date)

        return ctx

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_goalie(probables: dict | None) -> tuple[str | None, str]:
        """ESPN probables dict → (player_id, status).

        {"name":"probableStartingGoalie","playerId":4712036,
         "athlete":{"id":"4712036","fullName":"Jeremy Swayman"}}

        - athlete.id present → confirmed
        - playerId present, no athlete → expected
        - neither → unknown
        """
        if not probables or not isinstance(probables, dict):
            return None, "unknown"
        athlete = probables.get("athlete")
        if isinstance(athlete, dict):
            athlete_id = athlete.get("id")
            if athlete_id:
                return str(athlete_id), "confirmed"
        player_id = probables.get("playerId")
        if player_id:
            return str(player_id), "expected"
        return None, "unknown"

    def _apply_b2b_context(
        self,
        ctx: NHLEdgeContext,
        our_team_id: str,
        opp_team_id: str,
        game_date: datetime,
    ) -> None:
        """Query schedule client for B2B status; log + default on failure."""
        if our_team_id:
            try:
                ctx.is_our_back_to_back = self._schedule_client.is_back_to_back(
                    team_id=our_team_id, game_date=game_date
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "NHLEdgeEnricher: B2B check failed for our_team=%s: %s",
                    our_team_id,
                    exc,
                )

        if opp_team_id:
            try:
                ctx.is_opponent_back_to_back = self._schedule_client.is_back_to_back(
                    team_id=opp_team_id, game_date=game_date
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "NHLEdgeEnricher: B2B check failed for opp_team=%s: %s",
                    opp_team_id,
                    exc,
                )
