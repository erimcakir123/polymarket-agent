"""logs/runtime + logs/audit + data/ path ayrım testleri."""
from __future__ import annotations

from pathlib import Path


def test_startup_creates_runtime_audit_data_dirs(tmp_path: Path) -> None:
    """bootstrap() logs/runtime, logs/audit, data/ dizinlerini oluşturur."""
    from src.config.settings import AppConfig
    from src.orchestration.startup import bootstrap

    cfg = AppConfig()
    logs_dir = tmp_path / "logs"
    state = bootstrap(cfg, logs_dir=logs_dir)

    assert (logs_dir / "runtime").is_dir(), "logs/runtime/ oluşturulmalı"
    assert (logs_dir / "audit").is_dir(), "logs/audit/ oluşturulmalı"
    assert (tmp_path / "data").is_dir(), "data/ oluşturulmalı"


def test_readers_state_files_from_data_dir(tmp_path: Path) -> None:
    """readers.py state okuyucuları logs/../data/'dan okur."""
    from src.presentation.dashboard.readers import read_positions, read_breaker, read_bot_status

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    (data_dir / "positions.json").write_text(
        '{"positions": {}, "realized_pnl": 42.0, "high_water_mark": 0.0}',
        encoding="utf-8",
    )
    (data_dir / "circuit_breaker_state.json").write_text('{"tripped": true}', encoding="utf-8")
    (data_dir / "bot_status.json").write_text('{"mode": "dry_run"}', encoding="utf-8")

    pos = read_positions(logs_dir)
    assert pos["realized_pnl"] == 42.0

    breaker = read_breaker(logs_dir)
    assert breaker.get("tripped") is True

    status = read_bot_status(logs_dir)
    assert status.get("mode") == "dry_run"


def test_readers_audit_files_from_audit_subdir(tmp_path: Path) -> None:
    """readers.py log okuyucuları logs/audit/ subdir'den okur."""
    from src.presentation.dashboard.readers import read_trades, read_equity_history

    logs_dir = tmp_path / "logs"
    audit_dir = logs_dir / "audit"
    audit_dir.mkdir(parents=True)

    (audit_dir / "trade_history.jsonl").write_text(
        '{"condition_id": "abc", "entry_price": 0.5}\n', encoding="utf-8"
    )
    (audit_dir / "equity_history.jsonl").write_text(
        '{"equity": 1050.0}\n', encoding="utf-8"
    )

    trades = read_trades(logs_dir)
    assert len(trades) == 1
    assert trades[0]["condition_id"] == "abc"

    equity = read_equity_history(logs_dir)
    assert len(equity) == 1
    assert equity[0]["equity"] == 1050.0


def test_readers_runtime_skipped_from_runtime_subdir(tmp_path: Path) -> None:
    """readers.py skipped okuyucusu logs/runtime/ subdir'den okur."""
    from src.presentation.dashboard.readers import read_skipped

    logs_dir = tmp_path / "logs"
    runtime_dir = logs_dir / "runtime"
    runtime_dir.mkdir(parents=True)

    (runtime_dir / "skipped_trades.jsonl").write_text(
        '{"slug": "test-market", "reason": "INACTIVE_SPORT"}\n', encoding="utf-8"
    )

    skipped = read_skipped(logs_dir)
    assert len(skipped) == 1
    assert skipped[0]["slug"] == "test-market"
