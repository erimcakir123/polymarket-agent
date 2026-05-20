"""Tennis sandbox state isolation guard tests (Stage 7 PLAN-TENNIS-001).

Guarantees that `build_tennis_deps` honours the supplied data_dir/logs_dir,
i.e. all persistence layers anchor their files inside the caller-supplied
roots (here pytest tmp_path) — proving that running the tennis sandbox from
any CWD never writes into the main bot's worktree.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.orchestration.tennis_factory import build_tennis_deps

# Main bot worktree adı — bu string'i içeren hiçbir path tennis dep'inden
# çıkmamalı. Tennis sandbox tamamen kendi worktree'sinde yaşar.
_MAIN_BOT_MARKER = "Polymarket Agent 2.0"


def _tennis_config_path() -> Path:
    """Locate config_tennis.yaml relative to the tennis-lab worktree root."""
    return Path(__file__).resolve().parents[3] / "config_tennis.yaml"


def _collect_paths(deps) -> dict[str, Path]:  # type: ignore[no-untyped-def]
    """Mirror verify_tennis_isolation script — every disk location deps touch."""
    state = deps.state
    eq = deps.equity_logger
    inner = deps.entry_processor.deps
    paths: dict[str, Path] = {
        "state.positions_store": Path(state.positions_store.path),
        "state.breaker_store": Path(state.breaker_store.path),
        "state.blacklist_store": Path(state.blacklist_store.path),
        "equity_logger.path": Path(eq.path),
        "ratings_store._path": Path(deps.ratings_store._path),
        "sackmann_client._cache_dir": Path(deps.sackmann_client._cache_dir),
        "diagnostic_logger._log_dir": Path(deps.diagnostic_logger._log_dir),
        "trade_logger.path": Path(inner.trade_logger.path),
        "skipped_logger.path": Path(inner.skipped_logger.path),
        "bot_status_writer.store": Path(inner.bot_status_writer._store.path),
    }
    if eq.mirror is not None:
        paths["equity_logger.mirror"] = Path(eq.mirror)
    return paths


def test_factory_paths_inside_tennis_lab(tmp_path: Path) -> None:
    """When called with absolute roots, every dep path lives inside them.

    Asserts that the anchor logic in tennis_factory honours the caller-supplied
    data_dir/logs_dir for both state files and the cfg.tennis.* relative
    overrides (sackmann_cache, ratings_cache, diagnostic_log_dir).
    """
    config_path = _tennis_config_path()
    if not config_path.exists():
        pytest.skip(f"config_tennis.yaml not at {config_path}")

    data_dir = tmp_path / "data"
    logs_dir = tmp_path / "logs"

    deps = build_tennis_deps(
        config_path=config_path,
        data_dir=data_dir,
        logs_dir=logs_dir,
    )

    paths = _collect_paths(deps)
    tmp_resolved = tmp_path.resolve()
    for name, p in paths.items():
        resolved = p.resolve()
        assert str(resolved).startswith(str(tmp_resolved)), (
            f"{name} = {resolved} not inside tmp_path={tmp_resolved}"
        )


def test_factory_paths_do_not_leak_into_main_repo(tmp_path: Path) -> None:
    """No dep path may contain the main bot's worktree name."""
    config_path = _tennis_config_path()
    if not config_path.exists():
        pytest.skip(f"config_tennis.yaml not at {config_path}")

    deps = build_tennis_deps(
        config_path=config_path,
        data_dir=tmp_path / "data",
        logs_dir=tmp_path / "logs",
    )

    paths = _collect_paths(deps)
    for name, p in paths.items():
        resolved = str(p.resolve())
        assert _MAIN_BOT_MARKER not in resolved, (
            f"{name} leaks into main bot: {resolved}"
        )
