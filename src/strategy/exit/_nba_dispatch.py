"""NBA market_type dispatch (SPEC-J Group 3C).

Position'a göre route eder:
  TOTALS  → nba_totals_exit.check (pos.total_side kullanılır)
  MONEYLINE / SPREADS / eksik metadata → None (bu dispatch scope dışı)

NOT: NBA SPREADS exit modülü 2026-05-15 rollback (Faz 3/10) ile silindi.
112 trade taramasında SPREADS için 0 işlem açıldı (dead code). TOTALS exit
canlı (+$21 kanıt, korundu).

Strategy katmanı: I/O yok, log yok, monitor.py orchestration buna bağlanır.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.settings import BasketballExitConfig
from src.models.enums import ExitReason, SportsMarketType
from src.models.position import Position
from src.strategy.exit import nba_totals_exit


@dataclass
class NbaDispatchResult:
    reason: ExitReason
    detail: str
    partial: bool
    sell_pct: float


def check_nba_exit(
    pos: Position,
    score_info: dict,
    # _elapsed_pct: kept for signature symmetry with future moneyline integration
    _elapsed_pct: float,
    basketball_exit_cfg: BasketballExitConfig | None,
) -> NbaDispatchResult | None:
    """NBA market-type dispatch. None → HOLD."""
    cfg = basketball_exit_cfg or BasketballExitConfig()
    predictive_kwargs = dict(
        predictive_enabled=cfg.predictive_exit.enabled,
        predictive_safety_margin=cfg.predictive_exit.safety_margin,
        predictive_hold_threshold=cfg.predictive_exit.hold_threshold,
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
            _ot_over_scale_pct=cfg.totals_empirical.ot_over_scale_pct,
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
        return NbaDispatchResult(
            reason=tot_result.reason,
            detail=tot_result.detail,
            partial=tot_result.partial,
            sell_pct=tot_result.sell_pct,
        )

    # MONEYLINE / SPREADS / eksik total_line/total_side → bu dispatch scope dışı.
    return None
