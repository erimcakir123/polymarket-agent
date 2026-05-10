"""NBA market_type dispatch (SPEC-J Group 3C).

Position'a göre route eder:
  SPREADS → nba_spread_exit.check (slug'tan home/away çıkarılır)
  TOTALS  → nba_totals_exit.check (pos.total_side kullanılır)
  MONEYLINE / eksik metadata → None (bu dispatch scope dışı)

Strategy katmanı: I/O yok, log yok, monitor.py orchestration buna bağlanır.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import BasketballExitConfig
from src.models.enums import ExitReason, SportsMarketType
from src.models.position import Position
from src.strategy.exit import nba_spread_exit, nba_totals_exit


@dataclass
class NBADispatchResult:
    reason: ExitReason
    detail: str
    partial: bool
    sell_pct: float


def check_nba_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,    # MVP: spread/totals direkt period+clock kullanır; signature consistency.
    basketball_exit_cfg: BasketballExitConfig | None,
) -> NBADispatchResult | None:
    """NBA market-type dispatch. None → HOLD."""
    del elapsed_pct  # MVP: spread/totals period+clock kullanır; signature için tutuldu.

    cfg = basketball_exit_cfg or BasketballExitConfig()
    predictive_kwargs = dict(
        predictive_enabled=cfg.predictive_exit.enabled,
        predictive_safety_margin=cfg.predictive_exit.safety_margin,
        predictive_hold_threshold=cfg.predictive_exit.hold_threshold,
    )

    if pos.sports_market_type == SportsMarketType.SPREADS and pos.spread_line is not None:
        spread_side = _spread_side_from_slug(pos.slug)
        if spread_side is None:
            return None
        sp_result = nba_spread_exit.check(
            score_info=score_info,
            spread_line=pos.spread_line,
            direction=pos.direction,
            spread_side=spread_side,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            bill_james_multiplier=cfg.bill_james_multiplier,
            structural_damage_ratio=cfg.structural_damage_ratio,
            ot_seconds=cfg.overtime.seconds,
            ot_margin=cfg.overtime.deficit,
            q4_late_seconds=cfg.spread_empirical.q4_late_seconds,
            q4_late_margin=cfg.spread_empirical.q4_late_margin,
            q4_final_seconds=cfg.spread_empirical.q4_final_seconds,
            q4_final_margin=cfg.spread_empirical.q4_final_margin,
            q4_endgame_seconds=cfg.spread_empirical.q4_endgame_seconds,
            q4_endgame_margin=cfg.spread_empirical.q4_endgame_margin,
            **predictive_kwargs,
        )
        if sp_result is None:
            return None
        return NBADispatchResult(
            reason=sp_result.reason,
            detail=sp_result.detail,
            partial=sp_result.partial,
            sell_pct=sp_result.sell_pct,
        )

    if (
        pos.sports_market_type == SportsMarketType.TOTALS
        and pos.total_line is not None
        and pos.total_side is not None
    ):
        tot_result = nba_totals_exit.check(
            score_info=score_info,
            target_total=pos.total_line,
            side=pos.total_side.value,
            bid_price=pos.bid_price,
            entry_price=pos.entry_price,
            totals_multiplier=cfg.totals_multiplier,
            structural_damage_ratio=cfg.structural_damage_ratio,
            ot_over_scale_pct=cfg.totals_empirical.ot_over_scale_pct,
            q4_late_seconds=cfg.totals_empirical.q4_late_seconds,
            q4_late_gap=cfg.totals_empirical.q4_late_gap,
            q4_final_seconds=cfg.totals_empirical.q4_final_seconds,
            q4_final_gap=cfg.totals_empirical.q4_final_gap,
            q4_endgame_seconds=cfg.totals_empirical.q4_endgame_seconds,
            q4_endgame_gap=cfg.totals_empirical.q4_endgame_gap,
            **predictive_kwargs,
        )
        if tot_result is None:
            return None
        return NBADispatchResult(
            reason=tot_result.reason,
            detail=tot_result.detail,
            partial=tot_result.partial,
            sell_pct=tot_result.sell_pct,
        )

    # MONEYLINE veya eksik spread_line/total_line/total_side → bu dispatch scope dışı.
    return None


def _spread_side_from_slug(slug: str) -> str | None:
    """Slug suffix'ten spread tarafını çıkar.

    Polymarket slug konvansiyonu: '...-spread-home-...' veya '...-spread-away-...'.
    """
    slug_lc = slug.lower()
    if "-spread-home-" in slug_lc:
        return "home"
    if "-spread-away-" in slug_lc:
        return "away"
    return None
