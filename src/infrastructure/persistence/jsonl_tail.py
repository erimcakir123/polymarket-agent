"""JSONL tail reader — append-only JSONL dosyalarından son N satırı döndürür.

Diski end-seek ile küçük bir chunk okuyup deserialize eder. Birden fazla
logger (trade, equity, skipped) aynı algoritmayı kullanıyordu — tek kopya.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_BYTES_PER_LINE = 512


def read_jsonl_tail(
    path: Path,
    n: int,
    bytes_per_line_hint: int = _DEFAULT_BYTES_PER_LINE,
) -> list[dict[str, Any]]:
    """Dosyanın son N satırını dict listesi olarak döner. Dosya yok/bozuk → []."""
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk_size = min(size, n * bytes_per_line_hint)
            f.seek(size - chunk_size)
            raw = f.read().decode("utf-8", errors="replace")
        lines = [l for l in raw.strip().split("\n") if l.strip()]
        # Chunk dosyanın tamamını kapsamıyorsa ilk satır kesilmiş olabilir → at.
        if chunk_size < size and lines:
            lines = lines[1:]
        out: list[dict[str, Any]] = []
        for l in lines[-n:]:
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return out
    except OSError as e:
        logger.warning("read_jsonl_tail(%s) failed: %s", path, e)
        return []
