"""trade_history + equity_history arşiv dosyalarını aktif dosyaya merge et.

Bağlam (2026-05-20): scripts/reboot.py reboot()'unu koşulsuz audit
archive ediyordu → 14 archive dosyası birikti, dashboard fragmente.
TASK 1 root cause fix etti; bu script geçmiş archive'ları geri birleştirir.

Akış:
  1. logs/_pre_merge_<TS>/ altına aktif dosyaları + tüm archive'ları yedekle
  2. Trade records merge:
       - composite key (condition_id, entry_timestamp) ile dedupe
       - aynı key'de exit verisi olan kazanır (exit_pnl_usdc != null
         VEYA daha çok partial_exits)
       - tüm archive + aktif birleştir, entry_timestamp'e göre sırala
  3. Equity records merge: timestamp ile dedupe, sırala
  4. Aktif dosyaları (audit + session mirror) overwrite
  5. Archive dosyaları logs/_pre_merge_<TS>/ altına move (silinmez)

Kullanım:
  python scripts/merge_audit_archives.py            # dry-run
  python scripts/merge_audit_archives.py --apply    # gerçek uygula
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent

_AUDIT_DIR = ROOT / "logs" / "audit"
_SESSION_DIR = ROOT / "logs" / "session"
_TRADE_NAME = "trade_history.jsonl"
_EQUITY_NAME = "equity_history.jsonl"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """JSONL dosyasını oku; bozuk satırları atla (warn)."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  WARN: {path.name} satır {line_num} bozuk: {e}")
    return out


def _trade_key(rec: dict[str, Any]) -> tuple[str, str]:
    """Trade record için unique key — (condition_id, entry_timestamp)."""
    return (str(rec.get("condition_id", "")), str(rec.get("entry_timestamp", "")))


def _has_more_exit_data(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    """Aynı key'de iki kayıt: candidate daha "zengin" mi?

    Zengin = (a) exit_pnl_usdc null değil ve current'ınki null,
    veya (b) ikisi de exit'liyse partial_exits sayısı daha çok.
    """
    cand_has_exit = candidate.get("exit_price") is not None
    curr_has_exit = current.get("exit_price") is not None
    if cand_has_exit and not curr_has_exit:
        return True
    if not cand_has_exit and curr_has_exit:
        return False
    # İkisi de exit'li veya ikisi de exit'siz — partial sayısına bak
    cand_partials = len(candidate.get("partial_exits") or [])
    curr_partials = len(current.get("partial_exits") or [])
    return cand_partials > curr_partials


def merge_trade_records(records_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Birden çok trade record listesini composite key ile dedupe+merge et.

    Args:
        records_lists: Her biri bir dosyadan gelen kayıt listesi.
                       Birleştirme: tümü tek bucket'a düşer, key çakışmasında
                       _has_more_exit_data() kazananı seçer.

    Returns:
        entry_timestamp'e göre kronolojik sıralı dedupe edilmiş kayıtlar.
    """
    bucket: dict[tuple[str, str], dict[str, Any]] = {}
    for records in records_lists:
        for rec in records:
            k = _trade_key(rec)
            existing = bucket.get(k)
            if existing is None or _has_more_exit_data(rec, existing):
                bucket[k] = rec
    return sorted(bucket.values(), key=lambda r: str(r.get("entry_timestamp", "")))


def merge_equity_records(records_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Equity snapshot listelerini timestamp ile dedupe (ilk-gelen kazanır)."""
    bucket: dict[str, dict[str, Any]] = {}
    for records in records_lists:
        for rec in records:
            ts = str(rec.get("timestamp", ""))
            if ts and ts not in bucket:
                bucket[ts] = rec
    return sorted(bucket.values(), key=lambda r: str(r.get("timestamp", "")))


def backup_files(
    audit_dir: Path,
    session_dir: Path,
    backup_root: Path,
    file_name: str,
) -> int:
    """Aktif + tüm archive dosyalarını backup_root altına KOPYALA (move değil).

    Returns:
        Kopyalanan dosya sayısı.
    """
    backup_root.mkdir(parents=True, exist_ok=True)
    count = 0

    active_audit = audit_dir / file_name
    if active_audit.exists():
        shutil.copy2(active_audit, backup_root / f"audit_{file_name}")
        count += 1

    active_session = session_dir / file_name
    if active_session.exists():
        shutil.copy2(active_session, backup_root / f"session_{file_name}")
        count += 1

    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    for arch in sorted(audit_dir.glob(f"{stem}.archive.*{suffix}")):
        shutil.copy2(arch, backup_root / arch.name)
        count += 1

    return count


def move_archives_to_backup(
    audit_dir: Path,
    backup_root: Path,
    file_name: str,
) -> int:
    """Archive dosyalarını backup'a MOVE et — aktif dizinden kalkar.

    Returns:
        Move edilen dosya sayısı.
    """
    backup_root.mkdir(parents=True, exist_ok=True)
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    count = 0
    for arch in sorted(audit_dir.glob(f"{stem}.archive.*{suffix}")):
        target = backup_root / arch.name
        # Backup zaten içerir kopya; orijinali güvenle taşıyabiliriz
        # (eğer copy backup'tan farklı yoldaysa target var olabilir → overwrite)
        if target.exists():
            target.unlink()
        shutil.move(str(arch), str(target))
        count += 1
    return count


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _trade_summary(records: list[dict[str, Any]]) -> tuple[int, int, float]:
    """(toplam, kapalı, realized_pnl_toplam)."""
    closed = 0
    realized = 0.0
    for rec in records:
        for pe in rec.get("partial_exits") or []:
            realized += float(pe.get("realized_pnl_usdc", 0.0))
        if rec.get("exit_price") is not None:
            closed += 1
            realized += float(rec.get("exit_pnl_usdc", 0.0))
    return len(records), closed, realized


def run_merge(
    audit_dir: Path,
    session_dir: Path,
    apply: bool,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Ana merge orkestrasyonu.

    Returns:
        Özet dict — print için tüm sayılar.
    """
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT / "logs" / f"_pre_merge_{ts}"

    # ── Trade history ────────────────────────────────────────────────
    active_trade = audit_dir / _TRADE_NAME
    session_trade = session_dir / _TRADE_NAME
    trade_lists = [_load_jsonl(active_trade)]
    archive_trades = sorted(audit_dir.glob(f"{Path(_TRADE_NAME).stem}.archive.*.jsonl"))
    for arch in archive_trades:
        trade_lists.append(_load_jsonl(arch))
    merged_trades = merge_trade_records(trade_lists)
    trade_total, trade_closed, trade_realized = _trade_summary(merged_trades)

    # ── Equity history ───────────────────────────────────────────────
    active_equity = audit_dir / _EQUITY_NAME
    session_equity = session_dir / _EQUITY_NAME
    equity_lists = [_load_jsonl(active_equity)]
    archive_equities = sorted(audit_dir.glob(f"{Path(_EQUITY_NAME).stem}.archive.*.jsonl"))
    for arch in archive_equities:
        equity_lists.append(_load_jsonl(arch))
    merged_equities = merge_equity_records(equity_lists)

    summary: dict[str, Any] = {
        "timestamp": ts,
        "backup_dir": str(backup_root) if apply else None,
        "trade_archives_found": len(archive_trades),
        "trade_records_merged": trade_total,
        "trade_records_closed": trade_closed,
        "trade_realized_total": round(trade_realized, 2),
        "equity_archives_found": len(archive_equities),
        "equity_records_merged": len(merged_equities),
        "applied": apply,
    }

    if not apply:
        return summary

    # ── Backup before any write ──────────────────────────────────────
    backup_trades = backup_files(audit_dir, session_dir, backup_root, _TRADE_NAME)
    backup_equity = backup_files(audit_dir, session_dir, backup_root, _EQUITY_NAME)
    summary["backed_up_trade_files"] = backup_trades
    summary["backed_up_equity_files"] = backup_equity

    # ── Write merged active + session ────────────────────────────────
    write_jsonl(active_trade, merged_trades)
    write_jsonl(session_trade, merged_trades)
    write_jsonl(active_equity, merged_equities)
    write_jsonl(session_equity, merged_equities)

    # ── Move archives to backup (only after write succeeded) ─────────
    moved_t = move_archives_to_backup(audit_dir, backup_root, _TRADE_NAME)
    moved_e = move_archives_to_backup(audit_dir, backup_root, _EQUITY_NAME)
    summary["moved_trade_archives"] = moved_t
    summary["moved_equity_archives"] = moved_e

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit archive merge tool")
    parser.add_argument("--apply", action="store_true", help="Gerçek yaz (default dry-run)")
    args = parser.parse_args()

    print(f"[merge] audit_dir={_AUDIT_DIR}")
    print(f"[merge] session_dir={_SESSION_DIR}")
    print(f"[merge] mode={'APPLY' if args.apply else 'DRY-RUN'}")

    summary = run_merge(_AUDIT_DIR, _SESSION_DIR, apply=args.apply)

    print(
        f"\nMerged {summary['trade_archives_found']} archives + active -> "
        f"{summary['trade_records_merged']} records "
        f"({summary['trade_records_closed']} closed, "
        f"${summary['trade_realized_total']:+.2f} realized total)"
    )
    print(
        f"Equity: {summary['equity_archives_found']} archives + active -> "
        f"{summary['equity_records_merged']} snapshots"
    )
    if args.apply:
        print(f"\nBackup: {summary['backup_dir']}")
        print(
            f"Moved {summary['moved_trade_archives']} trade archives + "
            f"{summary['moved_equity_archives']} equity archives to backup."
        )
    else:
        print("\nDry-run only. --apply ile gerçek yazma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
