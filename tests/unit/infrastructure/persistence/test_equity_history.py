"""equity_history.py için birim testler."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.persistence.equity_history import EquityHistoryLogger, EquitySnapshot


def _snap(**overrides) -> EquitySnapshot:
    base = dict(
        timestamp="2026-04-14T10:00:00Z",
        bankroll=1000.0,
        realized_pnl=50.0,
        unrealized_pnl=-3.17,
        invested=396.0,
        open_positions=5,
    )
    base.update(overrides)
    return EquitySnapshot(**base)


def test_snapshot_fields_roundtrip() -> None:
    s = _snap()
    data = s.model_dump(mode="json")
    restored = EquitySnapshot(**data)
    assert restored.bankroll == 1000.0
    assert restored.open_positions == 5


def test_log_appends_jsonl_line(tmp_path: Path) -> None:
    log = EquityHistoryLogger(str(tmp_path / "equity.jsonl"))
    log.log(_snap(bankroll=1000.0))
    log.log(_snap(bankroll=1050.0))
    rows = log.read_recent(10)
    assert len(rows) == 2
    assert rows[0]["bankroll"] == 1000.0
    assert rows[1]["bankroll"] == 1050.0


def test_read_recent_tail(tmp_path: Path) -> None:
    log = EquityHistoryLogger(str(tmp_path / "equity.jsonl"))
    for i in range(150):
        log.log(_snap(bankroll=1000.0 + i))
    recent = log.read_recent(100)
    assert len(recent) == 100
    assert recent[-1]["bankroll"] == 1149.0
    assert recent[0]["bankroll"] == 1050.0


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    log = EquityHistoryLogger(str(tmp_path / "nope.jsonl"))
    assert log.read_recent(10) == []


def test_creates_parent_dir(tmp_path: Path) -> None:
    log = EquityHistoryLogger(str(tmp_path / "deep" / "nested" / "e.jsonl"))
    log.log(_snap())
    assert (tmp_path / "deep" / "nested" / "e.jsonl").exists()
