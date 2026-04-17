"""Trade history weekly pagination reader tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.presentation.dashboard.readers import read_trades_by_week


def _make_trade(exit_iso: str) -> dict:
    return {
        "slug": "test-abc-xyz-2026-04-18",
        "sport_tag": "baseball_mlb",
        "exit_timestamp": exit_iso,
        "exit_pnl_usdc": 10.0,
        "exit_price": 0.55,
        "entry_timestamp": "2026-04-15T10:00:00Z",
    }


def _write_trades(tmp_path: Path, trades: list[dict]) -> Path:
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    with open(logs / "trade_history.jsonl", "w") as f:
        for t in trades:
            f.write(json.dumps(t) + "\n")
    return logs


def _monday_of_current_week() -> datetime:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


class TestReadTradesByWeek:
    def test_current_week_returns_this_weeks_trades(self, tmp_path: Path):
        monday = _monday_of_current_week()
        t1 = _make_trade((monday + timedelta(hours=10)).isoformat())
        t2 = _make_trade((monday + timedelta(days=2, hours=5)).isoformat())
        old = _make_trade((monday - timedelta(days=3)).isoformat())
        logs = _write_trades(tmp_path, [old, t1, t2])
        trades, label, has_older = read_trades_by_week(logs, week_offset=0)
        assert len(trades) == 2
        assert has_older is True

    def test_past_week_returns_correct_trades(self, tmp_path: Path):
        monday = _monday_of_current_week()
        this_week = _make_trade((monday + timedelta(hours=5)).isoformat())
        last_week = _make_trade((monday - timedelta(days=3)).isoformat())
        logs = _write_trades(tmp_path, [last_week, this_week])
        trades, label, has_older = read_trades_by_week(logs, week_offset=1)
        assert len(trades) == 1
        assert has_older is False

    def test_empty_week_returns_empty(self, tmp_path: Path):
        monday = _monday_of_current_week()
        t = _make_trade((monday + timedelta(hours=5)).isoformat())
        logs = _write_trades(tmp_path, [t])
        trades, label, has_older = read_trades_by_week(logs, week_offset=5)
        assert trades == []
        assert has_older is False

    def test_has_older_true_when_older_exists(self, tmp_path: Path):
        monday = _monday_of_current_week()
        old = _make_trade((monday - timedelta(days=14)).isoformat())
        last_week = _make_trade((monday - timedelta(days=3)).isoformat())
        logs = _write_trades(tmp_path, [old, last_week])
        trades, label, has_older = read_trades_by_week(logs, week_offset=1)
        assert len(trades) == 1
        assert has_older is True

    def test_label_format(self, tmp_path: Path):
        monday = _monday_of_current_week()
        t = _make_trade((monday + timedelta(hours=5)).isoformat())
        logs = _write_trades(tmp_path, [t])
        _, label, _ = read_trades_by_week(logs, week_offset=0)
        assert " - " in label

    def test_no_file_returns_empty(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir(exist_ok=True)
        trades, label, has_older = read_trades_by_week(logs, week_offset=0)
        assert trades == []
        assert has_older is False
