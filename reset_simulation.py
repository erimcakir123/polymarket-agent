"""Reset simulation — kill bot, archive data, restart fresh.

Usage: python reset_simulation.py [--no-start]

Archive structure:
  logs/archive/run_001_20260322_1430/   ← Each reset's full data
    trades.jsonl, predictions.jsonl, positions.json, price_history/, ...
  logs/archive/run_002_20260323_1012/
  ...

The bot NEVER reads from logs/archive/ — it only uses logs/ root files.
Archive is for post-analysis: AI performance metrics, error detection, strategy review.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"
ARCHIVE_DIR = LOGS_DIR / "archive"

# Files to ARCHIVE then DELETE on reset (simulation state)
ARCHIVE_FILES = [
    "positions.json",
    "trades.jsonl",
    "portfolio.jsonl",
    "realized_pnl.json",
    "reentry_pool.json",
    "blacklist.json",
    "candidate_stock.json",
    "match_outcomes.jsonl",
    "exited_markets.json",
    "outcome_tracker.json",
    "predictions.jsonl",  # Delete on reset — all markets re-analyzed fresh after reset
]

# Files to ARCHIVE but KEEP (survives reset)
ARCHIVE_KEEP = []

# Files to DELETE only (not worth archiving)
DELETE_ONLY = [
    "bot_status.json",
    "agent.pid",
    "stop_signal",
    "bot_stdout.log",
    "bot_stderr.log",
    "bot_output.log",
    "bot_output_new.log",
]

# Directories to ARCHIVE then DELETE
ARCHIVE_DIRS = [
    "price_history",
]


def kill_all_bots() -> int:
    """Kill ALL running src.main processes. Returns count killed."""
    if sys.platform != "win32":
        print("Non-Windows kill not implemented")
        return 0

    try:
        result = subprocess.run(
            ["wmic", "process", "where", "CommandLine like '%src.main%'", "get", "ProcessId"],
            capture_output=True, text=True, timeout=10,
        )
        pids = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid != os.getpid():
                    pids.append(pid)
    except Exception as e:
        print(f"  Warning: wmic failed: {e}")
        pids = []

    if not pids:
        print("  No running bot processes found.")
        return 0

    killed = 0
    for pid in pids:
        try:
            subprocess.run(
                ["powershell", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                timeout=5, capture_output=True,
            )
            killed += 1
        except Exception:
            pass

    time.sleep(2)
    print(f"  Killed {killed} process(es): {pids}")
    return killed


def _next_run_number() -> int:
    """Get the next run number from existing archive folders."""
    if not ARCHIVE_DIR.exists():
        return 1
    existing = [d.name for d in ARCHIVE_DIR.iterdir() if d.is_dir() and d.name.startswith("run_")]
    if not existing:
        return 1
    nums = []
    for name in existing:
        try:
            nums.append(int(name.split("_")[1]))
        except (IndexError, ValueError):
            pass
    return max(nums, default=0) + 1


def archive_data() -> Path | None:
    """Move current simulation data to archive for post-analysis."""
    from datetime import datetime

    has_data = any((LOGS_DIR / f).exists() for f in ["trades.jsonl", "positions.json", "predictions.jsonl"])
    if not has_data:
        print("  No data to archive — skipping")
        return None

    run_num = _next_run_number()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = ARCHIVE_DIR / f"run_{run_num:03d}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Archive simulation files (will be deleted by wipe_data)
    archived = 0
    for fname in ARCHIVE_FILES:
        src = LOGS_DIR / fname
        if src.exists():
            shutil.copy2(src, run_dir / fname)
            archived += 1

    # Archive analysis cache files (copied but NOT deleted — survives reset)
    for fname in ARCHIVE_KEEP:
        src = LOGS_DIR / fname
        if src.exists():
            shutil.copy2(src, run_dir / fname)
            archived += 1

    # Archive price_history directory
    for dname in ARCHIVE_DIRS:
        src_dir = LOGS_DIR / dname
        if src_dir.exists() and any(src_dir.iterdir()):
            shutil.copytree(src_dir, run_dir / dname)
            archived += 1

    # Write run metadata
    meta = {
        "run": run_num,
        "archived_at": datetime.now().isoformat(),
        "files_archived": archived,
    }
    (run_dir / "_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"  Archived {archived} items -> archive/{run_dir.name}/")
    return run_dir


def wipe_data() -> None:
    """Delete all simulation data files after archiving."""
    deleted = 0
    for fname in ARCHIVE_FILES + DELETE_ONLY:
        fpath = LOGS_DIR / fname
        if fpath.exists():
            fpath.unlink()
            deleted += 1

    for dname in ARCHIVE_DIRS:
        dpath = LOGS_DIR / dname
        if dpath.exists():
            shutil.rmtree(dpath)
            deleted += 1

    print(f"  Wiped {deleted} items")



def reset_test_date() -> None:
    """Set test start date to today."""
    from datetime import date
    p = LOGS_DIR / "test_start_date.txt"
    p.write_text(date.today().isoformat())
    print(f"  Test start date: {date.today().isoformat()}")


def start_bot() -> int:
    """Start a single bot instance. Returns PID."""
    project_dir = Path(__file__).parent
    stdout_log = open(LOGS_DIR / "bot_stdout.log", "w")
    stderr_log = open(LOGS_DIR / "bot_stderr.log", "w")
    proc = subprocess.Popen(
        ["python", "-m", "src.main"],
        cwd=str(project_dir),
        stdout=stdout_log,
        stderr=stderr_log,
        creationflags=0x08000000 if sys.platform == "win32" else 0,  # CREATE_NO_WINDOW
    )
    print(f"  Bot started: PID {proc.pid}")
    return proc.pid


def verify_single_instance() -> bool:
    """Verify exactly 1 src.main process is running."""
    time.sleep(3)
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "CommandLine like '%src.main%'", "get", "ProcessId"],
            capture_output=True, text=True, timeout=10,
        )
        pids = [int(l.strip()) for l in result.stdout.splitlines() if l.strip().isdigit()]
        pids = [p for p in pids if p != os.getpid()]
        if len(pids) <= 2:
            # 2 is OK — WindowsApps shim + actual python (parent-child)
            print(f"  Verified: bot running (PIDs: {pids})")
            return True
        else:
            print(f"  WARNING: {len(pids)} processes found: {pids}")
            return False
    except Exception as e:
        print(f"  Verification failed: {e}")
        return False


def main() -> None:
    no_start = "--no-start" in sys.argv
    print("=" * 50)
    print("SIMULATION RESET")
    print("=" * 50)

    print("\n[1/5] Killing all bot processes...")
    kill_all_bots()

    print("\n[2/5] Archiving current data...")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    archive_data()

    print("\n[3/5] Wiping simulation data...")
    wipe_data()

    print("\n[4/5] Setting test start date...")
    reset_test_date()

    if no_start:
        print("\n[5/5] Skipped bot start (--no-start)")
    else:
        print("\n[5/5] Starting bot...")
        start_bot()
        verify_single_instance()

    print("\n" + "=" * 50)
    print("RESET COMPLETE — fresh simulation started")
    print("=" * 50)


if __name__ == "__main__":
    main()
