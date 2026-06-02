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


def test_acquire_lock_accepts_custom_process_marker(tmp_path: Path) -> None:
    """SPEC-Z8 (2026-06-03): process_marker parametresi ile çağrı çalışır.

    Lab_v2 'lab_v2.start' marker'ı ile çağırıyor — default 'src.main' yerine.
    Bu test sadece API uyumluluğunu doğrular (lab marker geçince crash yok,
    stale detection ona göre çalışır).
    """
    lock = tmp_path / "lab_v2.lock"
    acquire_lock(lock_path=lock, process_marker="lab_v2.start")
    assert lock.exists()
    assert int(lock.read_text().strip()) == os.getpid()


def test_is_agent_alive_marker_mismatch_returns_false() -> None:
    """SPEC-Z8: yanlış marker ile PID kontrolü → False (stale sayılır).

    Eski bug: lab process'inin PID'i lock'ta var, ama _is_agent_alive default
    'src.main' arıyor → lab cmdline'ı 'lab_v2.start' içerdiği için 'src.main'
    bulunamaz → False döner → yanlışlıkla "stale" sanır. Şimdi marker doğru
    geçilebiliyor, bu davranış BEKLENEN — sadece default behavior'ı doğrular.
    """
    from src.orchestration.process_lock import _is_agent_alive
    # Current PID gerçekten ayakta (test çalışıyor)
    my_pid = os.getpid()
    # Default marker "src.main" — pytest cmdline'ında yok → False beklenir
    # (Bu test'in amacı: marker parametresi gerçekten cmdline match'ine etki ediyor)
    assert _is_agent_alive(my_pid, marker="DEFINITELY_NOT_IN_CMDLINE_xyz123") is False
