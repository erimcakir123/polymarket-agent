"""Tennis Magnus predictor — composition root combining all pieces.

Resolves player names → loads serve stats → applies surface adjustment
→ runs Magnus chain. Single source of P(A wins) for both pre-match and
in-match queries.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from src.domain.math.tennis_magnus import (
    MatchState,
    p_match_bo3,
    p_match_from_state,
)
from src.domain.matching.tennis_player_resolver import (
    PlayerRecord,
    PlayerRegistry,
    resolve_player,
)
from src.infrastructure.apis.sackmann_client import (
    PlayerServeStats,
    aggregate_player_stats,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PredictionResult:
    p_win_a: float
    p_win_b: float
    p_serve_a: float
    p_serve_b: float
    player_a_record: PlayerRecord
    player_b_record: PlayerRecord


class TennisMagnusPredictor:
    """Predicts P(A wins match) given player names + state."""

    def __init__(
        self,
        registry: PlayerRegistry,
        matches: list[dict],
        surface_factors: dict[str, dict[str, float]],
    ) -> None:
        self._registry = registry
        self._matches = matches
        self._surface_factors = surface_factors

    def predict_pre_match(
        self,
        player_a_query: str,
        player_b_query: str,
        surface: Literal["clay", "hard", "grass"],
        format: Literal["BO3", "BO5"],
        is_wta: bool,
    ) -> PredictionResult | None:
        prep = self._prepare_inputs(player_a_query, player_b_query, surface, is_wta)
        if prep is None:
            return None
        rec_a, rec_b, p_a_adj, p_b_adj = prep
        if format == "BO5":
            return None  # Phase 2
        p_win_a = p_match_bo3(p_a_adj, p_b_adj)
        return PredictionResult(
            p_win_a=p_win_a,
            p_win_b=1 - p_win_a,
            p_serve_a=p_a_adj,
            p_serve_b=p_b_adj,
            player_a_record=rec_a,
            player_b_record=rec_b,
        )

    def predict_with_state(
        self,
        player_a_query: str,
        player_b_query: str,
        surface: Literal["clay", "hard", "grass"],
        format: Literal["BO3", "BO5"],
        sets_won_a: int,
        sets_won_b: int,
        games_a: int,
        games_b: int,
        server_is_a: bool,
        is_wta: bool,
    ) -> PredictionResult | None:
        prep = self._prepare_inputs(player_a_query, player_b_query, surface, is_wta)
        if prep is None:
            return None
        rec_a, rec_b, p_a_adj, p_b_adj = prep
        state = MatchState(
            sets_won_a=sets_won_a, sets_won_b=sets_won_b,
            games_a=games_a, games_b=games_b,
            server_is_a=server_is_a, format=format,
        )
        p_win_a = p_match_from_state(p_a_adj, p_b_adj, state)
        return PredictionResult(
            p_win_a=p_win_a,
            p_win_b=1 - p_win_a,
            p_serve_a=p_a_adj,
            p_serve_b=p_b_adj,
            player_a_record=rec_a,
            player_b_record=rec_b,
        )

    def _prepare_inputs(
        self,
        player_a_query: str,
        player_b_query: str,
        surface: str,
        is_wta: bool,
    ) -> tuple[PlayerRecord, PlayerRecord, float, float] | None:
        rec_a = resolve_player(player_a_query, self._registry)
        rec_b = resolve_player(player_b_query, self._registry)
        if rec_a is None or rec_b is None:
            logger.info("magnus_predictor: cannot resolve %s or %s", player_a_query, player_b_query)
            return None

        stats_a = aggregate_player_stats(rec_a.full_name, self._matches, surface=None)
        stats_b = aggregate_player_stats(rec_b.full_name, self._matches, surface=None)
        if stats_a is None or stats_b is None:
            logger.info("magnus_predictor: no stats for %s or %s", rec_a.full_name, rec_b.full_name)
            return None

        gender = "wta" if is_wta else "atp"
        factor = self._surface_factors.get(gender, {}).get(surface, 1.0)
        p_a_adj = max(0.0, min(1.0, stats_a.service_points_won_pct * factor))
        p_b_adj = max(0.0, min(1.0, stats_b.service_points_won_pct * factor))
        return rec_a, rec_b, p_a_adj, p_b_adj
