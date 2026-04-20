"""NFL score exit (score-only A3 spec).

N1 — Late game + 3-skor farkı (Q3 sonu + 21+ sayı = 3 touchdown)
N2 — Son dakikalar + 2-possession (son 5dk + 11+ sayı)

Pure fonksiyon: I/O yok. Tüm threshold'lar sport_rules.py config'inden.
Hockey K2/K4 simetrisinde. Erken fire etmez.

Overtime: elapsed 1.0'ı aşabilir. N2 gate'i aşıldığı için OT'de büyük deficit
→ fire eder (doğru davranış).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class NFLExitResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    elapsed_pct: float,
    sport_tag: str = "nfl",
) -> NFLExitResult | None:
    """NFL N1/N2 exit kontrolü."""
    if not score_info.get("available"):
        return None

    deficit = int(score_info.get("deficit", 0))
    if deficit <= 0:
        return None

    n1_elapsed = float(get_sport_rule(sport_tag, "score_exit_n1_elapsed", 0.75))
    n1_deficit = int(get_sport_rule(sport_tag, "score_exit_n1_deficit", 21))
    n2_elapsed = float(get_sport_rule(sport_tag, "score_exit_n2_elapsed", 0.92))
    n2_deficit = int(get_sport_rule(sport_tag, "score_exit_n2_deficit", 11))

    if elapsed_pct >= n2_elapsed and deficit >= n2_deficit:
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    if elapsed_pct >= n1_elapsed and deficit >= n1_deficit:
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N1: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
