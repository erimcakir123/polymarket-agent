"""scripts/reboot_tennis.py — kill + wipe testleri (FIX 5).

Process spawn yok — file + mock tabanlı. Asıl kill çağrısının yapıldığını
doğrular + --wipe modunda state dosyalarının arşiv dizinine taşındığını test
eder.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.reboot_tennis import archive_state, kill_tennis


def _write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid), encoding="utf-8")


# ── kill_tennis ───────────────────────────────────────────────────────────────


def test_reboot_script_kills_pid(tmp_path: Path) -> None:
    """PID dosyası var + process yaşıyor → kill çağrılır, PID dosyası silinir."""
    pid_file = tmp_path / "agent.pid"
    _write_pid(pid_file, 7777)

    with (
        patch("scripts.reboot_tennis._is_pid_alive", return_value=True),
        patch("scripts.reboot_tennis.subprocess.run") as mock_kill,
        patch("scripts.reboot_tennis.time.sleep"),
    ):
        killed = kill_tennis(pid_file=pid_file)

    assert killed == 7777
    assert mock_kill.call_count == 1
    assert not pid_file.exists()


def test_kill_tennis_stale_pid_no_kill(tmp_path: Path) -> None:
    """Process yaşamıyorsa kill çağrılmaz, PID dosyası yine silinir."""
    pid_file = tmp_path / "agent.pid"
    _write_pid(pid_file, 8888)

    with (
        patch("scripts.reboot_tennis._is_pid_alive", return_value=False),
        patch("scripts.reboot_tennis.subprocess.run") as mock_kill,
        patch("scripts.reboot_tennis.time.sleep"),
    ):
        killed = kill_tennis(pid_file=pid_file)

    assert killed is None
    assert mock_kill.call_count == 0
    assert not pid_file.exists()


def test_kill_tennis_no_pid_file(tmp_path: Path) -> None:
    """PID dosyası yoksa hata vermez, None döner."""
    pid_file = tmp_path / "agent.pid"
    with patch("scripts.reboot_tennis.time.sleep"):
        killed = kill_tennis(pid_file=pid_file)
    assert killed is None


# ── archive_state (--wipe) ────────────────────────────────────────────────────


def test_reboot_wipe_archives_state(tmp_path: Path) -> None:
    """--wipe: state dosyaları + log dizinleri _pre_reboot_<TS>/ altına taşınır."""
    # Setup: state dosyaları + log dizinleri oluştur
    (tmp_path / "data").mkdir()
    (tmp_path / "logs" / "audit").mkdir(parents=True)
    (tmp_path / "logs" / "session").mkdir(parents=True)

    positions = tmp_path / "data" / "positions.json"
    bot_status = tmp_path / "data" / "bot_status.json"
    positions.write_text(json.dumps({"positions": []}), encoding="utf-8")
    bot_status.write_text(json.dumps({"cycle": "light"}), encoding="utf-8")

    audit_file = tmp_path / "logs" / "audit" / "trades.jsonl"
    audit_file.write_text('{"trade": "test"}\n', encoding="utf-8")

    state_files = [positions, bot_status]
    log_dirs = [tmp_path / "logs" / "audit", tmp_path / "logs" / "session"]

    # Act
    data_archive, logs_archive = archive_state(
        state_files=state_files,
        log_dirs=log_dirs,
        timestamp="20260520_120000",
        root=tmp_path,
    )

    # Assert: orijinal dosyalar yok, arşivde var
    assert not positions.exists()
    assert not bot_status.exists()
    assert (data_archive / "positions.json").exists()
    assert (data_archive / "bot_status.json").exists()

    # Log dizinleri arşive taşındı + yenisi boş yeniden oluşturuldu
    assert (logs_archive / "audit" / "trades.jsonl").exists()
    assert (tmp_path / "logs" / "audit").exists()  # yeniden oluştu
    assert not any((tmp_path / "logs" / "audit").iterdir())  # ama boş


def test_wipe_skips_nonexistent_files(tmp_path: Path) -> None:
    """Dosya/dizin yoksa hata vermez, sessizce atlar."""
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    state_files = [tmp_path / "data" / "nonexistent.json"]
    log_dirs = [tmp_path / "logs" / "nonexistent_dir"]

    # Hata fırlatmamalı
    data_archive, logs_archive = archive_state(
        state_files=state_files,
        log_dirs=log_dirs,
        timestamp="20260520_120000",
        root=tmp_path,
    )
    # Arşiv dizini oluşturuldu ama boş
    assert data_archive.exists()
    assert logs_archive.exists()
