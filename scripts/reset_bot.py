"""Archive current bot state to logs/archive/<timestamp>/ and reset logs/.

Preserves everything that might be useful for post-run analysis (bot.log,
trades.jsonl, positions.json, portfolio.jsonl, ai_budget.json, blacklist.json,
reentry_pool.json) under a timestamped directory, then deletes runtime state
so the bot starts clean on the next launch.

Usage:
    python scripts/reset_bot.py
    python scripts/reset_bot.py --no-archive   # skip archive (nuke-only)
    python scripts/reset_bot.py --prune-days 30  # also delete arches >30 days

Does NOT touch:
    - logs/analyze.py, logs/full_report.py (utility scripts)
    - logs/archive/ (the archive tree itself)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
ARCHIVE_DIR = LOG_DIR / "archive"

# Files to archive before reset. Missing files are silently skipped.
CRITICAL_FILES = [
    "bot.log",
    "bot.log.1",
    "trades.jsonl",
    "positions.json",
    "portfolio.jsonl",
    "ai_budget.json",
    "blacklist.json",
    "reentry_pool.json",
    "realized_pnl.json",
    "circuit_breaker_state.json",
    "scout_queue.json",
    "bot_status.json",
    "equity.jsonl",
    "calibration.jsonl",
    "match_outcomes.jsonl",
]

# Files/directories to DELETE after archive (runtime state).
DELETE_FILES = CRITICAL_FILES + [
    "agent.pid",
    "ai_budget.backup.json",
    "api_usage.json",
    "odds_cache.json",
    "roster_cache.json",
    "team_resolver_cache.json",
]
DELETE_DIRS = ["price_history"]

# Note: analyze.py, full_report.py, and archive/ are never in DELETE_FILES/DIRS
# so they are implicitly preserved. Delete lists are opt-in, not opt-out.


def archive_state(archive_path: Path) -> int:
    """Copy critical files to archive_path. Returns count archived."""
    archive_path.mkdir(parents=True, exist_ok=True)
    count = 0
    for fname in CRITICAL_FILES:
        src = LOG_DIR / fname
        if src.exists() and src.is_file():
            try:
                shutil.copy2(src, archive_path / fname)
                count += 1
            except OSError as exc:
                print(f"  WARN: could not archive {fname}: {exc}", file=sys.stderr)
    return count


def reset_state() -> int:
    """Delete runtime state files/dirs. Returns count removed."""
    count = 0
    for fname in DELETE_FILES:
        target = LOG_DIR / fname
        if target.exists() and target.is_file():
            try:
                target.unlink()
                count += 1
            except OSError as exc:
                print(f"  WARN: could not delete {fname}: {exc}", file=sys.stderr)
    for dname in DELETE_DIRS:
        target = LOG_DIR / dname
        if target.exists() and target.is_dir():
            try:
                shutil.rmtree(target)
                count += 1
            except OSError as exc:
                print(f"  WARN: could not delete dir {dname}: {exc}", file=sys.stderr)
    return count


def prune_old_archives(days: int) -> int:
    """Delete archive subdirectories older than `days`. Returns count removed."""
    if not ARCHIVE_DIR.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for sub in ARCHIVE_DIR.iterdir():
        if not sub.is_dir():
            continue
        try:
            # Directory name format: YYYY-MM-DD_HH-MM-SS
            dt = datetime.strptime(sub.name, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            continue  # Skip directories not matching the format
        if dt < cutoff:
            try:
                shutil.rmtree(sub)
                removed += 1
                print(f"  pruned: {sub.name}")
            except OSError as exc:
                print(f"  WARN: could not prune {sub.name}: {exc}", file=sys.stderr)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive and reset bot state")
    parser.add_argument(
        "--no-archive", action="store_true",
        help="Skip archive step (delete state without backup)",
    )
    parser.add_argument(
        "--prune-days", type=int, default=0,
        help="Delete archives older than N days (default: keep all)",
    )
    args = parser.parse_args()

    if not LOG_DIR.exists():
        print(f"ERROR: {LOG_DIR} does not exist", file=sys.stderr)
        return 1

    print(f"LOG_DIR: {LOG_DIR}")

    if args.no_archive:
        print("Skipping archive (--no-archive).")
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_path = ARCHIVE_DIR / ts
        print(f"Archiving to: {archive_path}")
        n_archived = archive_state(archive_path)
        print(f"  archived {n_archived} file(s)")

    print("Resetting runtime state...")
    n_removed = reset_state()
    print(f"  removed {n_removed} item(s)")

    if args.prune_days > 0:
        print(f"Pruning archives older than {args.prune_days} days...")
        n_pruned = prune_old_archives(args.prune_days)
        print(f"  pruned {n_pruned} old archive(s)")

    print("Reset complete. Bot can now be started fresh:")
    print("  python -m src.main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
