"""Paper-mode execution audit — appends one JSONL record per fill decision.

Captures the book snapshot at decision time so post-hoc analysis can verify
the fill decision was correct given the orderbook state.
"""
from __future__ import annotations

import json
from pathlib import Path


class PaperExecutionsLogger:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str))
            f.write("\n")
