"""Flat stop-loss helper — 6-katman öncelik (TDD §6.7).

Tek kaynak: hem WebSocket path (exit_monitor._ws_check_exits) hem light cycle
(monitor.py) buradan çağırır.

Katmanlar (öncelik sırasına göre):
  1. Stale price skip (WS tick gelmedi → fake -100% PnL)
  2. Totals/spread skip (hold to resolution, SL yok)
  3. Ultra-low entry (eff < 9¢) → geniş %50 SL
  4. Low-entry graduated (9-20¢) → linear %60 → %40
  5. Sport-specific SL (sport_rules.py)
  6. Lossy reentry çarpanı (×0.75)
"""
from __future__ import annotations

import re

from src.config.sport_rules import get_sport_rule, get_stop_loss
from src.models.position import Position

_ULTRA_LOW_THRESHOLD = 0.09
_LOW_ENTRY_UPPER = 0.20
_LOW_ENTRY_SL_HIGH = 0.60
_LOW_ENTRY_SL_LOW = 0.40
_REENTRY_MULT = 0.75
_TOTALS_KEYWORDS = ("o/u", "total", "spread")
_INNING_RE = re.compile(r"(\d+)(?:st|nd|rd|th)")


def parse_baseball_inning(period: str) -> int | None:
    """ESPN period string'inden inning numarası çıkar.

    "Top 1st" → 1, "Bot 5th" → 5, "Mid 9th" → 9.
    Parse edilemezse None döner.
    """
    if not period:
        return None
    m = _INNING_RE.search(period)
    return int(m.group(1)) if m else None


def is_baseball_alive(inning: int, deficit: int) -> bool:
    """Canlılık matrisi — maç hala kazanılabilir mi?

    True=canlı (SL devre dışı), False=ölü (SL aktif).
    deficit = opp_score - our_score (pozitif = gerideyiz).
    """
    if deficit <= 0:
        return True

    thresholds: dict[int, int] = get_sport_rule("mlb", "comeback_thresholds", {})
    extra_thresh: int = get_sport_rule("mlb", "extra_inning_threshold", 1)

    if inning > 9:
        return deficit < extra_thresh

    for max_inning in sorted(thresholds):
        if inning <= max_inning:
            return deficit < thresholds[max_inning]

    return deficit < extra_thresh


def compute_stop_loss_pct(pos: Position) -> float | None:
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

    # 6. Lossy reentry çarpanı
    if pos.sl_reentry_count >= 1:
        sl *= _REENTRY_MULT

    return sl


def check(pos: Position) -> bool:
    """Flat SL tetiklendi mi? True → exit sinyali.

    unrealized_pnl_pct < -sl_pct tetikler. None sl_pct → False (muaf).
    """
    sl = compute_stop_loss_pct(pos)
    if sl is None:
        return False
    return pos.unrealized_pnl_pct < -sl
