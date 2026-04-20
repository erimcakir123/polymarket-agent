"""NBA score exit (SPEC-A3 + SPEC-A4).

N1 — Late game + ağır fark (Q3 sonu + 18+ sayı; SPEC-A4: 20→18)
N2 — Son 4 dakika + anlamlı fark (elapsed≥0.92 + 8+ sayı; SPEC-A4: 10→8)
N3 — Son 2 dakika + one-score+ (period==4 + clock≤120 + 5+ sayı; SPEC-A4 yeni tier)

Öncelik: N3 > N2 > N1 (en spesifik önce).

Pure fonksiyon: I/O yok, tüm veri parametre olarak gelir. Tüm threshold'lar
sport_rules.py config'inden okunur (magic number yok).

score_info opsiyonel olarak `period` + `clock_seconds` içerebilir (SPEC-A4).
Yoksa N3 skip edilir, N1/N2 elapsed_pct ile çalışmaya devam eder (backward compat).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


@dataclass
class NBAExitResult:
    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    elapsed_pct: float,
    sport_tag: str = "nba",
) -> NBAExitResult | None:
    """NBA N1/N2/N3 exit kontrolü.

    Returns:
        NBAExitResult → çık; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    deficit = int(score_info.get("deficit", 0))
    if deficit <= 0:
        return None

    n1_elapsed = float(get_sport_rule(sport_tag, "score_exit_n1_elapsed", 0.75))
    n1_deficit = int(get_sport_rule(sport_tag, "score_exit_n1_deficit", 18))
    n2_elapsed = float(get_sport_rule(sport_tag, "score_exit_n2_elapsed", 0.92))
    n2_deficit = int(get_sport_rule(sport_tag, "score_exit_n2_deficit", 8))
    n3_clock = int(get_sport_rule(sport_tag, "score_exit_n3_clock_seconds", 120))
    n3_deficit = int(get_sport_rule(sport_tag, "score_exit_n3_deficit", 5))

    # N3 önce (en spesifik — period==4 + clock≤threshold + one-score+)
    period_number = score_info.get("period_number")
    clock_seconds = score_info.get("clock_seconds")
    if (
        period_number == 4
        and clock_seconds is not None
        and int(clock_seconds) <= n3_clock
        and deficit >= n3_deficit
    ):
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N3: deficit={deficit} + Q4 clock={clock_seconds}s",
        )

    # N2 (son 4dk + anlamlı fark)
    if elapsed_pct >= n2_elapsed and deficit >= n2_deficit:
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    # N1 (Q3 sonu + ağır fark)
    if elapsed_pct >= n1_elapsed and deficit >= n1_deficit:
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N1: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
