"""json_store.py için birim testler."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.infrastructure.persistence.json_store import JsonStore


def test_save_load_roundtrip(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "state.json")
    store.save({"bankroll": 1000.0, "mode": "dry_run"})
    data = store.load(default={})
    assert data["bankroll"] == 1000.0
    assert data["mode"] == "dry_run"


def test_load_missing_returns_default(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "nope.json")
    assert store.load(default={"x": 1}) == {"x": 1}


def test_load_corrupt_returns_default(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    store = JsonStore(p)
    assert store.load(default={"ok": True}) == {"ok": True}


def test_save_creates_parent_dir(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "dir" / "state.json"
    store = JsonStore(p)
    store.save({"a": 1})
    assert p.exists()


def test_save_atomic_no_tmp_leftover(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    store = JsonStore(p)
    store.save({"a": 1})
    tmps = list(tmp_path.glob("*.tmp"))
    assert tmps == []


def test_save_handles_datetime_default_str(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "t.json")
    store.save({"ts": datetime(2026, 4, 13, tzinfo=timezone.utc)})
    data = store.load(default={})
    assert "2026-04-13" in data["ts"]


def test_exists(tmp_path: Path) -> None:
    store = JsonStore(tmp_path / "state.json")
    assert store.exists() is False
    store.save({})
    assert store.exists() is True
