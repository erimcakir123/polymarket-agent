"""NBA market_type-aware dispatch: spreads → spread_exit, totals → totals_exit, else → score_exit.

monitor.py'dan extract edildi (400-line guard).
Strategy katmanı, I/O yok.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import BasketballExitConfig
from src.models.position import Position
from src.strategy.exit import nba_score_exit, nba_spread_exit, nba_totals_exit


@dataclass
class NBADispatchResult:
    reason: object  # ExitReason enum (str mixin)
    detail: str
    partial: bool
    sell_pct: float


def check_nba_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
    basketball_exit_cfg: BasketballExitConfig | None,
) -> NBADispatchResult | None:
    """NBA market-type dispatch. None → HOLD."""
    _bk = basketball_exit_cfg or BasketballExitConfig()
    mtype = pos.sports_market_type or "moneyline"
    _predictive = dict(
        predictive_enabled=_bk.predictive_exit.enabled,
        predictive_safety_margin=_bk.predictive_exit.safety_margin,
        predictive_hold_threshold=_bk.predictive_exit.hold_threshold,
    )

    if mtype == "spreads" and pos.spread_line is not None:
        sp_result = nba_spread_exit.check(
            score_info=score_info,
            spread_line=pos.spread_line,
            direction=pos.direction,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            bill_james_multiplier=_bk.bill_james_multiplier,
            structural_damage_ratio=_bk.structural_damage_ratio,
            ot_seconds=_bk.overtime.seconds,
            ot_margin=_bk.overtime.deficit,
            q4_late_seconds=_bk.spread_empirical.q4_late_seconds,
            q4_late_margin=_bk.spread_empirical.q4_late_margin,
            q4_final_seconds=_bk.spread_empirical.q4_final_seconds,
            q4_final_margin=_bk.spread_empirical.q4_final_margin,
            q4_endgame_seconds=_bk.spread_empirical.q4_endgame_seconds,
            q4_endgame_margin=_bk.spread_empirical.q4_endgame_margin,
            **_predictive,
        )
        if sp_result is not None:
            return NBADispatchResult(
                reason=sp_result.reason, detail=sp_result.detail,
                partial=sp_result.partial, sell_pct=sp_result.sell_pct,
            )
        return None

    if mtype == "totals" and pos.total_line is not None:
        effective_side = pos.total_side or "over"
        tot_result = nba_totals_exit.check(
            score_info=score_info,
            target_total=pos.total_line,
            side=effective_side,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            totals_multiplier=_bk.totals_multiplier,
            structural_damage_ratio=_bk.structural_damage_ratio,
            ot_over_scale_pct=_bk.totals_empirical.ot_over_scale_pct,
            q4_late_seconds=_bk.totals_empirical.q4_late_seconds,
            q4_late_gap=_bk.totals_empirical.q4_late_gap,
            q4_final_seconds=_bk.totals_empirical.q4_final_seconds,
            q4_final_gap=_bk.totals_empirical.q4_final_gap,
            q4_endgame_seconds=_bk.totals_empirical.q4_endgame_seconds,
            q4_endgame_gap=_bk.totals_empirical.q4_endgame_gap,
            **_predictive,
        )
        if tot_result is not None:
            return NBADispatchResult(
                reason=tot_result.reason, detail=tot_result.detail,
                partial=tot_result.partial, sell_pct=tot_result.sell_pct,
            )
        return None

    # moneyline (or spread_line/total_line missing — disabled)
    nba_result = nba_score_exit.check(
        score_info=score_info,
        elapsed_pct=elapsed_pct,
        sport_tag=pos.sport_tag,
        bid_price=pos.bid_price,
        entry_price=pos.entry_price,
        bill_james_multiplier=_bk.bill_james_multiplier,
        structural_damage_ratio=_bk.structural_damage_ratio,
        ot_seconds=_bk.overtime.seconds,
        ot_deficit=_bk.overtime.deficit,
        q4_blowout_seconds=_bk.empirical.q4_blowout_seconds,
        q4_blowout_deficit=_bk.empirical.q4_blowout_deficit,
        q4_late_seconds=_bk.empirical.q4_late_seconds,
        q4_late_deficit=_bk.empirical.q4_late_deficit,
        q4_final_seconds=_bk.empirical.q4_final_seconds,
        q4_final_deficit=_bk.empirical.q4_final_deficit,
        q4_endgame_seconds=_bk.empirical.q4_endgame_seconds,
        q4_endgame_deficit=_bk.empirical.q4_endgame_deficit,
        **_predictive,
    )
    if nba_result is not None:
        return NBADispatchResult(
            reason=nba_result.reason, detail=nba_result.detail,
            partial=nba_result.partial, sell_pct=nba_result.sell_pct,
        )
    return None
