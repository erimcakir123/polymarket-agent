"""NFL score exit (SPEC-A3 + SPEC-A4).

N1 — Q3 sonu + 2.5-skor farkı (elapsed≥0.75 + 17+ sayı; SPEC-A4: 21→17)
N2 — Son 5 dakika + 2-possession (elapsed≥0.92 + 9+ sayı; SPEC-A4: 11→9)
N3 — Son 2.5 dakika + one-score (period==4 + clock≤150 + 4+ sayı; SPEC-A4 yeni tier)

Öncelik: N3 > N2 > N1 (en spesifik önce).

Pure fonksiyon: I/O yok, tüm veri parametre olarak gelir. Tüm threshold'lar
sport_rules.py config'inden okunur (magic number yok).

score_info opsiyonel olarak `period` + `clock_seconds` içerebilir (SPEC-A4).
Yoksa N3 skip edilir, N1/N2 elapsed_pct ile çalışmaya devam eder (backward compat).

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
    """NFL N1/N2/N3 exit kontrolü.

    Returns:
        NFLExitResult → çık; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    deficit = int(score_info.get("deficit", 0))
    if deficit <= 0:
        return None

    n1_elapsed = float(get_sport_rule(sport_tag, "score_exit_n1_elapsed", 0.75))
    n1_deficit = int(get_sport_rule(sport_tag, "score_exit_n1_deficit", 17))
    n2_elapsed = float(get_sport_rule(sport_tag, "score_exit_n2_elapsed", 0.92))
    n2_deficit = int(get_sport_rule(sport_tag, "score_exit_n2_deficit", 9))
    n3_clock = int(get_sport_rule(sport_tag, "score_exit_n3_clock_seconds", 150))
    n3_deficit = int(get_sport_rule(sport_tag, "score_exit_n3_deficit", 4))

    # N3 önce (en spesifik — period==4 + clock≤threshold + one-score+)
    period_number = score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    if (
        period_number == 4
        and clock_seconds is not None
        and int(clock_seconds) <= n3_clock
        and deficit >= n3_deficit
    ):
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N3: deficit={deficit} + Q4 clock={clock_seconds}s",
        )

    # N2 (son 5dk + 2-possession)
    if elapsed_pct >= n2_elapsed and deficit >= n2_deficit:
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    # N1 (Q3 sonu + 2.5-skor)
    if elapsed_pct >= n1_elapsed and deficit >= n1_deficit:
        return NFLExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N1: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
