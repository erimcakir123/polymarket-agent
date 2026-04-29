"""NHL puck line dispatch: score_info + Position → NHLSignal | None.

monitor.py import YOK (circular import önlemi).
Strategy katmanı: tablo dışarıdan inject edilir, I/O yok.
"""
from __future__ import annotations

from src.domain.math.nhl_puck_line_probability import p_favorite_covers_hybrid
from src.domain.sports.nhl_match_clock import period_clock_to_regulation_seconds
from src.models.position import Position
from src.strategy.exit._nhl_exit_mapping import NHLSignal, map_nhl_puck_line_decision
from src.strategy.exit.nhl_puck_line_exit import (
    NHLPuckLineExitConfig,
    decide_nhl_puck_line_exit,
)


def check_nhl_puck_line_exit(
    pos: Position,
    score_info: dict,
    elapsed_pct: float,  # şimdilik kullanılmıyor, signature uyum
    nhl_puck_line_cfg: NHLPuckLineExitConfig,
    nhl_puck_line_table: dict,
) -> NHLSignal | None:
    """Decide NHL puck line exit signal. Returns None → HOLD."""
    # period_number int (ESPN raw status.period) öncelikli; "period" string
    # description ("Scheduled", "1st Period") fallback ama int değilse None döner.
    # Pre-match'te period_number=None, period="Scheduled" → exit fire etmez.
    period = score_info.get("period_number") or score_info.get("period")
    if not isinstance(period, int) or period <= 0:
        return None
    period_clock = score_info.get("clock_seconds")
    our_score = score_info.get("our_score")
    opp_score = score_info.get("opp_score")

    if any(v is None for v in (period_clock, our_score, opp_score)):
        return None

    # ESPN displayClock periyot bazlı (0–1200s); empirical tablo ve Skellam λ
    # regulation-total bazlı (0–3600s) kalibre. Dispatch dönüşümü yapar.
    seconds_remaining = period_clock_to_regulation_seconds(period, period_clock)

    direction = getattr(pos, "direction", "BUY_YES")
    if direction == "BUY_YES":
        current_margin = our_score - opp_score
    else:
        current_margin = opp_score - our_score

    def _p_fn(p: int, m: int, s: int) -> tuple[float, str]:
        return p_favorite_covers_hybrid(p, m, s, table=nhl_puck_line_table)

    decision = decide_nhl_puck_line_exit(
        cfg=nhl_puck_line_cfg,
        entry_price=pos.entry_price,
        current_bid=pos.bid_price,
        current_price=pos.current_price,
        scaled_out_50=pos.scaled_out_50,
        period=period,
        seconds_remaining=seconds_remaining,
        current_margin=current_margin,
        p_cover_fn=_p_fn,
    )
    return map_nhl_puck_line_decision(decision)
