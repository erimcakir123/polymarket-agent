"""Match start/finish heuristics for entry gate.

Sport-aware: maç tahmini bitti mi (sport duration + tampon)?
Score data gerektirmez — sadece match_start_iso + sport_tag yeterli.
Kullanıcı: gate.run() entry-time finish check (production'da bitmiş maça
girişi engeller; instant-exit pattern'ini kapatır).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.config.sport_rules import get_match_duration_hours

# Tipik maç süresi sonrası tampon (overtime + Polymarket çözüm gecikme +
# saat senkron drift için). 30 dakika makul minimum.
_FINISH_BUFFER_HOURS: float = 0.5


def is_match_likely_finished(match_start_iso: str, sport_tag: str) -> tuple[bool, str]:
    """Sport-aware heuristic: maç bitmiş olabilir mi?

    Returns:
        (finished, reason). reason debug için detail string ("" → check skipped).
    """
    if not match_start_iso:
        return False, ""
    try:
        start = datetime.fromisoformat(match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False, ""
    hours_since_start = (datetime.now(timezone.utc) - start).total_seconds() / 3600.0
    duration = get_match_duration_hours(sport_tag)
    threshold = duration + _FINISH_BUFFER_HOURS
    if hours_since_start > threshold:
        return True, f"hours_since_start={hours_since_start:.2f} > threshold={threshold:.2f}"
    return False, ""
