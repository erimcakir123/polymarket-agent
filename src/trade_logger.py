"""Append-only JSONL trade logger."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TradeLogger:
    def __init__(self, file_path: str, archive_path: str | None = None) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._archive: Path | None = None
        if archive_path:
            self._archive = Path(archive_path)
            self._archive.parent.mkdir(parents=True, exist_ok=True)

    def log(self, data: dict[str, Any]) -> None:
        data = {**data}  # Don't mutate caller's dict
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(data, default=str) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
        if self._archive:
            try:
                with open(self._archive, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError:
                pass

    def read_recent(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        # Read from end of file -- avoids loading entire file into memory
        try:
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                # Read last chunk (generous: ~500 bytes per line)
                chunk_size = min(size, n * 500)
                f.seek(size - chunk_size)
                data = f.read().decode("utf-8", errors="replace")
            lines = [l for l in data.strip().split("\n") if l.strip()]
            # If we didn't read from the start, first line may be partial
            if chunk_size < size:
                lines = lines[1:]
            result = []
            for l in lines[-n:]:
                try:
                    result.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            return result
        except OSError:
            return []

    def read_recent_page(self, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        """Read last `limit` entries, with optional offset for pagination.

        Uses tail-read to avoid loading entire file. More efficient than read_all().
        """
        if not self.path.exists():
            return []
        try:
            total_needed = limit + offset
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                chunk_size = min(size, total_needed * 500)
                f.seek(size - chunk_size)
                data = f.read().decode("utf-8", errors="replace")
            lines = [l for l in data.strip().split("\n") if l.strip()]
            if chunk_size < size:
                lines = lines[1:]
            result = []
            for l in lines:
                try:
                    result.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            if offset > 0:
                result = result[:-offset] if offset < len(result) else []
            return result[-limit:] if len(result) > limit else result
        except OSError:
            return []

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


