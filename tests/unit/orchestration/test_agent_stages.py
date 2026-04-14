"""Agent cycle stage snapshot yazımı — bot_status.json şeması."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.cycle_manager import CycleTick


def _make_deps(tmp_path: Path) -> AgentDeps:
    """Minimal mock'lu AgentDeps."""
    status_store = JsonStore(str(tmp_path / "bot_status.json"))
    state = MagicMock()
    state.config = AppConfig()
    state.portfolio.positions = {}
    state.portfolio.count.return_value = 0
    cycle_manager = MagicMock()
    cycle_manager.next_heavy_at_iso.return_value = "2026-04-15T15:30:00+00:00"
    return AgentDeps(
        state=state,
        scanner=MagicMock(),
        cycle_manager=cycle_manager,
        executor=MagicMock(),
        odds_client=MagicMock(),
        trade_logger=MagicMock(),
        gate=MagicMock(),
        cooldown=MagicMock(),
        equity_logger=MagicMock(),
        skipped_logger=MagicMock(),
        eligible_snapshot=MagicMock(),
        bot_status_store=status_store,
        price_feed=None,
    )


def test_write_bot_status_stage_writes_expected_schema(tmp_path):
    """Stage yazımı — schema: mode, cycle, stage, stage_at, next_heavy_at, light_alive."""
    deps = _make_deps(tmp_path)
    agent = Agent(deps)
    agent._write_bot_status_stage(cycle="heavy", stage="scanning")

    snap = deps.bot_status_store.load(default={})
    assert snap["mode"] == "dry_run"
    assert snap["cycle"] == "heavy"
    assert snap["stage"] == "scanning"
    assert "stage_at" in snap and snap["stage_at"]
    assert snap["next_heavy_at"] == "2026-04-15T15:30:00+00:00"
    assert snap["light_alive"] is True


def test_write_bot_status_stage_idle_writes_idle_stage(tmp_path):
    """Heavy sonrası idle snapshot."""
    deps = _make_deps(tmp_path)
    agent = Agent(deps)
    agent._write_bot_status_stage(cycle="heavy", stage="idle")

    snap = deps.bot_status_store.load(default={})
    assert snap["stage"] == "idle"
    assert snap["cycle"] == "heavy"


def test_write_bot_status_stage_swallows_oserror(tmp_path, caplog):
    """OSError → warning, raise etmez."""
    deps = _make_deps(tmp_path)
    deps.bot_status_store = MagicMock()
    deps.bot_status_store.save.side_effect = OSError("disk full")
    agent = Agent(deps)
    agent._write_bot_status_stage(cycle="heavy", stage="scanning")  # raise etmemeli
