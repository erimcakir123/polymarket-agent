"""Resolved-market exit — fiyat ≤0.03 (lost) veya ≥0.97 (won) ise pozisyon kapat.

Polymarket tenis maçı bittiğinde fiyat doğal olarak 0¢ veya 100¢'e yapışır.
Önceki davranış: graduated_sl tetikleniyordu → reason="graduated_sl" yanıltıcı,
çünkü gerçek stop-loss değil, doğal maç bitişi. RESOLVED ayrı reason'la net
ayrım sağlar (dashboard "Maç Bitti" göstergesi + audit log doğru).

Tüm exit rule'lardan ÖNCE çalışır (monitor.py dispatch sırasında highest
priority). Pure: pos dışında bağımlılık yok.

2026-05-26 zakharo-muchova bugfix: WS feed thin-book transient `current_price=0.01`
tek tick'te resolved tetikledi → $19.29 yanlış kapanış (market closed=False,
outcomePrices_YES=0.49). Fix: extreme price (≤0.03 / ≥0.97) için EITHER
authoritative match_ended flag OR sustained N tick (consecutive_down_cycles)
gereklidir. Single-tick spike artık yutulmuyor.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.models.position import Position

# Resolve thresholds — Polymarket settled market'lerde fiyat genelde tam 0.00
# veya 1.00, ama market yapımcısı bid likiditesi nedeniyle ufak sapmalar olur.
# 3¢ / 97¢ aralığı pre-settled "almost there" durumu için güvenli marj.
LOST_THRESHOLD = 0.03
WON_THRESHOLD = 0.97

# 2026-05-26 zakharo bug: WS thin-book transient 0.01 spike tek tick'te resolved
# tetikliyordu. Authoritative match_ended flag YOKKEN extreme fiyatın gerçek
# settled olduğundan emin olmak için ardışık tick sayısı şart.
# 3 = tennis light-cycle ~15-20sn → ~45-60sn sürdürülmüş extreme.
MIN_SUSTAINED_TICKS = 3


@dataclass
class ResolvedSignal:
    """Exit kararı: reason=RESOLVED, full exit (sell_pct=1.0), detail won/lost."""
    sell_pct: float = 1.0
    detail: str = ""


def check(pos: Position) -> ResolvedSignal | None:
    """Pozisyon resolved sayılıyor mu?

    Resolved sayılması için fiyat extreme aralıkta olmalı (≤0.03 veya ≥0.97)
    VE şu iki koşuldan EN AZ BİRİ:
      (a) pos.match_ended=True (authoritative maç-bitti flag), VEYA
      (b) consecutive_down_cycles ≥ MIN_SUSTAINED_TICKS (kalıcı extreme fiyat,
          transient WS spike değil).

    "won" tarafında (≥0.97) consecutive_down_cycles doğal olarak 0'dır
    (fiyat yükseliyor); bu durum için match_ended yoksa fiyatın peak_price'a
    eşit/yakın ve previous_cycle_price de >=WON_THRESHOLD olmalı (en az 2 tick
    yüksek). Pratik proxy: previous_cycle_price >= WON_THRESHOLD.

    Args:
        pos: Açık pozisyon (current_price token-native, owned-side fiyat).

    Returns:
        ResolvedSignal (full exit + "won"/"lost" detail) veya None.
    """
    px = pos.current_price

    # Authoritative flag varsa kısa devre.
    if pos.match_ended:
        if px <= LOST_THRESHOLD:
            return ResolvedSignal(sell_pct=1.0, detail=f"lost (price={px:.3f}, match_ended)")
        if px >= WON_THRESHOLD:
            return ResolvedSignal(sell_pct=1.0, detail=f"won (price={px:.3f}, match_ended)")
        return None

    # Flag yok → sustained tick guard.
    if px <= LOST_THRESHOLD:
        if pos.consecutive_down_cycles >= MIN_SUSTAINED_TICKS:
            return ResolvedSignal(
                sell_pct=1.0,
                detail=f"lost (price={px:.3f}, sustained {pos.consecutive_down_cycles} ticks)",
            )
        return None

    if px >= WON_THRESHOLD:
        # Won-tarafta consecutive_down_cycles=0; previous_cycle_price proxy'si kullan.
        if pos.previous_cycle_price >= WON_THRESHOLD:
            return ResolvedSignal(
                sell_pct=1.0,
                detail=f"won (price={px:.3f}, prev={pos.previous_cycle_price:.3f})",
            )
        return None

    return None
