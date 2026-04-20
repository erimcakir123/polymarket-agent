"""NBA score exit (score-only A3 spec).

N1 — Late game + ağır fark (Q3 sonu + 20+ sayı)
N2 — Son dakikalar + iki possession (son 4dk + 10+ sayı)

Pure fonksiyon: I/O yok, tüm veri parametre olarak gelir. Tüm threshold'lar
sport_rules.py config'inden okunur (magic number yok).

Hockey K2/K4 simetrisinde: geç maç + insurmountable deficit. Erken fire etmez.
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
    """NBA N1/N2 exit kontrolü.

    Returns:
        NBAExitResult → çık; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    deficit = int(score_info.get("deficit", 0))
    if deficit <= 0:
        return None

    n1_elapsed = float(get_sport_rule(sport_tag, "score_exit_n1_elapsed", 0.75))
    n1_deficit = int(get_sport_rule(sport_tag, "score_exit_n1_deficit", 20))
    n2_elapsed = float(get_sport_rule(sport_tag, "score_exit_n2_elapsed", 0.92))
    n2_deficit = int(get_sport_rule(sport_tag, "score_exit_n2_deficit", 10))

    # N2 önce (daha geç + daha küçük deficit gerektirir)
    if elapsed_pct >= n2_elapsed and deficit >= n2_deficit:
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    if elapsed_pct >= n1_elapsed and deficit >= n1_deficit:
        return NBAExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"N1: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
