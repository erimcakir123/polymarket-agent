"""presentation/dashboard/readers.py için birim testler.

ARCH_GUARD Kural 1 kontrolü: bu modül infra import etmemeli.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.presentation.dashboard import readers


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
    out = readers.read_positions(tmp_path)
    assert out == {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0}


def test_read_positions_valid_file(tmp_path: Path) -> None:
    data = {"positions": {"k1": {"slug": "a"}}, "realized_pnl": 42.0, "high_water_mark": 1200.0}
    (tmp_path / "positions.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_positions(tmp_path)
    assert out["realized_pnl"] == 42.0
    assert "k1" in out["positions"]


def test_read_positions_corrupt_returns_default(tmp_path: Path) -> None:
    (tmp_path / "positions.json").write_text("not json", encoding="utf-8")
    out = readers.read_positions(tmp_path)
    assert out["positions"] == {}


# ── JSONL tail readers ──

def _write_jsonl(path: Path, lines: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")


def test_read_trades_missing_returns_empty(tmp_path: Path) -> None:
    assert readers.read_trades(tmp_path) == []


def test_read_trades_tail(tmp_path: Path) -> None:
    rows = [{"slug": f"m-{i}"} for i in range(30)]
    _write_jsonl(tmp_path / "trade_history.jsonl", rows)
    out = readers.read_trades(tmp_path, n=10)
    assert len(out) == 10
    assert out[-1]["slug"] == "m-29"
    assert out[0]["slug"] == "m-20"


def test_read_equity_history_tail(tmp_path: Path) -> None:
    rows = [{"bankroll": 1000 + i} for i in range(5)]
    _write_jsonl(tmp_path / "equity_history.jsonl", rows)
    out = readers.read_equity_history(tmp_path, n=100)
    assert len(out) == 5
    assert out[-1]["bankroll"] == 1004


def test_read_skipped_tail(tmp_path: Path) -> None:
    rows = [{"slug": f"s-{i}", "skip_reason": "no_edge"} for i in range(3)]
    _write_jsonl(tmp_path / "skipped_trades.jsonl", rows)
    out = readers.read_skipped(tmp_path)
    assert len(out) == 3
    assert out[0]["skip_reason"] == "no_edge"


# ── read_eligible_queue ──

def test_read_eligible_queue_missing_empty(tmp_path: Path) -> None:
    assert readers.read_eligible_queue(tmp_path) == []


def test_read_eligible_queue_list(tmp_path: Path) -> None:
    data = [{"slug": "a"}, {"slug": "b"}]
    (tmp_path / "stock_queue.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_eligible_queue(tmp_path)
    assert len(out) == 2


def test_read_eligible_queue_non_list_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "stock_queue.json").write_text('{"not": "list"}', encoding="utf-8")
    assert readers.read_eligible_queue(tmp_path) == []


# ── read_breaker ──

def test_read_breaker_missing_returns_empty_dict(tmp_path: Path) -> None:
    assert readers.read_breaker(tmp_path) == {}


def test_read_breaker_valid(tmp_path: Path) -> None:
    data = {"daily_realized_pnl_pct": -0.05, "consecutive_losses": 2}
    (tmp_path / "circuit_breaker_state.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_breaker(tmp_path)
    assert out["consecutive_losses"] == 2


# ── bot_is_alive ──

def test_bot_is_alive_no_pid_file(tmp_path: Path) -> None:
    assert readers.bot_is_alive(tmp_path) is False


def test_bot_is_alive_invalid_pid_content(tmp_path: Path) -> None:
    (tmp_path / "agent.pid").write_text("not a number", encoding="utf-8")
    assert readers.bot_is_alive(tmp_path) is False


def test_bot_is_alive_nonexistent_pid(tmp_path: Path) -> None:
    (tmp_path / "agent.pid").write_text("999999", encoding="utf-8")
    assert readers.bot_is_alive(tmp_path) is False
