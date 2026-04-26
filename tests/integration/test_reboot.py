"""scripts/reboot.py için integration testler — process spawn olmadan, file+mock tabanlı."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts.reboot import (
    clear_runtime_logs,
    kill_processes,
    reload_bot,
    reset_state,
    reboot,
    start_bot,
    start_dashboard,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid), encoding="utf-8")


# ─── kill_processes ───────────────────────────────────────────────────────────

def test_reboot_kills_processes(tmp_path: Path) -> None:
    """PID dosyaları varsa ve process yaşıyorsa → kill çağrılır, PID dosyaları silinir."""
    agent_pid = tmp_path / "agent.pid"
    dash_pid = tmp_path / "dashboard.pid"
    _write_pid(agent_pid, 9991)
    _write_pid(dash_pid, 9992)

    with (
        patch("scripts.reboot._is_pid_alive", return_value=True),
        patch("scripts.reboot.subprocess.run") as mock_kill,
        patch("scripts.reboot.time.sleep"),
    ):
        kill_processes(pid_files=[agent_pid, dash_pid])

    assert mock_kill.call_count == 2
    assert not agent_pid.exists()
    assert not dash_pid.exists()


def test_kill_stale_pid_no_kill_called(tmp_path: Path) -> None:
    """Process yaşamıyorsa kill çağrılmaz, PID dosyası yine silinir."""
    pid_file = tmp_path / "agent.pid"
    _write_pid(pid_file, 9999)

    with (
        patch("scripts.reboot._is_pid_alive", return_value=False),
        patch("scripts.reboot.subprocess.run") as mock_kill,
        patch("scripts.reboot.time.sleep"),
    ):
        kill_processes(pid_files=[pid_file])

    mock_kill.assert_not_called()
    assert not pid_file.exists()


def test_kill_missing_pid_file_no_error(tmp_path: Path) -> None:
    """PID dosyası yoksa hata fırlatmadan geçer."""
    missing = tmp_path / "agent.pid"
    with patch("scripts.reboot.time.sleep"):
        kill_processes(pid_files=[missing])  # should not raise


# ─── clear_runtime_logs ───────────────────────────────────────────────────────

def test_clear_runtime_logs_empties_nonempty_file(tmp_path: Path) -> None:
    """İçerikli runtime log dosyası boşaltılır, dosya yerinde kalır."""
    log_file = tmp_path / "bot.log"
    log_file.write_text("some log data\n", encoding="utf-8")

    clear_runtime_logs(log_files=[log_file])

    assert log_file.exists()
    assert log_file.stat().st_size == 0


def test_clear_runtime_logs_creates_missing_file(tmp_path: Path) -> None:
    """Olmayan runtime log dosyası için boş dosya oluşturulur."""
    log_file = tmp_path / "runtime" / "skipped_trades.jsonl"

    clear_runtime_logs(log_files=[log_file])

    assert log_file.exists()
    assert log_file.stat().st_size == 0


def test_clear_runtime_logs_empty_file_untouched(tmp_path: Path) -> None:
    """Zaten boş olan dosyaya dokunulur ama içerik değişmez."""
    log_file = tmp_path / "dashboard.log"
    log_file.touch()

    clear_runtime_logs(log_files=[log_file])

    assert log_file.exists()
    assert log_file.stat().st_size == 0


# ─── audit/ dosyaları dokunulmaz ─────────────────────────────────────────────

def test_audit_files_untouched_on_reboot(tmp_path: Path) -> None:
    """Reboot: clear_runtime_logs sadece runtime dosyalarını etkiler; audit/ korunur."""
    audit_file = tmp_path / "audit" / "trade_history.jsonl"
    audit_file.parent.mkdir(parents=True)
    audit_file.write_text('{"trade":1}\n', encoding="utf-8")

    runtime_file = tmp_path / "runtime" / "bot.log"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("log data\n", encoding="utf-8")

    clear_runtime_logs(log_files=[runtime_file])

    # Audit içeriği bozulmadı
    assert audit_file.read_text(encoding="utf-8") == '{"trade":1}\n'
    # Runtime temizlendi
    assert runtime_file.stat().st_size == 0


# ─── reset_state ──────────────────────────────────────────────────────────────

def test_reboot_resets_state(tmp_path: Path) -> None:
    """State dosyaları silinir."""
    positions = tmp_path / "positions.json"
    breaker = tmp_path / "circuit_breaker_state.json"
    positions.write_text('{"open":[]}', encoding="utf-8")
    breaker.write_text('{"state":"ok"}', encoding="utf-8")

    reset_state(state_files=[positions, breaker])

    assert not positions.exists()
    assert not breaker.exists()


def test_reset_state_missing_file_no_error(tmp_path: Path) -> None:
    """Olmayan state dosyası için hata fırlatmaz."""
    missing = tmp_path / "not_exists.json"
    reset_state(state_files=[missing])  # should not raise


# ─── reload koruma ────────────────────────────────────────────────────────────

def test_reload_preserves_state(tmp_path: Path) -> None:
    """Reload: kill + start; state dosyalarına dokunmaz."""
    positions = tmp_path / "positions.json"
    positions.write_text('{"open":[{"id":"x"}]}', encoding="utf-8")

    with (
        patch("scripts.reboot.kill_processes"),
        patch("scripts.reboot.start_dashboard"),
        patch("scripts.reboot.start_bot"),
        patch("scripts.reboot.time.sleep"),
    ):
        reload_bot("dry_run")

    assert positions.exists()
    assert positions.read_text(encoding="utf-8") == '{"open":[{"id":"x"}]}'


def test_reload_only_restarts() -> None:
    """Reload: kill + dashboard + bot çağrılır; clear_runtime_logs/reset_state çağrılmaz."""
    with (
        patch("scripts.reboot.kill_processes") as mock_kill,
        patch("scripts.reboot.start_dashboard") as mock_dash,
        patch("scripts.reboot.start_bot") as mock_bot,
        patch("scripts.reboot.clear_runtime_logs") as mock_clear,
        patch("scripts.reboot.reset_state") as mock_reset,
        patch("scripts.reboot.time.sleep"),
    ):
        reload_bot("dry_run")

    mock_kill.assert_called_once()
    mock_dash.assert_called_once()
    mock_bot.assert_called_once_with("dry_run")
    mock_clear.assert_not_called()
    mock_reset.assert_not_called()


# ─── tekillik garantisi ───────────────────────────────────────────────────────

def test_no_stacking(tmp_path: Path) -> None:
    """2 kez reboot çağrıldığında önceki PID kill edilir → stacklenme yok."""
    agent_pid = tmp_path / "agent.pid"
    dash_pid = tmp_path / "dashboard.pid"

    killed_pids: list[int] = []

    def fake_kill_processes(pid_files: list[Path] | None = None) -> None:
        files = pid_files or [agent_pid, dash_pid]
        for f in files:
            if f.exists():
                try:
                    killed_pids.append(int(f.read_text().strip()))
                except ValueError:
                    pass
                f.unlink(missing_ok=True)

    def fake_start_bot(mode: str = "dry_run", root=None) -> None:
        agent_pid.write_text("7777", encoding="utf-8")

    def fake_start_dashboard(root=None) -> None:
        dash_pid.write_text("7778", encoding="utf-8")

    with (
        patch("scripts.reboot.kill_processes", side_effect=fake_kill_processes),
        patch("scripts.reboot.start_bot", side_effect=fake_start_bot),
        patch("scripts.reboot.start_dashboard", side_effect=fake_start_dashboard),
        patch("scripts.reboot.clear_runtime_logs"),
        patch("scripts.reboot.reset_state"),
        patch("scripts.reboot.time.sleep"),
    ):
        reboot("dry_run")  # 1. çağrı: PID 7777 + 7778 oluşur
        reboot("dry_run")  # 2. çağrı: 7777 + 7778 kill edilmeli

    assert 7777 in killed_pids, f"Agent PID 7777 kill edilmedi. Killed: {killed_pids}"
    assert 7778 in killed_pids, f"Dashboard PID 7778 kill edilmedi. Killed: {killed_pids}"
