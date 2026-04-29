"""NHL totals dispatch: score_info + Position → NHLSignal | None.

monitor.py import YOK (circular safe).
Strategy katmanı, I/O yok.
"""
from __future__ import annotations

from src.domain.math.nhl_totals_probability import p_over_hybrid
from src.domain.sports.nhl_match_clock import period_clock_to_regulation_seconds
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_totals_decision
from src.strategy.exit.nhl_totals_exit import NHLTotalsExitConfig, decide_nhl_totals_exit


def check_nhl_totals_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,
    nhl_totals_cfg: NHLTotalsExitConfig,
    nhl_totals_table: dict,
) -> NHLSignal | None:
    """Decide NHL totals exit signal. Returns None → HOLD."""
    # period_number int (ESPN raw status.period) öncelikli; "period" string
    # description ("Scheduled", "1st Period") fallback ama int değilse None döner.
    # Pre-match'te period_number=None, period="Scheduled" → exit fire etmez.
    period = score_info.get("period_number") or score_info.get("period")
    if not isinstance(period, int) or period <= 0:
        return None
    period_clock = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")

    target_total = getattr(pos, "total_line", None)
    side = getattr(pos, "total_side", None) or "over"

    if any(v is None for v in (period_clock, our_score, opp_score, target_total)):
        return None

    # ESPN displayClock periyot bazlı (0–1200s); empirical tablo ve Skellam λ
    # regulation-total bazlı (0–3600s) kalibre. Dispatch dönüşümü yapar.
    seconds_remaining = period_clock_to_regulation_seconds(period, period_clock)
    current_total = int(our_score + opp_score)

    def _p_fn(p: int, c: int, s: int, t: float) -> tuple[float, str]:
        return p_over_hybrid(p, c, s, t, table=nhl_totals_table)

    decision = decide_nhl_totals_exit(
        cfg=nhl_totals_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=seconds_remaining,
        current_total=current_total,
        target_total=float(target_total),
        side=side,
        p_over_fn=_p_fn,
    )
    return map_nhl_totals_decision(decision)
