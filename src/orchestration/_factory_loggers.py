"""Logger helpers — extracted from factory.py to honour 400-line cap.

SPEC-Z18 (2026-06-05): trade_events + equity_history artık TEK dosya (audit/),
session aynası yok. Reboot dosyayı arşive taşır → dashboard 0. Çift kopya
ayrışması (audit=4 vs session=113) imkânsız. session mirror yalnızca
ArchiveLogger (score_events/match_results) için kaldı.

SPEC-Z17 (2026-06-04): legacy build_trade_logger kaldırıldı — tek truth
trade_events.jsonl event log.
"""
from __future__ import annotations

from src.infrastructure.persistence.archive_logger import ArchiveLogger
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.trade_event_log import TradeEventLog

_AUDIT = "logs/audit"
_SESSION = "logs/session"


def build_trade_event_log() -> TradeEventLog:
    """SPEC-Z18: append-only event log — tek dosya, tek truth (mirror yok)."""
    return TradeEventLog(f"{_AUDIT}/trade_events.jsonl")


def build_equity_logger() -> EquityHistoryLogger:
    """SPEC-Z18: tek dosya equity log (mirror yok)."""
    return EquityHistoryLogger(f"{_AUDIT}/equity_history.jsonl")


def build_archive_logger() -> ArchiveLogger:
    return ArchiveLogger(_AUDIT, mirror_dir=_SESSION)
