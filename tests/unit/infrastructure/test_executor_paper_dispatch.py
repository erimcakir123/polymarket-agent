"""Executor must delegate Mode.PAPER to PaperExecutor (not fake _simulate_order)."""
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import Mode, PaperConfig
from src.infrastructure.executor import Executor


def _book_resp(asks, bids):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"asks": asks, "bids": bids}
    return m


def test_paper_mode_delegates_to_paper_executor(tmp_path: Path) -> None:
    # Polymarket asks DESC, best ask at end (0.65). Plus stale-price guard wants
    # a CLOB book fetch result for the same token — same MagicMock works.
    book = _book_resp(
        asks=[{"price": "0.65", "size": "200"}],
        bids=[{"price": "0.62", "size": "100"}],
    )
    http = MagicMock(return_value=book)
    ex = Executor(
        mode=Mode.PAPER,
        http_get=http,
        paper_config=PaperConfig(),
        paper_audit_path=tmp_path / "exec.jsonl",
    )
    result = ex.place_order(token_id="tok1", side="BUY", price=0.65, size_usdc=50.0)
    assert result["mode"] == "paper"
    assert result["status"] == "FILLED"
    assert (tmp_path / "exec.jsonl").exists()


def test_dry_run_mode_keeps_old_behavior(tmp_path: Path) -> None:
    book = _book_resp([{"price": "0.65", "size": "1000"}], [{"price": "0.63", "size": "1000"}])
    http = MagicMock(return_value=book)
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    result = ex.place_order(token_id="tok1", side="BUY", price=0.65, size_usdc=50.0)
    assert result["mode"] == "dry_run"
    assert result["status"] == "simulated"


def test_exit_position_paper_mode_uses_paper_executor(tmp_path: Path) -> None:
    book = _book_resp(asks=[], bids=[{"price": "0.65", "size": "1000"}])
    http = MagicMock(return_value=book)
    ex = Executor(
        mode=Mode.PAPER,
        http_get=http,
        paper_config=PaperConfig(),
        paper_audit_path=tmp_path / "exec.jsonl",
    )
    pos = MagicMock(token_id="tok1", shares=50.0, bid_price=0.65, current_price=0.65)
    result = ex.exit_position(pos, reason="test")
    assert result["mode"] == "paper"
    assert result["reason"] == "test"
