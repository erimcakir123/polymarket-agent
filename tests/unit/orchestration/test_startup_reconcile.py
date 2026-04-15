"""Startup reconciliation — trade_history.jsonl vs portfolio snapshot uyumsuzluk düzeltimi."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.domain.portfolio.manager import PortfolioManager
from src.orchestration.startup import _reconcile_realized_pnl


def _make_logger_with_records(records: list[dict]) -> MagicMock:
    logger = MagicMock()
    logger.read_all.return_value = records
    return logger


def test_reconcile_no_change_when_snapshot_matches_log():
    """Snapshot ve log eşit ise dokunulmaz (delta < 0.01)."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -30.0
    pm.bankroll = 970.0
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.4, "exit_pnl_usdc": -30.0},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert pm.realized_pnl == -30.0
    assert pm.bankroll == 970.0


def test_reconcile_overrides_snapshot_when_log_differs():
    """Log -82, snapshot -46 → log kazanır, bankroll yeniden türetilir."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -46.0
    pm.bankroll = 954.0  # eski yanlış değer
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.27, "exit_pnl_usdc": -17.07, "partial_exits": []},
        {"exit_price": 0.27, "exit_pnl_usdc": -19.32, "partial_exits": []},
        {"exit_price": 0.34, "exit_pnl_usdc": -15.31, "partial_exits": []},
        {"exit_price": 0.29, "exit_pnl_usdc": -15.48, "partial_exits": []},
        {"exit_price": 0.41, "exit_pnl_usdc": -14.97, "partial_exits": []},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert abs(pm.realized_pnl - (-82.15)) < 0.01
    assert abs(pm.bankroll - (1000.0 - 82.15)) < 0.01  # invested=0


def test_reconcile_includes_partial_exits():
    """Partial exit'ler de toplama dahil."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = 0.0
    pm.bankroll = 1000.0
    trade_logger = _make_logger_with_records([
        {
            "exit_price": None,
            "exit_pnl_usdc": 0.0,
            "partial_exits": [
                {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0, "timestamp": "t1"},
                {"tier": 2, "sell_pct": 0.5, "realized_pnl_usdc": 8.0, "timestamp": "t2"},
            ],
        },
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert abs(pm.realized_pnl - 13.0) < 0.01


def test_reconcile_empty_log_leaves_zero():
    """Boş log + zero snapshot → noop."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    trade_logger = _make_logger_with_records([])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert pm.realized_pnl == 0.0
    assert pm.bankroll == 1000.0
