"""PaperExecutionsLogger — JSONL audit append for paper mode fills."""
import json
import tempfile
from pathlib import Path

from src.infrastructure.audit.paper_executions import PaperExecutionsLogger


def test_writes_execution_record_with_book_snapshot() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exec.jsonl"
        log = PaperExecutionsLogger(p)
        log.write({
            "ts": "2026-05-29T00:00:00Z",
            "token_id": "tok1",
            "side": "BUY",
            "strategy": "market",
            "target_price": 0.65,
            "result_status": "filled",
            "book_snapshot": {"asks_top3": [{"p": 0.65, "s": 100}], "bids_top3": []},
        })
        rec = json.loads(p.read_text(encoding="utf-8").strip())
        assert rec["token_id"] == "tok1"
        assert rec["book_snapshot"]["asks_top3"][0]["p"] == 0.65


def test_appends_not_overwrites() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exec.jsonl"
        log = PaperExecutionsLogger(p)
        log.write({"ts": "1", "token_id": "a"})
        log.write({"ts": "2", "token_id": "b"})
        assert len(p.read_text(encoding="utf-8").strip().split("\n")) == 2


def test_handles_empty_book_snapshot() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exec.jsonl"
        log = PaperExecutionsLogger(p)
        log.write({"ts": "1", "token_id": "a", "book_snapshot": {"asks_top3": [], "bids_top3": []}})
        rec = json.loads(p.read_text(encoding="utf-8").strip())
        assert rec["book_snapshot"]["asks_top3"] == []
