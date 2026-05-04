"""Logger and table-loader helpers — extracted from factory.py to honour 400-line cap.

Provides:
- build_trade_logger / build_equity_logger / build_archive_logger:
  dual-write paths (permanent audit + reboot-clearable session).
- load_nhl_*_table: thin fallback wrappers around NHL repository loaders.
"""
from __future__ import annotations

import logging

from src.infrastructure.persistence.archive_logger import ArchiveLogger
from src.infrastructure.persistence.equity_history import EquityHistoryLogger
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.infrastructure.repositories.nhl_puck_line_repository import load_table as _nhl_puck_line_raw
from src.infrastructure.repositories.nhl_totals_repository import load_table as _nhl_totals_raw
from src.infrastructure.repositories.nhl_wp_repository import load_table as _nhl_wp_raw

_log = logging.getLogger(__name__)

_AUDIT = "logs/audit"
_SESSION = "logs/session"


def build_trade_logger() -> TradeHistoryLogger:
    return TradeHistoryLogger(
        f"{_AUDIT}/trade_history.jsonl",
        mirror_path=f"{_SESSION}/trade_history.jsonl",
    )


def build_equity_logger() -> EquityHistoryLogger:
    return EquityHistoryLogger(
        f"{_AUDIT}/equity_history.jsonl",
        mirror_path=f"{_SESSION}/equity_history.jsonl",
    )


def build_archive_logger() -> ArchiveLogger:
    return ArchiveLogger(
        _AUDIT,
        mirror_dir=_SESSION,
    )


def load_nhl_wp_table() -> dict:
    try:
        return _nhl_wp_raw()
    except FileNotFoundError:
        _log.warning("NHL WP table not found at data/nhl_empirical_win_table.json — predictive exit disabled")
        return {}


def load_nhl_puck_line_table() -> dict:
    try:
        return _nhl_puck_line_raw()
    except FileNotFoundError:
        _log.warning("NHL puck line table not found at data/nhl_empirical_puck_line_table.json — Skellam fallback only")
        return {}


def load_nhl_totals_table() -> dict:
    try:
        return _nhl_totals_raw()
    except FileNotFoundError:
        _log.warning("NHL totals table not found at data/nhl_empirical_totals_table.json — Poisson fallback only")
        return {}
