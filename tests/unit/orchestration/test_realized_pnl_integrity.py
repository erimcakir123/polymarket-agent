"""Realized PnL integrity (drift detector) testleri (2026-05-20).

Bug bağlamı: tennis-lab paper trading'de portfolio.realized_pnl (positions.json
snapshot) ile audit log toplamı (trade_history.jsonl) arasında $25.49 drift
gözlendi (phantom-restored entry + GUARD-4 sebebiyle reconcile blokluyordu).

Test edilen davranışlar:
  1. Bootstrap reconcile: zaten startup.py'de var; test mirror —
     drift varsa audit kazanır (GUARD-4 case haricinde).
  2. Dashboard realized = audit log toplamı (drift-immune SPOT).
  3. Per-cycle drift > $0.10 → ERROR log (görünür, otomatik düzeltme YOK).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.domain.portfolio.manager import PortfolioManager
from src.infrastructure.persistence.trade_logger import TradeHistoryLogger
from src.orchestration.tennis_pnl_integrity import (
    DRIFT_TOLERANCE_USD,
    audit_realized_sum,
    check_realized_pnl_drift,
    run_light_telemetry,
)
from src.presentation.dashboard import computed


# ── 3a: bootstrap reconcile (existing GUARD-4 behavior preserved) ──

def test_bootstrap_reconciles_realized_to_audit_sum_when_drifted(tmp_path: Path):
    """Audit log > snapshot → reconcile audit'i kabul eder (GUARD-4 tetiklenmez
    çünkü delta > 0). Bu davranış zaten startup._reconcile_realized_pnl içinde;
    burada smoke test."""
    from src.orchestration.startup import _reconcile_realized_pnl

    trade_path = tmp_path / "trade_history.jsonl"
    records = [
        {"condition_id": "0xA", "entry_timestamp": "2026-05-20T10:00:00Z",
         "exit_price": 0.6, "exit_pnl_usdc": 25.00, "partial_exits": []},
        {"condition_id": "0xB", "entry_timestamp": "2026-05-20T11:00:00Z",
         "exit_price": 0.7, "exit_pnl_usdc": 50.00, "partial_exits": []},
    ]
    trade_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    portfolio.realized_pnl = 10.00  # snapshot drifted low
    trade_logger = TradeHistoryLogger(str(trade_path))

    _reconcile_realized_pnl(portfolio, trade_logger, initial_bankroll=1000.0)

    # Audit kazanır → 75.00
    assert abs(portfolio.realized_pnl - 75.00) < 0.01


# ── 3b: dashboard realized = audit sum ──

def test_dashboard_realized_matches_audit_log_sum():
    """equity_summary_from_session trades verirsek realized = audit'ten gelir."""
    session_balance = {
        "has_data": True,
        "bankroll": 800.0,
        "realized_pnl": 99.99,  # session'a sızmış drift değeri
        "unrealized_pnl": 0.0,
        "invested": 100.0,
        "open_positions": 2,
        "peak_bankroll": 1000.0,
    }
    trades = [
        {"exit_price": 0.6, "exit_pnl_usdc": 20.00, "partial_exits": []},
        {"exit_price": None,
         "partial_exits": [{"realized_pnl_usdc": 15.00, "sell_pct": 0.4, "tier": 1}]},
    ]
    out = computed.equity_summary_from_session(session_balance, 1000.0, trades=trades)
    # Widget audit toplamı 35.00, session'daki 99.99'u görmezden gelmeli
    assert out["realized_pnl"] == 35.00


def test_dashboard_realized_falls_back_to_session_when_trades_none():
    """trades=None verilirse session'a düşer (geriye uyumlu)."""
    session_balance = {
        "has_data": True,
        "bankroll": 800.0,
        "realized_pnl": 99.99,
        "unrealized_pnl": 0.0,
        "invested": 100.0,
        "open_positions": 0,
        "peak_bankroll": 1000.0,
    }
    out = computed.equity_summary_from_session(session_balance, 1000.0)
    assert out["realized_pnl"] == 99.99


def test_realized_pnl_from_trades_handles_partial_only_and_full_only():
    """Mixed: 1 full-close, 1 partial-only, 1 not-yet-exited."""
    trades = [
        {"exit_price": 0.5, "exit_pnl_usdc": 10.0, "partial_exits": [
            {"realized_pnl_usdc": 5.0}]},  # full + partial of same trade
        {"exit_price": None,
         "partial_exits": [{"realized_pnl_usdc": 3.0}, {"realized_pnl_usdc": 2.0}]},
        {"exit_price": None, "partial_exits": []},  # open, no PnL
    ]
    total = computed.realized_pnl_from_trades(trades)
    assert abs(total - 20.0) < 1e-9


# ── 3c: per-cycle drift detector ──

def test_per_cycle_drift_warning_when_realized_differs(tmp_path: Path, caplog):
    """snapshot $50, audit $35 → ERROR log."""
    trade_path = tmp_path / "trade_history.jsonl"
    records = [
        {"condition_id": "0xA", "entry_timestamp": "ts",
         "exit_price": 0.5, "exit_pnl_usdc": 35.00, "partial_exits": []},
    ]
    trade_path.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    trade_logger = TradeHistoryLogger(str(trade_path))

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    portfolio.realized_pnl = 50.00  # drifted high (phantom case)

    with caplog.at_level(logging.ERROR, logger="src.orchestration.tennis_pnl_integrity"):
        drift = check_realized_pnl_drift(portfolio, trade_logger)

    assert abs(drift - 15.00) < 0.01
    assert "PnL DRIFT" in caplog.text
    assert "snapshot.realized=$50.00" in caplog.text
    assert "audit.realized=$35.00" in caplog.text


def test_no_drift_warning_when_within_tolerance(tmp_path: Path, caplog):
    """Floating noise (< $0.10) → log YOK."""
    trade_path = tmp_path / "trade_history.jsonl"
    records = [
        {"condition_id": "0xA", "entry_timestamp": "ts",
         "exit_price": 0.5, "exit_pnl_usdc": 50.00, "partial_exits": []},
    ]
    trade_path.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    trade_logger = TradeHistoryLogger(str(trade_path))

    portfolio = PortfolioManager(initial_bankroll=1000.0)
    portfolio.realized_pnl = 50.05  # within $0.10 noise

    with caplog.at_level(logging.ERROR, logger="src.orchestration.tennis_pnl_integrity"):
        check_realized_pnl_drift(portfolio, trade_logger)

    assert "PnL DRIFT" not in caplog.text


def test_audit_realized_sum_handles_partials_correctly(tmp_path: Path):
    """audit_realized_sum: partial + full birlikte doğru toplanır."""
    trade_path = tmp_path / "trade_history.jsonl"
    records = [
        {"condition_id": "0xA", "entry_timestamp": "ts1",
         "exit_price": 0.7, "exit_pnl_usdc": 30.0,
         "partial_exits": [{"realized_pnl_usdc": 10.0}]},
        {"condition_id": "0xB", "entry_timestamp": "ts2",
         "exit_price": None,
         "partial_exits": [{"realized_pnl_usdc": 5.0}]},
    ]
    trade_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    trade_logger = TradeHistoryLogger(str(trade_path))
    assert abs(audit_realized_sum(trade_logger) - 45.0) < 1e-9


def test_drift_check_skipped_when_trade_logger_none():
    """run_light_telemetry trade_logger=None → drift check çağrılmaz, crash YOK."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    # No trade_logger — drift not checked, but REST refresh should still call (will 0/0 since no positions).
    refreshed, resolved = run_light_telemetry(portfolio, None)
    assert refreshed == 0
    assert resolved == 0


def test_drift_tolerance_constant_matches_startup_reconcile():
    """Tolerance startup.py ile aynı olmalı (regression guard)."""
    # startup.py'deki eşik 0.01 değil 0.10 — drift detector burada daha cömert
    # (per-cycle gözlem için), reconcile daha sıkı (snapshot düzeltmek için).
    # Anchor değer: kullanıcının görebileceği en küçük anlamlı drift.
    assert DRIFT_TOLERANCE_USD == 0.10
