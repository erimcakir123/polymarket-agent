"""presentation/dashboard/readers.py için birim testler.

ARCH_GUARD Kural 1 kontrolü: bu modül infra import etmemeli.

Dizin yapısı (yeni):
  logs_dir/audit/trade_history.jsonl, equity_history.jsonl
  logs_dir/runtime/skipped_trades.jsonl
  logs_dir/../data/positions.json, circuit_breaker_state.json, stock_queue.json
"""
from __future__ import annotations

import json
from pathlib import Path

from src.presentation.dashboard import readers


# ── Dizin setup helper ───────────────────────────────────────────────────────

def _mk_logs(tmp_path: Path) -> tuple[Path, Path]:
    """logs_dir ve data_dir oluştur, döner."""
    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    (logs_dir / "audit").mkdir(parents=True)
    (logs_dir / "runtime").mkdir(parents=True)
    data_dir.mkdir()
    return logs_dir, data_dir


# ── Katman ihlali kontrolü ──

def test_readers_module_has_no_infra_imports() -> None:
    """readers.py infrastructure/domain/strategy/orchestration import etmemeli."""
    path = Path(readers.__file__)
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from src.infrastructure",
        "import src.infrastructure",
        "from src.domain",
        "import src.domain",
        "from src.strategy",
        "import src.strategy",
        "from src.orchestration",
        "import src.orchestration",
    ):
        assert forbidden not in source, f"Layer violation: {forbidden}"


# ── read_positions ──

def test_read_positions_missing_returns_default(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    out = readers.read_positions(logs_dir)
    assert out == {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0}


def test_read_positions_valid_file(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = {"positions": {"k1": {"slug": "a"}}, "realized_pnl": 42.0, "high_water_mark": 1200.0}
    (data_dir / "positions.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_positions(logs_dir)
    assert out["realized_pnl"] == 42.0
    assert "k1" in out["positions"]


def test_read_positions_corrupt_returns_default(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "positions.json").write_text("not json", encoding="utf-8")
    out = readers.read_positions(logs_dir)
    assert out["positions"] == {}


# ── JSONL tail readers ──

def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")


def test_read_trades_missing_returns_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_trades(logs_dir) == []


def test_read_trades_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"slug": f"m-{i}"} for i in range(30)]
    _write_jsonl(logs_dir / "audit" / "trade_history.jsonl", rows)
    out = readers.read_trades(logs_dir, n=10)
    assert len(out) == 10
    assert out[-1]["slug"] == "m-29"
    assert out[0]["slug"] == "m-20"


def test_read_equity_history_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"bankroll": 1000 + i} for i in range(5)]
    _write_jsonl(logs_dir / "audit" / "equity_history.jsonl", rows)
    out = readers.read_equity_history(logs_dir, n=100)
    assert len(out) == 5
    assert out[-1]["bankroll"] == 1004


def test_read_skipped_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"slug": f"s-{i}", "skip_reason": "no_edge"} for i in range(3)]
    _write_jsonl(logs_dir / "runtime" / "skipped_trades.jsonl", rows)
    out = readers.read_skipped(logs_dir)
    assert len(out) == 3
    assert out[0]["skip_reason"] == "no_edge"


# ── read_eligible_queue ──

def test_read_eligible_queue_missing_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_eligible_queue(logs_dir) == []


def test_read_eligible_queue_list(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = [{"slug": "a"}, {"slug": "b"}]
    (data_dir / "stock_queue.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_eligible_queue(logs_dir)
    assert len(out) == 2


def test_read_eligible_queue_non_list_returns_empty(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "stock_queue.json").write_text('{"not": "list"}', encoding="utf-8")
    assert readers.read_eligible_queue(logs_dir) == []


# ── read_breaker ──

def test_read_breaker_missing_returns_empty_dict(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_breaker(logs_dir) == {}


def test_read_breaker_valid(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = {"daily_realized_pnl_pct": -0.05, "consecutive_losses": 2}
    (data_dir / "circuit_breaker_state.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_breaker(logs_dir)
    assert out["consecutive_losses"] == 2


# ── bot_is_alive ──

def test_bot_is_alive_no_pid_file(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.bot_is_alive(logs_dir) is False


def test_bot_is_alive_invalid_pid_content(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "agent.pid").write_text("not a number", encoding="utf-8")
    assert readers.bot_is_alive(logs_dir) is False


def test_bot_is_alive_nonexistent_pid(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "agent.pid").write_text("999999", encoding="utf-8")
    assert readers.bot_is_alive(logs_dir) is False
