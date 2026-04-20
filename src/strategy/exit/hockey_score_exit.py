"""Score-based exit for hockey — SPEC-004 K1-K4.

Pure fonksiyon: I/O yok, tüm veri parametre olarak gelir.
Hockey family (NHL + AHL) pozisyonları için geçerlidir.
Eşikler sport_rules.py config'inden okunur (magic number yok).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config.sport_rules import get_sport_rule, _normalize
from src.models.enums import ExitReason


@dataclass
class ScoreExitResult:
    """Score exit sonucu — monitor.py ExitSignal'a çevirir."""

    reason: ExitReason
    detail: str


_HOCKEY_FAMILY: frozenset[str] = frozenset({"nhl", "ahl"})


def _is_hockey_family(sport_tag: str) -> bool:
    """NHL + AHL — aynı K1-K4 kuralları (SPEC-014)."""
    return _normalize(sport_tag) in _HOCKEY_FAMILY


# Backward-compat alias — existing callers
_is_hockey = _is_hockey_family


def check(
    sport_tag: str,
    confidence: str,
    score_info: dict,
    elapsed_pct: float,
    current_price: float,
) -> ScoreExitResult | None:
    """Score-based exit kontrolü (K1-K4).

    Returns:
        ScoreExitResult → çık; None → skor kuralı tetiklenmedi.

    Kapsam: hockey family (NHL + AHL), tüm confidence seviyeleri.
    A-conf gate A3 unified flow'da kaldırıldı — confidence parametresi
    sinyatürde kalıyor (monitor.py hâlâ pas geçiyor).
    """
    if not _is_hockey(sport_tag):
        return None
    if not score_info.get("available"):
        return None

    deficit: int = score_info.get("deficit", 0)
    if deficit <= 0:
        return None  # skorda öndeyiz veya eşitiz

    # K1 — Ağır yenilgi: deficit >= period_exit_deficit (default 3)
    heavy_deficit = int(get_sport_rule(sport_tag, "period_exit_deficit", 3))
    if deficit >= heavy_deficit:
        return ScoreExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"K1: deficit={deficit} >= {heavy_deficit}",
        )

    # K2 — Geç maç dezavantajı: deficit >= late_deficit + elapsed >= gate
    late_deficit = int(get_sport_rule(sport_tag, "late_deficit", 2))
    late_gate = float(get_sport_rule(sport_tag, "late_elapsed_gate", 0.67))
    if deficit >= late_deficit and elapsed_pct >= late_gate:
        return ScoreExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"K2: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    # K3 — Skor + fiyat teyidi: deficit >= late_deficit + price < threshold
    price_confirm = float(get_sport_rule(sport_tag, "score_price_confirm", 0.35))
    if deficit >= late_deficit and current_price < price_confirm:
        return ScoreExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"K3: deficit={deficit} + price={current_price:.2f}",
        )

    # K4 — Son dakika: deficit >= 1 + elapsed >= final gate
    final_gate = float(get_sport_rule(sport_tag, "final_elapsed_gate", 0.92))
    if deficit >= 1 and elapsed_pct >= final_gate:
        return ScoreExitResult(
            reason=ExitReason.SCORE_EXIT,
            detail=f"K4: deficit={deficit} + elapsed={elapsed_pct:.0%}",
        )

    return None
