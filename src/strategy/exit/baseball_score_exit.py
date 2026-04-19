"""Baseball score exit (MLB/KBO/NPB) — SPEC-010 + SPEC-014.

M1: Late-inning big deficit (blowout)
M2: Mid-late inning deficit
M3: Final inning any deficit

Tum threshold'lar sport_rules.py config'inden (magic number yok).
SPEC-014: inning artik score_info['inning'] int olarak gelir — ESPN
status.period'dan parse edilmis. Regex-based _parse_inning olu kod.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule
from src.models.enums import ExitReason


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
        score_info: score_enricher'dan gelen dict — 'inning' int field'i zorunlu (SPEC-014).
        current_price: pozisyonun o anki fiyati
        sport_tag: "mlb", "kbo", "npb", "baseball" — config lookup icin

    Returns:
        BaseballExitResult → cik; None → tetiklenmedi.
    """
    if not score_info.get("available"):
        return None

    inning = score_info.get("inning")
    if not isinstance(inning, int) or inning <= 0:
        return None

    home_score = int(score_info.get("home_score", 0))
    away_score = int(score_info.get("away_score", 0))
    our_is_home = bool(score_info.get("our_is_home", False))

    if our_is_home:
        deficit = away_score - home_score
    else:
        deficit = home_score - away_score

    # Fallback: enricher 'deficit' alanini dogrudan saglar — our_is_home olmadan da calisir
    if home_score == 0 and away_score == 0:
        deficit = int(score_info.get("deficit", 0))

    if deficit <= 0:
        return None

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
            detail=f"M1: inn={inning} deficit={deficit} threshold={m1_deficit}",
        )

    # M2: late big deficit
    if inning >= m2_inning and deficit >= m2_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M2: inn={inning} deficit={deficit} threshold={m2_deficit}",
        )

    # M3: final inning, any deficit
    if inning >= m3_inning and deficit >= m3_deficit:
        return BaseballExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"M3: inn={inning} deficit={deficit} threshold={m3_deficit}",
        )

    return None
