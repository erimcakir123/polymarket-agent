"""Flat stop-loss helper — 7-katman öncelik (TDD §6.7, v2 MVP).

Tek kaynak: hem WebSocket path (exit_monitor._ws_check_exits) hem light cycle
(monitor.py) buradan çağırır.

Katmanlar (öncelik sırasına göre):
  1. Stale price skip (WS tick gelmedi → fake -100% PnL)
  2. Totals/spread skip (hold to resolution, SL yok)
  3. Volatility swing → vs_sl_pct
  4. Ultra-low entry (eff < 9¢) → geniş %50 SL
  5. Low-entry graduated (9-20¢) → linear %60 → %40
  6. Sport-specific SL (sport_rules.py)
  7. Lossy reentry çarpanı (×0.75)

v2 değişiklikleri (eski v1'den):
  - B- confidence katmanı YOK (v2 sadece A/B)
  - Esports BO5+ bonus YOK (MVP dışı)
  - scouted kavramı YOK
"""
from __future__ import annotations

from src.config.sport_rules import get_stop_loss
from src.models.position import Position, effective_price

_ULTRA_LOW_THRESHOLD = 0.09
_LOW_ENTRY_UPPER = 0.20
_LOW_ENTRY_SL_HIGH = 0.60
_LOW_ENTRY_SL_LOW = 0.40
_REENTRY_MULT = 0.75
_TOTALS_KEYWORDS = ("o/u", "total", "spread")


def compute_stop_loss_pct(
    pos: Position,
    vs_sl_pct: float = 0.20,
) -> float | None:
    """Pozisyon için doğru SL yüzdesini hesapla.

    Returns:
        float: SL yüzdesi (örn. 0.30 = %30).
        None: bu pozisyonda flat SL UYGULANMAZ (totals/spread veya stale price).
    """
    # 1. Stale price — WS tick hiç gelmemiş gibi
    if pos.current_price <= 0.001 and pos.current_price != pos.entry_price:
        return None

    # 2. Totals/spread — hold to resolution
    q = (pos.question or "").lower()
    slug = (pos.slug or "").lower()
    if any(k in q or k in slug for k in _TOTALS_KEYWORDS):
        return None

    # 3. Volatility swing → kendi SL'si
    if pos.volatility_swing:
        sl = vs_sl_pct
        if pos.sl_reentry_count >= 1:
            sl *= _REENTRY_MULT
        return sl

    eff_entry = effective_price(pos.entry_price, pos.direction)

    # 4. Ultra-low entry — geniş %50 SL
    if eff_entry < _ULTRA_LOW_THRESHOLD:
        sl = 0.50
    elif eff_entry < _LOW_ENTRY_UPPER:
        # 5. Low-entry graduated: 9¢ → %60, 20¢ → %40 linear
        t = (eff_entry - _ULTRA_LOW_THRESHOLD) / (_LOW_ENTRY_UPPER - _ULTRA_LOW_THRESHOLD)
        sl = _LOW_ENTRY_SL_HIGH - t * (_LOW_ENTRY_SL_HIGH - _LOW_ENTRY_SL_LOW)
    else:
        # 6. Sport-specific SL
        sl = get_stop_loss(pos.sport_tag)

    # 7. Lossy reentry çarpanı
    if pos.sl_reentry_count >= 1:
        sl *= _REENTRY_MULT

    return sl


def check(pos: Position, vs_sl_pct: float = 0.20) -> bool:
    """Flat SL tetiklendi mi? True → exit sinyali.

    unrealized_pnl_pct < -sl_pct tetikler. None sl_pct → False (muaf).
    """
    sl = compute_stop_loss_pct(pos, vs_sl_pct=vs_sl_pct)
    if sl is None:
        return False
    return pos.unrealized_pnl_pct < -sl
