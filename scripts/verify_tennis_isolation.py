"""Verify tennis sandbox state isolation — guarantees that build_tennis_deps
yields NO path pointing into the main bot's worktree.

Exit 0 → isolation OK (all paths inside tennis-lab/).
Exit 1 → isolation BROKEN (at least one path leaks).

Usage:
    python scripts/verify_tennis_isolation.py

Stage 7 PLAN-TENNIS-001.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.orchestration.tennis_factory import build_tennis_deps

# Main bot worktree adı — bu string'i içeren hiçbir path kabul edilmez.
_MAIN_BOT_MARKER = "Polymarket Agent 2.0"


def _collect_dep_paths(deps) -> dict[str, Path]:  # type: ignore[no-untyped-def]
    """Build the {name → Path} map of every disk location the deps will touch."""
    state = deps.state
    eq = deps.equity_logger
    # EntryProcessor / ExitProcessor ortak `_TennisAgentDeps` instance'ı
    # paylaşır — trade_logger + skipped_logger + bot_status_writer'ın
    # store path'lerini bu üzerinden topla.
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


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    config_path = _ROOT / "config_tennis.yaml"
    if not config_path.exists():
        print(f"ERROR: {config_path} not found.")
        return 1

    logs_root = _ROOT / "logs"
    data_root = _ROOT / "data"
    deps = build_tennis_deps(
        config_path=config_path,
        data_dir=data_root,
        logs_dir=logs_root,
    )

    paths = _collect_dep_paths(deps)

    print("Tennis sandbox path audit")
    print(f"  Tennis root: {_ROOT}")
    print(f"  Forbidden marker: '{_MAIN_BOT_MARKER}'")
    print("  Paths:")
    for name, p in paths.items():
        print(f"    {name}: {p}")

    failures: list[str] = []
    for name, p in paths.items():
        resolved = p.resolve()
        if _MAIN_BOT_MARKER in str(resolved):
            failures.append(f"  LEAK INTO MAIN BOT: {name} → {resolved}")
            continue
        if not _is_inside(p, _ROOT):
            failures.append(f"  OUTSIDE TENNIS-LAB: {name} → {resolved}")

    if failures:
        print("\nISOLATION BROKEN:")
        for f in failures:
            print(f)
        return 1

    print("\nIsolation OK — all paths inside tennis-lab/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
