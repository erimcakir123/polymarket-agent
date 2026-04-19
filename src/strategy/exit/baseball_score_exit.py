"""Baseball inning-based score exit (SPEC-010) — pure.

A-conf pozisyonlar icin FORCED exit kurallari. Tennis T1/T2 ve
hockey K1-K4 ile simetrik.

M1: Blowout — inning >= 7 AND deficit >= 5
M2: Late big deficit — inning >= 8 AND deficit >= 3
M3: Final inning — inning >= 9 AND deficit >= 1

deficit = opp_score - our_score (pozitif = gerideyiz)
Esikler sport_rules.py config'inden (magic number yok).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason

_INNING_RE = re.compile(r"(\d+)(?:st|nd|rd|th)")


@dataclass
class BaseballExitResult:
    """Baseball exit sonucu — monitor.py ExitSignal'a cevirir."""

    reason: ExitReason
    detail: str


def check(
    score_info: dict,
    current_price: float,
    sport_tag: str = "mlb",
) -> BaseballExitResult | None:
    """Baseball M1/M2/M3 exit kontrolu.

    Args:
        score_info: score_enricher'dan gelen dict (available, period, deficit, ...)
        current_price: pozisyonun o anki fiyati
        sport_tag: "mlb", "kbo", "npb", "baseball" — config lookup icin

    Returns:
        BaseballExitResult → cik; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    period = score_info.get("period", "")
    inning = _parse_inning(period)
    if inning is None:
        return None

    deficit = score_info.get("deficit", 0)
    if deficit <= 0:
        return None  # onde veya esit

    # Config thresholds (sport_rules.py)
    m1_inning = int(get_sport_rule(sport_tag, "score_exit_m1_inning", 7))
    m1_deficit = int(get_sport_rule(sport_tag, "score_exit_m1_deficit", 5))
    m2_inning = int(get_sport_rule(sport_tag, "score_exit_m2_inning", 8))
    m2_deficit = int(get_sport_rule(sport_tag, "score_exit_m2_deficit", 3))
    m3_inning = int(get_sport_rule(sport_tag, "score_exit_m3_inning", 9))
    m3_deficit = int(get_sport_rule(sport_tag, "score_exit_m3_deficit", 1))

    # M1: blowout
    if inning >= m1_inning and deficit >= m1_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M1: inning={inning} deficit={deficit} threshold={m1_deficit}",
        )

    # M2: late big deficit
    if inning >= m2_inning and deficit >= m2_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M2: inning={inning} deficit={deficit} threshold={m2_deficit}",
        )

    # M3: final inning, any deficit
    if inning >= m3_inning and deficit >= m3_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M3: inning={inning} deficit={deficit} threshold={m3_deficit}",
        )

    return None


def _parse_inning(period: str) -> int | None:
    """ESPN period stringinden inning numarasi.

    "Top 1st" → 1, "Bot 5th" → 5, "Mid 9th" → 9, "Top 11th" → 11.
    Parse edilemezse None.
    """
    if not period:
        return None
    m = _INNING_RE.search(period)
    return int(m.group(1)) if m else None
