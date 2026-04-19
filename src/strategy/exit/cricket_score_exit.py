"""Cricket inning-based score exit (SPEC-011) — pure.

Tennis T1/T2 ve hockey K1-K4 ile simetrik. A-conf pozisyonlar icin
FORCED exit. Sadece 2. innings (chase) ve bizim chasing tarafimiz iken
C1/C2/C3 tetiklenir — defending tarafindaysak chase cokmek bizim lehimize.

C1: Matematiksel imkansiz chase
    balls_remaining < c1_balls AND required_run_rate > c1_rate

C2: Cok fazla wicket kaybi
    wickets_lost >= c2_wickets AND runs_remaining > c2_runs

C3: Son over'lar + uzak hedef
    balls_remaining < c3_balls AND runs_remaining > c3_runs

Tum threshold'lar sport_rules.py config'inden (magic number yok).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class CricketExitResult:
    """Cricket exit sonucu — monitor.py ExitSignal'a cevirir."""

    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "cricket_ipl",
) -> CricketExitResult | None:
    """Cricket C1/C2/C3 exit kontrolu.

    score_info beklenen format:
      {
        "available": True,
        "innings": 2,                  # 2 = chase, 1 = first innings
        "our_chasing": True,           # biz chase eden taraftayiz mi
        "balls_remaining": int,
        "runs_remaining": int,
        "wickets_lost": int,
        "required_run_rate": float,
      }

    1. innings VEYA available=False VEYA our_chasing=False → None (skip).
    """
    if not score_info.get("available"):
        return None

    if score_info.get("innings", 0) != 2:
        return None  # Sadece chase'te mantikli

    if not score_info.get("our_chasing", False):
        # Biz defending'iz — chase cokerse BIZ kazaniyoruz, exit yok
        return None

    balls_remaining = int(score_info.get("balls_remaining", 0))
    runs_remaining = int(score_info.get("runs_remaining", 0))
    wickets_lost = int(score_info.get("wickets_lost", 0))
    required_rate = float(score_info.get("required_run_rate", 0.0))

    if runs_remaining <= 0:
        return None  # Chase tamamlandi (kazandik)

    # Config thresholds
    c1_balls = int(get_sport_rule(sport_tag, "score_exit_c1_balls", 30))
    c1_rate = float(get_sport_rule(sport_tag, "score_exit_c1_rate", 18.0))
    c2_wickets = int(get_sport_rule(sport_tag, "score_exit_c2_wickets", 8))
    c2_runs = int(get_sport_rule(sport_tag, "score_exit_c2_runs", 20))
    c3_balls = int(get_sport_rule(sport_tag, "score_exit_c3_balls", 6))
    c3_runs = int(get_sport_rule(sport_tag, "score_exit_c3_runs", 10))

    # C1: Impossible RRR
    if balls_remaining < c1_balls and required_rate > c1_rate:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C1: balls_left={balls_remaining} rrr={required_rate:.1f} threshold={c1_rate}",
        )

    # C2: Too many wickets lost
    if wickets_lost >= c2_wickets and runs_remaining > c2_runs:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C2: wkts={wickets_lost} runs_left={runs_remaining} threshold={c2_runs}",
        )

    # C3: Final balls, big gap
    if balls_remaining < c3_balls and runs_remaining > c3_runs:
        return CricketExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"C3: balls_left={balls_remaining} runs_left={runs_remaining} threshold={c3_runs}",
        )

    return None
