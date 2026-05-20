"""Resolved-market exit — fiyat ≤0.03 (lost) veya ≥0.97 (won) ise pozisyon kapat.

Polymarket tenis maçı bittiğinde fiyat doğal olarak 0¢ veya 100¢'e yapışır.
Önceki davranış: graduated_sl tetikleniyordu → reason="graduated_sl" yanıltıcı,
çünkü gerçek stop-loss değil, doğal maç bitişi. RESOLVED ayrı reason'la net
ayrım sağlar (dashboard "Maç Bitti" göstergesi + audit log doğru).

Tüm exit rule'lardan ÖNCE çalışır (monitor.py dispatch sırasında highest
priority). Pure: pos dışında bağımlılık yok.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.models.enums import ExitReason
from src.models.position import Position

# Resolve thresholds — Polymarket settled market'lerde fiyat genelde tam 0.00
# veya 1.00, ama market yapımcısı bid likiditesi nedeniyle ufak sapmalar olur.
# 3¢ / 97¢ aralığı pre-settled "almost there" durumu için güvenli marj.
LOST_THRESHOLD = 0.03
WON_THRESHOLD = 0.97


@dataclass
class ResolvedSignal:
    """Exit kararı: reason=RESOLVED, full exit (sell_pct=1.0), detail won/lost."""
    sell_pct: float = 1.0
    detail: str = ""


def check(pos: Position) -> ResolvedSignal | None:
    """Pozisyon resolved sayılıyor mu?

    Args:
        pos: Açık pozisyon (current_price token-native, owned-side fiyat).

    Returns:
        ResolvedSignal (full exit + "won"/"lost" detail) veya None (normal range).
    """
    if pos.current_price <= LOST_THRESHOLD:
        return ResolvedSignal(sell_pct=1.0, detail=f"lost (price={pos.current_price:.3f})")
    if pos.current_price >= WON_THRESHOLD:
        return ResolvedSignal(sell_pct=1.0, detail=f"won (price={pos.current_price:.3f})")
    return None
