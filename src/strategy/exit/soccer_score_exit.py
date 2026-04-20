"""Soccer score exit (SPEC-015).

HOME/AWAY position:
- 0-65' HOLD (comeback potential)
- 65'+ 2 gol geride → EXIT
- 75'+ 1 gol geride → EXIT

DRAW position:
- 0-70' 0-0 → HOLD (draw değeri zirvede)
- 75'+ herhangi gol atıldı → EXIT
- Knockout maç + 90+stoppage → AUTO-EXIT (uzatma+pen draw'ı bitirir)

Sport config'ten okur (DRY — diğer 3-way sporlara uyarlanır).
Pure function, no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_configs import get_sport_config
from src.models.enums import ExitReason


@dataclass
class SoccerExitResult:
    reason: ExitReason
    detail: str


def check(score_info: dict, sport_tag: str = "soccer") -> SoccerExitResult | None:
    """Soccer score exit kontrolu. None → HOLD."""
    if not score_info.get("available"):
        return None

    minute = score_info.get("minute")
    if not isinstance(minute, int) or minute < 0:
        return None

    state = score_info.get("regulation_state", "")
    if state in ("pre", ""):
        return None

    cfg = get_sport_config(sport_tag) or {}
    if not cfg:
        return None

    our_outcome = score_info.get("our_outcome", "")
    home_score = int(score_info.get("home_score", 0))
    away_score = int(score_info.get("away_score", 0))
    knockout = bool(score_info.get("knockout", False))

    # ── DRAW position ──
    if our_outcome == "draw":
        reg_minutes = cfg.get("regulation_minutes", 90)
        if (
            knockout
            and minute >= reg_minutes
            and cfg.get("knockout_auto_exit_draw")
        ):
            return SoccerExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"draw_knockout_auto: minute={minute}",
            )
        any_goal = home_score > 0 or away_score > 0
        if any_goal and minute >= cfg.get("draw_exit_after_goal", 75):
            return SoccerExitResult(
                reason=ExitReason.SCORE_EXIT,
                detail=f"draw_goal_late: minute={minute} score={home_score}-{away_score}",
            )
        return None

    # ── HOME/AWAY position ──
    if our_outcome not in ("home", "away"):
        return None

    if our_outcome == "home":
        deficit = away_score - home_score
    else:
        deficit = home_score - away_score

    if deficit <= 0:
        return None

    first_half_lock = cfg.get("score_exit_first_half_lock", 65)
    if minute < first_half_lock:
        return None

    two_goal_min = cfg.get("score_exit_2goal_minute", 65)
    one_goal_min = cfg.get("score_exit_1goal_minute", 75)

    if minute >= two_goal_min and deficit >= 2:
        return SoccerExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"2_goal_deficit: minute={minute} deficit={deficit}",
        )

    if minute >= one_goal_min and deficit >= 1:
        return SoccerExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"1_goal_deficit: minute={minute} deficit={deficit}",
        )

    return None
