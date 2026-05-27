"""Force-close strategy — kayıp pozisyonların maç bittikten sonra zorla kapatılması.

Pure decision module — I/O yok, sadece state + ESPN status + zaman -> signal.
Implementation entegrasyonu exit_processor.py'da (Task 6).

Karar mantığı (hybrid):
  1. ESPN says event ended (set bitti / match final) -> signal
  2. ESPN cevap yok / event bulunamadı -> elapsed time check
  3. elapsed > timeouts[market_type] (veya default) -> signal
  4. Hiçbiri yoksa -> None (normal exit chain devam)

SPEC: docs/superpowers/specs/2026-05-27-force-close-design.md
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping

from src.models.match_status import MatchStatus
from src.models.position import Position

logger = logging.getLogger(__name__)

ForceCloseReason = Literal["espn_event_ended", "time_expired"]


@dataclass(frozen=True)
class ForceCloseSignal:
    """Force-close tetiklendi — exit_processor slippage-bypass satışı çalıştırır."""
    reason: ForceCloseReason


def check(
    pos: Position,
    espn_status: MatchStatus | None,
    now: datetime,
    timeouts: Mapping[str, int],
    market_type: str,
) -> ForceCloseSignal | None:
    """Pozisyon için force-close sinyali üret — None = sinyal yok."""
    # 1. ESPN-first: bu market_type'ın olayı bittiyse hemen sinyal
    if espn_status is not None and _espn_indicates_event_done(espn_status, market_type):
        return ForceCloseSignal(reason="espn_event_ended")

    # 2. Time-based fallback
    if not pos.match_start_iso:
        return None

    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except ValueError:
        # Bozuk match_start_iso — force-close kararı veremeyiz; gözlemlenebilir hata.
        logger.warning(
            "force_close: invalid match_start_iso=%r (token=%s, slug=%s)",
            pos.match_start_iso, pos.token_id, pos.slug,
        )
        return None

    elapsed_min = (now - start).total_seconds() / 60
    # I1 fix: explicit `is None` — `timeouts.get(...) or` kabul edilemez çünkü
    # 0 falsy → "default'a düş" yanlış davranış (intent: "anında force-close").
    timeout_min = timeouts.get(market_type)
    if timeout_min is None:
        timeout_min = timeouts.get("default")
    if timeout_min is None:
        return None
    if elapsed_min > timeout_min:
        return ForceCloseSignal(reason="time_expired")
    return None


def _espn_indicates_event_done(status: MatchStatus, market_type: str) -> bool:
    """Market_type için ilgili period/match bitmiş mi?

    Period-based markets (e.g. tennis_first_set_winner): cari period >=2 yeterli.
    Match-level markets (e.g. tennis_match_winner): completed=True gerek.
    """
    if status.is_completed:
        return True
    # First-set / set-N specific markets: o setin bitmiş olduğu = period > 1
    if "first_set" in market_type and status.period is not None and status.period >= 2:
        return True
    # Quarter-based extension: q1 winner için period >= 2 (NBA/NFL)
    if "_quarter_1" in market_type and status.period is not None and status.period >= 2:
        return True
    return False
