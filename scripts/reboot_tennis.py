"""Tennis bot için kill / reload / wipe kontrol scripti (FIX 5 — 2026-05-20).

Tennis agent ana bot'tan ayrı process'te çalışıyor (cmdline marker:
'tennis_main'). PID'i logs/agent.pid'de tutuluyor. Manuel `taskkill /PID`
yerine bu script kullanılır.

Kullanım:
    python scripts/reboot_tennis.py            # Sadece kill
    python scripts/reboot_tennis.py --reload   # Kill + restart (state korunur)
    python scripts/reboot_tennis.py --wipe     # Kill + arşivle + restart (clean slate)

--wipe: data/positions.json + bot_status.json + circuit_breaker_state.json +
audit/session/runtime log'larını `data/_pre_reboot_<TS>/` ve
`logs/_pre_reboot_<TS>/` altına taşır (silinmez — recovery için).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Tennis agent kimliği — main bot (src.main) ile karışmasın.
TENNIS_CMDLINE_MARKER = "tennis_main"
TENNIS_PID_FILE = ROOT / "logs" / "agent.pid"

# --wipe modunda arşivlenecek state dosyaları (silinmez, taşınır).
_WIPE_STATE_FILES = [
    ROOT / "data" / "positions.json",
    ROOT / "data" / "bot_status.json",
    ROOT / "data" / "circuit_breaker_state.json",
    ROOT / "data" / "blacklist.json",
    ROOT / "data" / "stock_queue.json",
]

# --wipe modunda arşivlenecek log dizinleri (içerik taşınır).
_WIPE_LOG_DIRS = [
    ROOT / "logs" / "audit",
    ROOT / "logs" / "session",
    ROOT / "logs" / "runtime",
    ROOT / "logs" / "tennis_diagnostics",
]

_GRACEFUL_WAIT_SECONDS = 2


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


def _kill_pid(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/pid", str(pid), "/f"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        os.kill(pid, __import__("signal").SIGTERM)
    print(f"  Killed PID {pid}")


def kill_tennis(pid_file: Path | None = None) -> int | None:
    """Tennis agent'ı durdur. PID dosyasından oku; yoksa cmdline tara.

    Returns:
        Öldürülen PID (yoksa None).
    """
    pf = pid_file if pid_file is not None else TENNIS_PID_FILE
    killed: int | None = None
    if pf.exists():
        try:
            pid = int(pf.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pid = None
        if pid is not None:
            if _is_pid_alive(pid):
                _kill_pid(pid)
                killed = pid
            else:
                print(f"  Stale PID {pid} ({pf.name}) — process zaten durmuş")
        pf.unlink(missing_ok=True)

    if killed is None:
        print(f"  PID dosyası yok / stale — cmdline tarama ({TENNIS_CMDLINE_MARKER!r})")
    time.sleep(_GRACEFUL_WAIT_SECONDS)
    return killed


def archive_state(
    state_files: list[Path] | None = None,
    log_dirs: list[Path] | None = None,
    timestamp: str | None = None,
    root: Path | None = None,
) -> tuple[Path, Path]:
    """State + log'ları `_pre_reboot_<TS>` altına taşı.

    Silmez — kullanıcı kaybettiği bir pozisyonu / log'u geri getirebilir.

    Returns:
        (data_archive_dir, logs_archive_dir) yolları.
    """
    files = state_files if state_files is not None else _WIPE_STATE_FILES
    dirs = log_dirs if log_dirs is not None else _WIPE_LOG_DIRS
    r = root if root is not None else ROOT
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    data_archive = r / "data" / f"_pre_reboot_{stamp}"
    logs_archive = r / "logs" / f"_pre_reboot_{stamp}"
    data_archive.mkdir(parents=True, exist_ok=True)
    logs_archive.mkdir(parents=True, exist_ok=True)

    for sf in files:
        if sf.exists():
            shutil.move(str(sf), str(data_archive / sf.name))
            print(f"  Archived state: {sf.name} -> {data_archive.name}/{sf.name}")

    for ld in dirs:
        if ld.exists() and any(ld.iterdir()):
            target = logs_archive / ld.name
            shutil.move(str(ld), str(target))
            ld.mkdir(parents=True, exist_ok=True)
            print(f"  Archived logs: {ld.name}/* -> {logs_archive.name}/{ld.name}/")

    return data_archive, logs_archive


def start_tennis_bot(interval_sec: int = 1800, root: Path | None = None) -> None:
    """Tennis agent'ı yeni process'te başlat.

    FIX (2026-05-22): stdout/stderr tennis_run.out'a redirect — detached process
    konsola yazma yetisini kaybediyordu; print/traceback kayıpları engellenir.
    """
    r = root if root is not None else ROOT
    cmd = [sys.executable, "scripts/tennis_main.py", "--run", "--interval", str(interval_sec)]
    stdout_path = r / "logs" / "tennis_run.out"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_file = stdout_path.open("a", encoding="utf-8")
    if sys.platform == "win32":
        subprocess.Popen(
            cmd, cwd=str(r),
            stdout=stdout_file, stderr=subprocess.STDOUT,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
    else:
        subprocess.Popen(
            cmd, cwd=str(r),
            stdout=stdout_file, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    print(f"  Tennis bot started (interval={interval_sec}s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tennis bot kill / reload / wipe")
    parser.add_argument("--reload", action="store_true", help="Kill + restart (state korunur)")
    parser.add_argument("--wipe", action="store_true", help="Kill + arşivle + restart (clean slate)")
    parser.add_argument("--interval", type=int, default=1800, help="Heavy cycle interval (s)")
    args = parser.parse_args()

    if args.reload and args.wipe:
        print("HATA: --reload ve --wipe aynı anda kullanılamaz.")
        sys.exit(1)

    print("=== TENNIS REBOOT ===")
    killed = kill_tennis()
    if killed:
        print(f"Tennis bot durduruldu (PID {killed}).")
    else:
        print("Tennis bot zaten durmuştu.")

    if args.wipe:
        print("\n--wipe: state + log arşivleme...")
        data_dir, logs_dir = archive_state()
        print(f"Arşiv: data/{data_dir.name}/ + logs/{logs_dir.name}/")

    if args.reload or args.wipe:
        print("\nRestarting...")
        start_tennis_bot(interval_sec=args.interval)
        print("Reboot complete.")
    else:
        print("(--reload veya --wipe verilmediği için restart edilmedi.)")


if __name__ == "__main__":
    main()
