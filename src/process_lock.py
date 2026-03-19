"""Single-instance process lock using a PID file."""
from __future__ import annotations
import atexit
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

LOCK_FILE = Path(__file__).parent.parent / "logs" / "agent.pid"


def acquire_lock() -> None:
    """Acquire a process lock. Exit if another instance is running."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            # Check if the old process is still running
            if _is_process_alive(old_pid):
                logger.error(
                    "Another agent instance is already running (PID %d). "
                    "Kill it first or delete %s to force start.",
                    old_pid, LOCK_FILE,
                )
                sys.exit(1)
            else:
                logger.warning("Stale lock file found (PID %d not running). Overwriting.", old_pid)
        except (ValueError, OSError):
            logger.warning("Corrupt lock file. Overwriting.")

    # Write our PID
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(_release_lock)
    logger.info("Process lock acquired (PID %d)", os.getpid())


def _release_lock() -> None:
    """Release the process lock on exit."""
    try:
        if LOCK_FILE.exists():
            stored_pid = int(LOCK_FILE.read_text().strip())
            if stored_pid == os.getpid():
                LOCK_FILE.unlink()
                logger.info("Process lock released")
    except (ValueError, OSError):
        pass


def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
