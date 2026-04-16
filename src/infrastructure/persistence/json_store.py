"""Atomic JSON read/write helper for state files."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def load(self, default: Any) -> Any:
        if not self.path.exists():
            return default
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("JsonStore.load(%s) failed: %s — returning default", self.path, e)
            return default

    def save(self, data: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2, default=str)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        try:
            tmp.replace(self.path)
        except PermissionError:
            # Windows/OneDrive: target locked — direct overwrite fallback
            self.path.write_text(payload, encoding="utf-8")
            tmp.unlink(missing_ok=True)
