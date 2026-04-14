"""process_lock.py için birim testler."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.orchestration.process_lock import acquire_lock


def test_acquire_creates_pid_file(tmp_path: Path) -> None:
    lock = tmp_path / "agent.pid"
    acquire_lock(lock_path=lock)
    assert lock.exists()
    assert int(lock.read_text().strip()) == os.getpid()


def test_same_pid_reacquire_noop(tmp_path: Path) -> None:
    lock = tmp_path / "agent.pid"
    acquire_lock(lock_path=lock)
    # Tekrar aynı PID ile → noop
    acquire_lock(lock_path=lock)
    assert int(lock.read_text().strip()) == os.getpid()


def test_stale_lock_overwritten(tmp_path: Path) -> None:
    # Yaşamayan PID (çok büyük) → stale, üzerine yaz
    lock = tmp_path / "agent.pid"
    lock.write_text("999999999", encoding="utf-8")
    acquire_lock(lock_path=lock)
    assert int(lock.read_text().strip()) == os.getpid()


def test_corrupt_lock_overwritten(tmp_path: Path) -> None:
    lock = tmp_path / "agent.pid"
    lock.write_text("not_a_number", encoding="utf-8")
    acquire_lock(lock_path=lock)
    assert int(lock.read_text().strip()) == os.getpid()
