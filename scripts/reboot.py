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
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent

_AGENT_PID_FILE = ROOT / "logs" / "agent.pid"
_DASHBOARD_PID_FILE = ROOT / "logs" / "dashboard.pid"
_POSITIONS_FILE = ROOT / "data" / "positions.json"
_TRADE_HISTORY_FILENAME = "trade_history.jsonl"

# REBOOT'ta sıfırlanan state dosyaları (silindi → fresh state)
_STATE_FILES_DELETE = [
    ROOT / "data" / "circuit_breaker_state.json",
    ROOT / "data" / "positions.json",
    ROOT / "data" / "stock_queue.json",
    ROOT / "data" / "bot_status.json",
    ROOT / "data" / "blacklist.json",
    # session_start.json: reboot siler -> bootstrap yeniden olusturur (yeni session
    # zaman damgasi). Reload bu listeyi kullanmaz -> dashboard topbar'inda
    # gosterilen "session basladi" zamani reload boyunca sabit kalir.
    ROOT / "data" / "session_start.json",
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


def _read_open_condition_ids(positions_file: Path | None = None) -> set[str]:
    """data/positions.json'dan açık pozisyonların condition_id'lerini oku.
    Dosya yoksa veya bozuksa boş set döner.
    """
    p = positions_file if positions_file is not None else _POSITIONS_FILE
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    positions = data.get("positions") if isinstance(data, dict) else None
    if not isinstance(positions, dict):
        return set()
    return {cid for cid in positions.keys() if cid}


def archive_audit_logs(
    audit_files: list[Path] | None = None,
    timestamp: str | None = None,
    open_condition_ids: set[str] | None = None,
) -> None:
    """Audit dosyalarını arşivle (snapshot olarak kopyala).

    SPEC-Z7 (2026-05-25): rename → copy. Audit dosyası (trade_history.jsonl,
    equity_history.jsonl) dashboard exited tab'inin ground truth'u. Gizli bir
    scheduler periyodik olarak archive_audit_logs çağırıyor (DECISIONS 1137
    TODO investigate) — rename davranışı dashboard'ı boşaltıyordu. Copy ile
    orijinal korunur, snapshot forensic için yaratılır. Reboot mode reset_state
    ile asıl temizliği yapar; bu fonksiyon clean-start semantiğini bozmaz.

    2026-05-21: trade_history.jsonl için açık pozisyonların kayıtları audit'te
    bırakılır (kapanmış trade'ler archive'a). Açık pozisyon split mantığı yine
    `_split_trade_history` ile yapılır (orijinal trade_history yeniden yazılır
    — sadece açık kayıtlar). open_condition_ids None ise tüm audit kopyalanır.
    """
    from datetime import datetime, timezone
    import inspect  # noqa: PLC0415 — TODO-007 forensic, geçici
    # TODO-007 (2026-05-25): Gizli scheduler kim? Çağrı zincirini bas, sorun bulununca kaldır.
    _trace = " ← ".join(f"{Path(f.filename).name}:{f.lineno}" for f in inspect.stack()[1:5])
    print(f"  [TODO-007 forensic] archive_audit_logs called from: {_trace}")

    files = audit_files if audit_files is not None else _AUDIT_FILES_CLEAR
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    import shutil  # noqa: PLC0415 - lazy import for copy-on-archive path
    for audit_file in files:
        if not (audit_file.exists() and audit_file.stat().st_size > 0):
            continue
        archived = audit_file.with_name(
            f"{audit_file.stem}.archive.{stamp}{audit_file.suffix}",
        )
        if (audit_file.name == _TRADE_HISTORY_FILENAME
                and open_condition_ids is not None and open_condition_ids):
            _split_trade_history(audit_file, archived, open_condition_ids)
        else:
            # SPEC-Z7 (2026-05-25): rename → copy. Audit dosyası dashboard exited
            # tab'inin ground truth'u; otomatik archive trigger (DECISIONS satır 1137
            # "TODO investigate") rename yapinca dashboard boşaliyordu. Reboot modunda
            # reset_state sonradan siler — copy yaklaşımı reboot'u kırmaz.
            shutil.copy2(audit_file, archived)
            print(f"  Archived (copy): {audit_file.name} -> {archived.name}")


def _split_trade_history(
    audit_file: Path, archived: Path, open_cids: set[str],
) -> None:
    """trade_history.jsonl'i ikiye böl: açık pozisyonların kayıtları audit'te kalır,
    kalanı archive'a taşınır. Bozuk satırlar archive'a gönderilir (forensic için).
    """
    keep: list[str] = []
    move: list[str] = []
    for line in audit_file.read_text(encoding="utf-8").splitlines(keepends=True):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            move.append(line)
            continue
        cid = rec.get("condition_id") or ""
        if cid in open_cids:
            keep.append(line)
        else:
            move.append(line)
    if move:
        archived.write_text("".join(move), encoding="utf-8")
        print(f"  Archived: {audit_file.name} -> {archived.name} "
              f"({len(move)} closed, {len(keep)} kept open)")
    if keep:
        audit_file.write_text("".join(keep), encoding="utf-8")
    else:
        # Tüm kayıtlar kapanmış → audit dosyasını sıfırla (yeni session boş başlar)
        audit_file.write_text("", encoding="utf-8")


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


def reboot(mode: str = "dry_run", skip_confirm: bool = False, wipe_audit: bool = False) -> None:
    """REBOOT: state + session + runtime sıfırlanır. Audit varsayılan olarak
    arşivlenir (kopya), orijinaller dashboard için durur.

    wipe_audit=True ise orijinal audit dosyaları da silinir (tam fabrika sıfır) —
    arşiv kopyası zaten oluşturulduğu için veri kaybı yoktur, sadece dashboard
    eski kayıtları göstermez.
    """
    print("=== REBOOT ===")
    if not skip_confirm:
        print("\n⚠️  UYARI: Bu işlem state + session + runtime log'ları SİLER.")
        print("   - data/positions.json, data/circuit_breaker_state.json (state)")
        print("   - logs/session/* (dashboard kaynağı)")
        print("   - logs/runtime/* (bot.log)")
        if wipe_audit:
            print("   - logs/audit/* SİLİNECEK (--wipe). Arşiv kopyası saklanır.")
        else:
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
    # Audit kalıcı arşiv (SPEC-H 2026-05-10) — rename ile archive'lenir, veri
    # kaybolmaz, yeni session boş audit'le başlar.
    # 2026-05-22: open_condition_ids=None → FULL archive. reset_state() zaten
    # positions.json'ı siliyor, açık pozisyon kaydı tutmanın anlamı yok.
    archive_audit_logs(open_condition_ids=None)
    if wipe_audit:
        clear_audit_logs()
    reset_state()
    start_dashboard()
    time.sleep(3)
    start_bot(mode)
    print("Reboot complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot reload/reboot kontrolü")
    parser.add_argument("action", choices=["reload", "reboot"])
    parser.add_argument("--mode", default="dry_run", choices=["dry_run", "paper", "live"])
    parser.add_argument("--yes", action="store_true",
                        help="Reboot onayını bypass et (audit silme uyarısını atla)")
    parser.add_argument("--wipe", action="store_true",
                        help="Reboot'a ek: orijinal audit dosyalarını da sil (arşiv kopya saklanır)")
    args = parser.parse_args()

    if args.action == "reboot":
        reboot(args.mode, skip_confirm=args.yes, wipe_audit=args.wipe)
    else:
        reload_bot(args.mode)
