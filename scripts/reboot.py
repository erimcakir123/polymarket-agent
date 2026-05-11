"""Bot ve dashboard için reload/reboot kontrol scripti.

RELOAD: Graceful kill + state/audit DOKUNMAZ + yeniden başlat.
REBOOT: Graceful kill + runtime + session + state + AUDIT temizle + yeniden başlat (gerçek factory reset).

Dizin yapısı:
  logs/runtime/  — reboot'ta temizlenir (bot.log, dashboard.log, skipped_trades.jsonl)
  logs/session/  — reboot'ta temizlenir (audit aynası — dashboard kaynağı)
  logs/audit/    — REBOOT'ta temizlenir (kullanıcı kararı 2026-05-05); reload korur
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
    ROOT / "data" / "blacklist.json",
]

# REBOOT'ta temizlenen runtime log dosyaları (içeriği boşaltılır, arşiv yok)
_RUNTIME_LOG_FILES = [
    ROOT / "logs" / "runtime" / "bot.log",
    ROOT / "logs" / "runtime" / "dashboard.log",
    ROOT / "logs" / "runtime" / "skipped_trades.jsonl",
]

# REBOOT'ta temizlenen audit dosyaları (kullanıcı kararı 2026-05-05: gerçek factory reset)
_AUDIT_FILES_CLEAR = [
    ROOT / "logs" / "audit" / "trade_history.jsonl",
    ROOT / "logs" / "audit" / "equity_history.jsonl",
    ROOT / "logs" / "audit" / "exits.jsonl",
    ROOT / "logs" / "audit" / "score_events.jsonl",
    ROOT / "logs" / "audit" / "match_results.jsonl",
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
    """Runtime log dosyalarını boşalt (audit/ asla dokunulmaz).

    Bot.log için rotate'lenmiş suffix'leri (bot.log.1, .2, ...) de temizler —
    aksi halde "clean start" semantiği ihlal olur ve 30MB+ eski log birikir.
    """
    files = log_files if log_files is not None else _RUNTIME_LOG_FILES
    for log_file in files:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if log_file.exists() and log_file.stat().st_size > 0:
            log_file.write_bytes(b"")
            print(f"  Cleared: {log_file.name}")
        else:
            log_file.touch()
        # Rotate'lenmiş suffix'leri sil (bot.log.1, bot.log.2, ...)
        # RotatingFileHandler bunlari oluşturur; reboot temizliği bunlari da kapsamalı.
        for rotated in log_file.parent.glob(f"{log_file.name}.*"):
            rotated.unlink(missing_ok=True)
            print(f"  Removed rotated: {rotated.name}")


def reset_state(state_files: list[Path] | None = None) -> None:
    """State dosyalarını sil (fresh state için)."""
    files = state_files if state_files is not None else _STATE_FILES_DELETE
    for state_file in files:
        if state_file.exists():
            state_file.unlink()
            print(f"  Removed state: {state_file.name}")


def clear_audit_logs(audit_files: list[Path] | None = None) -> None:
    """Audit log dosyalarını sil (gerçek factory reset — kullanıcı kararı 2026-05-05).

    Daha önce audit ASLA dokunulmazdı; kullanıcı reboot'un tam wipe olmasını istiyor.
    Reload bu fonksiyonu çağırmaz, sadece reboot.
    """
    files = audit_files if audit_files is not None else _AUDIT_FILES_CLEAR
    for audit_file in files:
        if audit_file.exists():
            audit_file.unlink()
            print(f"  Removed audit: {audit_file.name}")


def archive_audit_logs(
    audit_files: list[Path] | None = None,
    timestamp: str | None = None,
) -> None:
    """Reboot'ta audit dosyalarını rename ile arşivle — silmez, taşır.

    2026-05-11 fix: SPEC-E _reconcile_realized_pnl audit'i ground truth okuyor.
    Reboot audit'i korusa da bot startup'ta audit'ten realized_pnl'i geri inşa
    ediyordu → "clean start" semantiği ihlal. Bu fonksiyon mevcut audit'i
    `<name>.archive.YYYYMMDD_HHMMSS.jsonl` olarak rename eder; yeni session boş
    audit ile başlar, eski archive forensic erişim için kalır.
    """
    from datetime import datetime, timezone

    files = audit_files if audit_files is not None else _AUDIT_FILES_CLEAR
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for audit_file in files:
        if audit_file.exists() and audit_file.stat().st_size > 0:
            archived = audit_file.with_name(
                f"{audit_file.stem}.archive.{stamp}{audit_file.suffix}",
            )
            audit_file.rename(archived)
            print(f"  Archived: {audit_file.name} -> {archived.name}")


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


def clear_session_logs(session_dir: Path | None = None) -> None:
    """Session log dosyalarını sil (display layer — audit/ asla dokunulmaz)."""
    d = session_dir if session_dir is not None else ROOT / "logs" / "session"
    if not d.exists():
        return
    for f in d.glob("*.jsonl"):
        f.unlink()
        print(f"  Cleared session log: {f.name}")


def reboot(mode: str = "dry_run", skip_confirm: bool = False) -> None:
    """REBOOT: state + session + runtime sıfırlanır. AUDIT KORUNUR (kalıcı arşiv).

    Audit tamamen silinmek istenirse manuel olarak `clear_audit_logs()` çağrılmalı
    veya dosyalar elle silinmeli (--include-audit flag yok, kazara silmeyi önler).
    """
    print("=== REBOOT ===")
    if not skip_confirm:
        print("\n⚠️  UYARI: Bu işlem state + session + runtime log'ları SİLER.")
        print("   - data/positions.json, data/circuit_breaker_state.json (state)")
        print("   - logs/session/* (dashboard kaynağı)")
        print("   - logs/runtime/* (bot.log)")
        print("   AUDIT KORUNUR (logs/audit/* — tarihsel arşiv).\n")
        try:
            answer = input("Onayla 'REBOOT' yaz (başka bir şey iptal eder): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("İptal edildi.")
            return
        if answer != "REBOOT":
            print("İptal — state korundu. (`reload` istiyor olabilirsin?)")
            return
    kill_processes()
    clear_runtime_logs()
    clear_session_logs()
    # NOT: clear_audit_logs() çağrılmıyor — audit kalıcı arşiv (SPEC-H 2026-05-10).
    # AMA mevcut audit dosyaları rename ile archive'lenir (2026-05-11 fix):
    # SPEC-E reconcile_realized_pnl audit'i ground truth okuyordu, reboot sonrası
    # realized_pnl audit'ten geri inşa ediliyordu → "clean start" ihlal.
    # Archive ile audit veri kaybolmaz ama yeni session boş audit ile başlar.
    archive_audit_logs()
    reset_state()
    start_dashboard()
    time.sleep(3)
    start_bot(mode)
    print("Reboot complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot reload/reboot kontrolü")
    parser.add_argument("action", choices=["reload", "reboot"])
    parser.add_argument("--mode", default="dry_run", choices=["dry_run", "live"])
    parser.add_argument("--yes", action="store_true",
                        help="Reboot onayını bypass et (audit silme uyarısını atla)")
    args = parser.parse_args()

    if args.action == "reboot":
        reboot(args.mode, skip_confirm=args.yes)
    else:
        reload_bot(args.mode)
