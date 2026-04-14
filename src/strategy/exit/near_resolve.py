"""Near-resolve profit exit (TDD §6.11) — eff ≥ 94¢ → çık (pure).

Polymarket'te near-resolve en büyük kâr kaynağı (v1 verisi: 27 trade = +$140.31, 93% WR).

Sanity guard: pre-match veya just-started (< 5 dk) pozisyonlar için WS spike'ına
karşı reddet (açılışta bazen 0.00 veya 1.00 gelir).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.models.position import Position, effective_price

DEFAULT_THRESHOLD_CENTS = 94
DEFAULT_PRE_MATCH_GUARD_MIN = 10  # İlk 10dk'da 94¢ = WS spike (MVP sporlarında imkansız)


def check(
    pos: Position,
    threshold_cents: int = DEFAULT_THRESHOLD_CENTS,
    pre_match_guard_minutes: int = DEFAULT_PRE_MATCH_GUARD_MIN,
) -> bool:
    """Near-resolve exit tetiklendi mi?

    eff_current ≥ threshold AND pozisyon yeterince eski (guard). Guard sanity'yi
    sağlar: maç daha başlamadıysa veya yeni başladıysa (< 5dk) spike olabilir.
    """
    eff_current = effective_price(pos.current_price, pos.direction)
    threshold = threshold_cents / 100.0

    if eff_current < threshold:
        return False

    # Sanity: match_start_iso var mı ve >=5 dk geçti mi?
    if not pos.match_start_iso:
        # Bilinmiyorsa güven ver — threshold yüksek zaten
        return True

    try:
        start_dt = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return True  # Bozuk tarih → yine güven

    now = datetime.now(timezone.utc)
    # Pre-match: maç henüz başlamadı → reddet
    if now < start_dt:
        return False
    # Just-started: ilk 5 dk → WS spike riski
    minutes_since_start = (now - start_dt).total_seconds() / 60.0
    if minutes_since_start < pre_match_guard_minutes:
        return False

    return True
