"""Bot ve dashboard için reload/reboot kontrol scripti.

RELOAD: Graceful kill + state DOKUNMAZ + yeniden başlat.
REBOOT: Graceful kill + runtime logları temizle + state sıfırla + yeniden başlat.

Dizin yapısı:
  logs/runtime/  — reboot'ta temizlenir (bot.log, dashboard.log, skipped_trades.jsonl)
  logs/audit/    — ASLA dokunulmaz (trade_history, exits, score_events, match_results, equity_history, counterfactual)
  data/          — state dosyaları (positions, circuit_breaker, stock_queue, bot_status, blacklist)
  logs/          — PID dosyaları (agent.pid, dashboard.pid)

Tekillik garantisi: agent.pid + dashboard.pid kontrolü — stacklenme yok.

Kullanım:
  python scripts/reboot.py reload
  python scripts/reboot.py reboot
  python scripts/reboot.py reboot --mode live
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent

_AGENT_PID_FILE = ROOT / "logs" / "agent.pid"
_DASHBOARD_PID_FILE = ROOT / "logs" / "dashboard.pid"

# REBOOT'ta sıfırlanan state dosyaları (silindi → fresh state)
_STATE_FILES_DELETE = [
    ROOT / "data" / "circuit_breaker_state.json",
    ROOT / "data" / "positions.json",
    ROOT / "data" / "stock_queue.json",
    ROOT / "data" / "bot_status.json",
]

# REBOOT'ta temizlenen runtime log dosyaları (içeriği boşaltılır, arşiv yok)
_RUNTIME_LOG_FILES = [
    ROOT / "logs" / "runtime" / "bot.log",
    ROOT / "logs" / "runtime" / "dashboard.log",
    ROOT / "logs" / "runtime" / "skipped_trades.jsonl",
]

_GRACEFUL_WAIT_SECONDS = 2


_BOT_CMDLINE_MARKER = "src.main"
_DASHBOARD_CMDLINE_MARKER = "src.presentation.dashboard"


def _is_pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return str(pid) in result.stdout
        except (subprocess.TimeoutExpired, OSError):
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _find_pids_by_cmdline(marker: str) -> list[int]:
    """Command line'ında marker geçen tüm Python PID'lerini döndür."""
    my_pid = os.getpid()
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["wmic", "process", "where", "name='python.exe'",
                 "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            pids = []
            for line in result.stdout.splitlines():
                if marker in line:
                    parts = line.strip().split(",")
                    for part in reversed(parts):
                        try:
                            pid = int(part.strip())
                            if pid != my_pid:
                                pids.append(pid)
                            break
                        except ValueError:
                            continue
            return pids
        except (subprocess.TimeoutExpired, OSError):
            return []
    # Linux/Mac: use ps
    try:
        result = subprocess.run(
            ["ps", "ax", "-o", "pid,command"],
            capture_output=True, text=True, timeout=10,
        )
        pids = []
        for line in result.stdout.splitlines():
            if marker in line:
                try:
                    pid = int(line.strip().split()[0])
                    if pid != my_pid:
                        pids.append(pid)
                except (ValueError, IndexError):
                    continue
        return pids
    except (subprocess.TimeoutExpired, OSError):
        return []


def _kill_pid(pid: int, label: str) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/pid", str(pid), "/f"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        os.kill(pid, __import__("signal").SIGTERM)
    print(f"  Killed PID {pid} ({label})")


def kill_processes(
    pid_files: list[Path] | None = None,
) -> None:
    """Tüm bot ve dashboard process'lerini durdur.

    Önce cmdline taramasıyla TÜM eski instance'ları öldürür (PID file
    olmayan eski process'ler dahil), ardından stale PID file'ları temizler.
    pid_files parametresi sadece test injection içindir.
    """
    if pid_files is not None:
        # Test modu: sadece verilen PID dosyalarını işle
        for pid_file in pid_files:
            if not pid_file.exists():
                continue
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pid_file.unlink(missing_ok=True)
                continue
            if _is_pid_alive(pid):
                _kill_pid(pid, pid_file.name)
            else:
                print(f"  Stale PID {pid} ({pid_file.name}) — process zaten durmuş")
            pid_file.unlink(missing_ok=True)
        time.sleep(_GRACEFUL_WAIT_SECONDS)
        return

    # Production modu: cmdline tarama ile tüm instance'ları bul
    killed: set[int] = set()
    for marker, label in [
        (_BOT_CMDLINE_MARKER, "bot"),
        (_DASHBOARD_CMDLINE_MARKER, "dashboard"),
    ]:
        for pid in _find_pids_by_cmdline(marker):
            if pid not in killed:
                _kill_pid(pid, label)
                killed.add(pid)

    # Stale PID dosyalarını temizle
    for pid_file in [_AGENT_PID_FILE, _DASHBOARD_PID_FILE]:
        pid_file.unlink(missing_ok=True)

    time.sleep(_GRACEFUL_WAIT_SECONDS)


def clear_runtime_logs(log_files: list[Path] | None = None) -> None:
    """Runtime log dosyalarını boşalt (audit/ asla dokunulmaz)."""
    files = log_files if log_files is not None else _RUNTIME_LOG_FILES
    for log_file in files:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if log_file.exists() and log_file.stat().st_size > 0:
            log_file.write_bytes(b"")
            print(f"  Cleared: {log_file.name}")
        else:
            log_file.touch()


def reset_state(state_files: list[Path] | None = None) -> None:
    """State dosyalarını sil (fresh state için)."""
    files = state_files if state_files is not None else _STATE_FILES_DELETE
    for state_file in files:
        if state_file.exists():
            state_file.unlink()
            print(f"  Removed state: {state_file.name}")


def start_dashboard(root: Path | None = None) -> None:
    """Dashboard'u ayrı process'te başlat."""
    r = root or ROOT
    cmd = [sys.executable, "-m", "src.presentation.dashboard.app"]
    if sys.platform == "win32":
        subprocess.Popen(
            cmd, cwd=str(r),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
    else:
        subprocess.Popen(cmd, cwd=str(r), start_new_session=True)
    print("  Dashboard started")


def start_bot(mode: str = "dry_run", root: Path | None = None) -> None:
    """Bot'u ayrı process'te başlat."""
    r = root or ROOT
    cmd = [sys.executable, "-m", "src.main", "--mode", mode]
    if sys.platform == "win32":
        subprocess.Popen(
            cmd, cwd=str(r),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
    else:
        subprocess.Popen(cmd, cwd=str(r), start_new_session=True)
    print(f"  Bot started (mode={mode})")


def reload_bot(mode: str = "dry_run") -> None:
    """RELOAD: State korunur, sadece process restart."""
    print("=== RELOAD ===")
    kill_processes()
    start_dashboard()
    time.sleep(3)
    start_bot(mode)
    print("Reload complete.")


def reboot(mode: str = "dry_run") -> None:
    """REBOOT: Tam temizlik + yeniden başlat."""
    print("=== REBOOT ===")
    kill_processes()
    clear_runtime_logs()
    reset_state()
    start_dashboard()
    time.sleep(3)
    start_bot(mode)
    print("Reboot complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot reload/reboot kontrolü")
    parser.add_argument("action", choices=["reload", "reboot"])
    parser.add_argument("--mode", default="dry_run", choices=["dry_run", "live"])
    args = parser.parse_args()

    if args.action == "reboot":
        reboot(args.mode)
    else:
        reload_bot(args.mode)
