"""Tennis lab sandbox entry point.

Run:
    python scripts/tennis_main.py

Loads config_tennis.yaml, builds tennis deps, prints sandbox status.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §11
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.tennis_factory import build_tennis_deps


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config_path = Path("config_tennis.yaml")
    if not config_path.exists():
        print(f"ERROR: {config_path} not found. Run from tennis-lab worktree root.")
        sys.exit(1)
    deps = build_tennis_deps(config_path=config_path)
    print("Tennis lab sandbox starting...")
    print(f"  Mode: {deps.config.mode.value}")
    print(f"  Bankroll: ${deps.config.initial_bankroll}")
    print(
        f"  Dashboard: http://{deps.config.dashboard.host}:{deps.config.dashboard.port}"
    )
    print(f"  Ratings cache: {deps.config.tennis.ratings_cache}")
    print(f"  Diagnostic logs: {deps.config.tennis.diagnostic_log_dir}")
    # Full agent loop wired in subsequent tasks
    print("\nReady. Run scripts/build_tennis_ratings.py first to build initial ratings.")


if __name__ == "__main__":
    main()
