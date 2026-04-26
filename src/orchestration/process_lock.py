"""Tek instance process lock (PID file tabanlı).

İki bot aynı anda çalışmasın — aynı cüzdan, çift order, çift pozisyon = felaket.
Lock file: logs/agent.pid. PID file varsa ve süreç yaşıyorsa → exit.
"""
from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

LOCK_FILE = Path("logs/agent.pid")


def acquire_lock(lock_path: Path | None = None) -> None:
    """Lock al. Başka instance aktifse sys.exit(1)."""
    path = lock_path or LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            old_pid = int(path.read_text(encoding="utf-8").strip())
            if old_pid == os.getpid():
                return  # Same process re-acquiring
            if _is_agent_alive(old_pid):
                logger.error(
                    "Another agent already running (PID %d). Kill it or delete %s.",
                    old_pid, path,
                )
                sys.exit(1)
            logger.warning("Stale lock file (PID %d not alive). Overwriting.", old_pid)
        except (ValueError, OSError):
            logger.warning("Corrupt lock file. Overwriting.")

    path.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(lambda: _release(path))
    logger.info("Process lock acquired (PID %d)", os.getpid())


def _release(path: Path) -> None:
    try:
        if path.exists():
            stored = int(path.read_text(encoding="utf-8").strip())
            if stored == os.getpid():
                path.unlink()
                logger.info("Process lock released")
    except (ValueError, OSError):
        pass


def _is_agent_alive(pid: int) -> bool:
    """PID yaşıyor ve 'src.main' içeren komut satırı varsa True."""
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return "src.main" in result.stdout
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
