"""NHL edge modifier helper. Called from gate._apply_edge_modifiers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.domain.matching.team_resolver import resolve_nhl_espn_id
from src.domain.sports.nhl_question_parser import parse_nhl_question


def apply_nhl_edge_modifiers(
    market: Any,
    nhl_edge_enricher: Any,
    config: Any,
) -> tuple[float, float]:
    """NHL B2B modifier. Goalie confirmation deferred (no probables flow v1).

    Returns (gap_threshold_adj, size_multiplier_adj).
    """
    gap_adj = 0.0
    size_mult = 1.0

    if nhl_edge_enricher is None:
        return gap_adj, size_mult

    teams = parse_nhl_question(getattr(market, "question", ""))
    if teams is None:
        return gap_adj, size_mult
    team_a, team_b = teams

    our_id = resolve_nhl_espn_id(team_a)
    opp_id = resolve_nhl_espn_id(team_b)
    if not our_id or not opp_id:
        return gap_adj, size_mult

    try:
        ctx = nhl_edge_enricher.enrich(
            our_team_id=our_id,
            opp_team_id=opp_id,
            game_date=datetime.now(timezone.utc),
            probables_home=None,
            probables_away=None,
            we_are_home=True,
        )
    except Exception:  # noqa: BLE001
        return gap_adj, size_mult

    if ctx.is_opponent_back_to_back:
        gap_adj -= config.nhl_b2b_opponent_gap_bonus
        size_mult *= config.nhl_b2b_opponent_size_mult

    if ctx.is_our_back_to_back:
        gap_adj += config.nhl_b2b_self_gap_bonus

    return gap_adj, size_mult
