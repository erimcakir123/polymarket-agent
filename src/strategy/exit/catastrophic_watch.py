"""Catastrophic watch — dead cat bounce detector (SPEC-004 K5).

Tüm sporlar ve tüm confidence seviyeleri için geçerli (universal safety net).
Pure fonksiyon: I/O yok.
Eşikler config'den okunur (ExitExtrasConfig).

Davranış:
  1. Fiyat < trigger → watch moduna gir
  2. Fiyat yükselirse → recovery_peak güncelle
  3. Fiyat recovery_peak'ten drop_pct+ düşerse → ÇIK (sahte toparlanma)
  4. Fiyat >= cancel → watch iptal (gerçek comeback)
"""
from __future__ import annotations

from dataclasses import dataclass

from src.models.enums import ExitReason
from src.models.position import Position


@dataclass
class CatastrophicExitResult:
    """Catastrophic watch sonucu — monitor.py ExitSignal'a çevirir."""

    reason: ExitReason
    detail: str


def tick(
    pos: Position,
    trigger: float,
    cancel: float,
) -> None:
    """Catastrophic watch state'i güncelle (her light cycle'da çağrılır).

    Mutates pos.catastrophic_watch ve pos.catastrophic_recovery_peak.
    """
    price = pos.current_price

    if not pos.catastrophic_watch:
        if price < trigger:
            pos.catastrophic_watch = True
            pos.catastrophic_recovery_peak = price
        return

    # Watch aktif
    if price >= cancel:
        # Gerçek comeback — iptal
        pos.catastrophic_watch = False
        pos.catastrophic_recovery_peak = 0.0
        return

    if price > pos.catastrophic_recovery_peak:
        pos.catastrophic_recovery_peak = price


def check(
    pos: Position,
    trigger: float,
    drop_pct: float,
) -> CatastrophicExitResult | None:
    """Catastrophic bounce exit kontrolü.

    tick() çağrıldıktan SONRA çağrılmalı (state güncel olmalı).

    Returns:
        ExitSignal → çık (bounce + drop pattern); None → tetiklenmedi.
    """
    if not pos.catastrophic_watch:
        return None

    peak = pos.catastrophic_recovery_peak
    price = pos.current_price

    # Peak trigger'ın üstüne çıkmış olmalı (en az bir bounce oldu)
    if peak <= trigger:
        return None

    # Peak'ten drop_pct+ düştü mü?
    if price < peak * (1.0 - drop_pct):
        return CatastrophicExitResult(
            reason=ExitReason.CATASTROPHIC_BOUNCE,
            detail=f"K5: peak={peak:.3f} now={price:.3f} drop={1 - price / peak:.0%}",
        )

    return None
