"""BotStatusWriter — bot_status.json şeması ve hata toleransı."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.bot_status_writer import BotStatusWriter
from src.orchestration.cycle_manager import CycleTick


def _writer(tmp_path: Path) -> BotStatusWriter:
    store = JsonStore(str(tmp_path / "bot_status.json"))
    cm = MagicMock()
    cm.next_heavy_at_iso.return_value = "2026-04-15T15:30:00+00:00"
    return BotStatusWriter(store, cm)


def test_write_stage_writes_full_schema(tmp_path):
    w = _writer(tmp_path)
    w.write_stage(mode="dry_run", cycle="heavy", stage="scanning")
    snap = JsonStore(str(tmp_path / "bot_status.json")).load({})
    assert snap["mode"] == "dry_run"
    assert snap["cycle"] == "heavy"
    assert snap["stage"] == "scanning"
    assert snap["stage_at"]
    assert snap["next_heavy_at"] == "2026-04-15T15:30:00+00:00"
    assert snap["light_alive"] is True


def test_write_from_tick_heavy_writes_idle(tmp_path):
    w = _writer(tmp_path)
    w.write_from_tick(mode="dry_run", tick=CycleTick(run_heavy=True, run_light=True, reason="periodic_heavy"))
    snap = JsonStore(str(tmp_path / "bot_status.json")).load({})
    assert snap["cycle"] == "heavy"
    assert snap["stage"] == "idle"


def test_write_from_tick_light_writes_light(tmp_path):
    w = _writer(tmp_path)
    w.write_from_tick(mode="dry_run", tick=CycleTick(run_heavy=False, run_light=True, reason="light"))
    snap = JsonStore(str(tmp_path / "bot_status.json")).load({})
    assert snap["cycle"] == "light"
    assert snap["stage"] == "light"


def test_write_stage_swallows_oserror(tmp_path):
    store = MagicMock()
    store.save.side_effect = OSError("disk full")
    cm = MagicMock()
    cm.next_heavy_at_iso.return_value = "iso"
    w = BotStatusWriter(store, cm)
    w.write_stage(mode="dry_run", cycle="heavy", stage="scanning")  # raise etmemeli
