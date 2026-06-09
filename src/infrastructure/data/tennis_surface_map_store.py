"""Zemin haritası JSON save/load (infra — I/O burada)."""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_PATH = Path("data/tennis_surface_map.json")


def save_surface_map(surface_map: dict[str, str], path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(surface_map, ensure_ascii=False, indent=2), encoding="utf-8")


def load_surface_map(path: Path = _DEFAULT_PATH) -> dict[str, str]:
    """Dosya yoksa/bozuksa boş dict (caller skip+uyar yapar)."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
