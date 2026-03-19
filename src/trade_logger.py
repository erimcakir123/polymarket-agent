"""Append-only JSONL trade logger."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TradeLogger:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, data: dict[str, Any]) -> None:
        data = {**data}  # Don't mutate caller's dict
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l.strip()]
        result = []
        for l in lines[-n:]:
            try:
                result.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return result

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().split("\n")
        result = []
        for l in lines:
            if not l.strip():
                continue
            try:
                result.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return result
