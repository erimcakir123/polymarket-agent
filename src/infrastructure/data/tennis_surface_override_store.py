"""Tenis zemin override önbelleği (Wiki sonuçları) — JSON I/O (infra)."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

_DEFAULT_PATH = Path("data/tennis_surface_overrides.json")


def load_overrides(path: Path = _DEFAULT_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_overrides(overrides: dict[str, dict], path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")


def is_stale(checked_at: str, now_iso: str, ttl_days: int) -> bool:
    """UNKNOWN kaydı TTL'den eski mi (tekrar Wiki gerekir mi). Bozuk damga → stale."""
    try:
        return (datetime.fromisoformat(now_iso) - datetime.fromisoformat(checked_at)).days >= ttl_days
    except (ValueError, TypeError):
        return True
