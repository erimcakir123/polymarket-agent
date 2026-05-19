"""Tennis lab sandbox entry point.

Usage:
    python scripts/tennis_main.py                    # Print sandbox status
    python scripts/tennis_main.py --once             # Run one scan cycle and exit
    python scripts/tennis_main.py --run              # Run forever (30-min interval)
    python scripts/tennis_main.py --run --interval 900  # Run forever (15-min interval)

Loads config_tennis.yaml, builds tennis deps, then:
  - (default) prints sandbox status
  - (--once) runs one scan cycle and prints N candidates logged
  - (--run) runs the agent loop indefinitely

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §11
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.orchestration.tennis_agent import run_forever, run_one_cycle
from src.orchestration.tennis_factory import build_tennis_deps


def _print_status(deps) -> None:  # type: ignore[no-untyped-def]
    print("Tennis lab sandbox")
    print(f"  Mode: {deps.config.mode.value}")
    print(f"  Bankroll: ${deps.config.initial_bankroll}")
    print(
        f"  Dashboard: http://{deps.config.dashboard.host}:{deps.config.dashboard.port}"
    )
    print(f"  Ratings cache: {deps.config.tennis.ratings_cache}")
    print(f"  Diagnostic logs: {deps.config.tennis.diagnostic_log_dir}")
    print(f"  Min edge: {deps.config.edge.min_edge:.0%}")
    print("\nRun with --once for a single scan, or --run to start the agent loop.")
    print("Run scripts/build_tennis_ratings.py first if ratings cache is missing.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tennis lab sandbox")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Start agent loop (runs until interrupted)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one scan cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="Cycle interval in seconds for --run mode (default: 1800 = 30min)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config_path = _ROOT / "config_tennis.yaml"
    if not config_path.exists():
        print(f"ERROR: {config_path} not found.")
        sys.exit(1)

    deps = build_tennis_deps(config_path=config_path)

    if args.run:
        run_forever(
            deps,
            interval_sec=args.interval,
            logs_dir=_ROOT / "logs",
            data_dir=_ROOT / "data",
        )
    elif args.once:
        n = run_one_cycle(deps)
        print(f"Logged {n} candidates")
    else:
        _print_status(deps)


if __name__ == "__main__":
    main()
