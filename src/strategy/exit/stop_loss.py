"""Flat stop-loss helper — 4-katman öncelik (DECISIONS §6.7).

Tek kaynak: hem WebSocket path (exit_monitor._ws_check_exits) hem light cycle
(monitor.py) buradan çağırır.

Katmanlar (öncelik sırasına göre):
  1. Stale price skip (WS tick gelmedi → fake -100% PnL)
  2. Ultra-low entry (eff < 9¢) → geniş %50 SL
  3. Low-entry graduated (9-20¢) → linear %60 → %40
  4. Sport-specific SL (sport_rules.py)

SPEC-V (2026-05-23): Totals/spread muafiyeti KALDIRILDI. Tüm market türlerinde
SL aktif — anlık çakılma riski bimodal sizing cap'i ile sınırlanır (SPEC-U).
"""
from __future__ import annotations

from src.config.sport_rules import get_stop_loss, is_bimodal_market
from src.models.position import Position

_ULTRA_LOW_THRESHOLD = 0.09
_LOW_ENTRY_UPPER = 0.20
_LOW_ENTRY_SL_HIGH = 0.60
_LOW_ENTRY_SL_LOW = 0.40


def compute_stop_loss_pct(pos: Position) -> float | None:
    """Pozisyon için doğru SL yüzdesini hesapla.

    Returns:
        float: SL yüzdesi (örn. 0.30 = %30).
        None: bu pozisyonda flat SL UYGULANMAZ (sadece stale price).
    """
    # 1. Stale price — WS tick hiç gelmemiş gibi
    if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
        return None

    # 2. Bimodal market'ler flat SL'den MUAF (2026-05-31 fix).
    # Set bittiğinde fiyat 99¢/1¢ sıçrar — %50 SL fire eder, bot satar, sonra
    # fiyat geri uçar → kâr kaybedilir. Tennis-paper-lab raporu pattern.
    # Graduated SL (low entry) ve sport-level kontrol AKTİF KALIR; flat SL kapanır.
    market_type = ""
    smt = getattr(pos, "sports_market_type", None)
    if smt is not None:
        market_type = getattr(smt, "value", None) or str(smt)
    if is_bimodal_market(pos.sport_tag or "", market_type):
        return None

    # 2.5. Hold-to-resolve (2026-05-31 Adım 2): tennis için yüksek-güven
    # pozisyonları SL muaf. Kullanıcı verisi: anchor < %30 deep dog'lar
    # %81 doğru çıkıyor AMA SL fire → tahmin paraya çevrilmiyor.
    # Eşik: |anchor - 0.50| > 0.20 → güvenli → resolve'a tut.
    if (pos.sport_tag or "").lower() == "tennis":
        anchor = pos.anchor_probability or 0.50
        if abs(anchor - 0.50) > 0.20:
            return None

    # entry_price zaten token-native (owned side).
    eff_entry = pos.entry_price

    # 3. Ultra-low entry — geniş %50 SL
    if eff_entry < _ULTRA_LOW_THRESHOLD:
        sl = 0.50
    elif eff_entry < _LOW_ENTRY_UPPER:
        # 4. Low-entry graduated: 9¢ → %60, 20¢ → %40 linear
        t = (eff_entry - _ULTRA_LOW_THRESHOLD) / (_LOW_ENTRY_UPPER - _ULTRA_LOW_THRESHOLD)
        sl = _LOW_ENTRY_SL_HIGH - t * (_LOW_ENTRY_SL_HIGH - _LOW_ENTRY_SL_LOW)
    else:
        # 5. Sport-specific SL
        sl = get_stop_loss(pos.sport_tag)

    return sl


def check(pos: Position) -> bool:
    """Flat SL tetiklendi mi? True → exit sinyali.

    unrealized_pnl_pct < -sl_pct tetikler. None sl_pct → False (muaf).
    """
    sl = compute_stop_loss_pct(pos)
    if sl is None:
        return False
    return pos.unrealized_pnl_pct < -sl
