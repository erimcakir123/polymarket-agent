"""Logger helpers — extracted from factory.py to honour 400-line cap.

3-tier dual-write:
- audit/  → kalıcı (reboot dokunmaz, ground truth)
- session/ → reboot mirror (dashboard kaynağı, reboot temizler)

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
    """SPEC-Z17: append-only event log — tek truth kaynağı."""
    return TradeEventLog(
        f"{_AUDIT}/trade_events.jsonl",
        mirror_path=f"{_SESSION}/trade_events.jsonl",
    )


def build_equity_logger() -> EquityHistoryLogger:
    return EquityHistoryLogger(
        f"{_AUDIT}/equity_history.jsonl",
        mirror_path=f"{_SESSION}/equity_history.jsonl",
    )


def build_archive_logger() -> ArchiveLogger:
    return ArchiveLogger(_AUDIT, mirror_dir=_SESSION)
