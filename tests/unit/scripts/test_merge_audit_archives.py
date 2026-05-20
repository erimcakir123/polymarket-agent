"""scripts/merge_audit_archives.py için unit testler — dosya I/O izole tmp_path."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.merge_audit_archives import (
    backup_files,
    merge_equity_records,
    merge_trade_records,
    move_archives_to_backup,
    run_merge,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def test_merge_dedupes_by_composite_key() -> None:
    """Aynı (condition_id, entry_timestamp) iki kayıt → tek kayıt kalır."""
    a = [
        {"condition_id": "c1", "entry_timestamp": "2026-05-20T10:00:00Z", "exit_price": None, "size_usdc": 50.0},
    ]
    b = [
        # Aynı key — duplicate
        {"condition_id": "c1", "entry_timestamp": "2026-05-20T10:00:00Z", "exit_price": None, "size_usdc": 50.0},
        # Farklı key — eklenir
        {"condition_id": "c2", "entry_timestamp": "2026-05-20T11:00:00Z", "exit_price": None, "size_usdc": 30.0},
    ]
    merged = merge_trade_records([a, b])
    assert len(merged) == 2
    cids = {r["condition_id"] for r in merged}
    assert cids == {"c1", "c2"}


def test_merge_prefers_record_with_exit_data() -> None:
    """Aynı key'de bir kayıt exit'li, biri exit'siz → exit'li kazanır."""
    open_rec = {
        "condition_id": "c1",
        "entry_timestamp": "2026-05-20T10:00:00Z",
        "exit_price": None,
        "exit_pnl_usdc": 0.0,
    }
    closed_rec = {
        "condition_id": "c1",
        "entry_timestamp": "2026-05-20T10:00:00Z",
        "exit_price": 1.0,
        "exit_pnl_usdc": 18.33,
        "exit_reason": "resolved",
    }
    merged = merge_trade_records([[open_rec], [closed_rec]])
    assert len(merged) == 1
    assert merged[0]["exit_price"] == 1.0
    assert merged[0]["exit_pnl_usdc"] == 18.33

    # Sıra önemsiz — ters dizilim de aynı sonuç
    merged_rev = merge_trade_records([[closed_rec], [open_rec]])
    assert merged_rev[0]["exit_price"] == 1.0


def test_merge_preserves_partial_exits() -> None:
    """İki kapalı kayıttan partial_exits daha çok olan kazanır."""
    one_partial = {
        "condition_id": "c1",
        "entry_timestamp": "2026-05-20T10:00:00Z",
        "exit_price": 1.0,
        "exit_pnl_usdc": 10.0,
        "partial_exits": [{"tier": 1, "realized_pnl_usdc": 5.0}],
    }
    two_partials = {
        "condition_id": "c1",
        "entry_timestamp": "2026-05-20T10:00:00Z",
        "exit_price": 1.0,
        "exit_pnl_usdc": 10.0,
        "partial_exits": [
            {"tier": 1, "realized_pnl_usdc": 5.0},
            {"tier": 2, "realized_pnl_usdc": 8.0},
        ],
    }
    merged = merge_trade_records([[one_partial], [two_partials]])
    assert len(merged) == 1
    assert len(merged[0]["partial_exits"]) == 2


def test_merge_creates_backup_before_modify(tmp_path: Path) -> None:
    """run_merge --apply önce backup_files yapar, sonra yazar.

    Hedef: aktif dosya değiştirilmeden önce backup'ta orijinal kopyası bulunmalı.
    """
    audit_dir = tmp_path / "audit"
    session_dir = tmp_path / "session"
    audit_dir.mkdir()
    session_dir.mkdir()

    # Aktif trade — 1 kayıt
    _write_jsonl(audit_dir / "trade_history.jsonl", [
        {"condition_id": "c1", "entry_timestamp": "2026-05-20T10:00:00Z",
         "exit_price": None, "exit_pnl_usdc": 0.0, "partial_exits": []},
    ])
    # Archive — 1 kayıt
    _write_jsonl(audit_dir / "trade_history.archive.20260520_120000.jsonl", [
        {"condition_id": "c2", "entry_timestamp": "2026-05-20T11:00:00Z",
         "exit_price": 1.0, "exit_pnl_usdc": 12.50, "partial_exits": []},
    ])
    # Aktif equity (boş bırakma)
    _write_jsonl(audit_dir / "equity_history.jsonl", [
        {"timestamp": "2026-05-20T10:00:00Z", "bankroll": 1000.0},
    ])

    # Backup root için run_merge'ün ROOT'tan türettiğini override edemeyiz;
    # bu yüzden ROOT bağımsız low-level fonksiyonu doğrudan test edelim:
    backup_root = tmp_path / "_pre_merge_test"
    n_trade = backup_files(audit_dir, session_dir, backup_root, "trade_history.jsonl")
    n_equity = backup_files(audit_dir, session_dir, backup_root, "equity_history.jsonl")

    # Backup içeriği kontrol
    assert (backup_root / "audit_trade_history.jsonl").exists()
    assert (backup_root / "trade_history.archive.20260520_120000.jsonl").exists()
    assert (backup_root / "audit_equity_history.jsonl").exists()
    # Aktif: 1 + archive: 1 = 2 trade dosyası backup'a kopyalandı
    assert n_trade == 2
    # Equity: aktif 1, archive 0 = 1
    assert n_equity == 1

    # Aktif dosya HÂLÂ orijinal (henüz overwrite olmadı)
    original = json.loads((audit_dir / "trade_history.jsonl").read_text().strip())
    assert original["condition_id"] == "c1"


def test_run_merge_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    """--apply olmadan: hiçbir dosya silinmez/yazılmaz."""
    audit_dir = tmp_path / "audit"
    session_dir = tmp_path / "session"
    audit_dir.mkdir()
    session_dir.mkdir()

    _write_jsonl(audit_dir / "trade_history.jsonl", [
        {"condition_id": "c1", "entry_timestamp": "2026-05-20T10:00:00Z",
         "exit_price": None, "exit_pnl_usdc": 0.0, "partial_exits": []},
    ])
    archive = audit_dir / "trade_history.archive.20260520_120000.jsonl"
    _write_jsonl(archive, [
        {"condition_id": "c2", "entry_timestamp": "2026-05-20T11:00:00Z",
         "exit_price": 1.0, "exit_pnl_usdc": 12.50, "partial_exits": []},
    ])
    _write_jsonl(audit_dir / "equity_history.jsonl", [
        {"timestamp": "2026-05-20T10:00:00Z", "bankroll": 1000.0},
    ])

    summary = run_merge(audit_dir, session_dir, apply=False, timestamp="test")

    # Özet doğru
    assert summary["trade_archives_found"] == 1
    assert summary["trade_records_merged"] == 2
    assert summary["trade_records_closed"] == 1
    assert summary["trade_realized_total"] == 12.50
    assert summary["applied"] is False

    # Archive HÂLÂ aktif dizinde (move yok)
    assert archive.exists()
    # Session dosyası yazılmadı
    assert not (session_dir / "trade_history.jsonl").exists()


def test_equity_merge_dedupes_by_timestamp() -> None:
    """Aynı timestamp'li equity snapshot → tek kayıt kalır, sıralı."""
    a = [
        {"timestamp": "2026-05-20T10:00:00Z", "bankroll": 1000.0},
        {"timestamp": "2026-05-20T11:00:00Z", "bankroll": 1020.0},
    ]
    b = [
        {"timestamp": "2026-05-20T10:00:00Z", "bankroll": 1000.0},  # dup
        {"timestamp": "2026-05-20T12:00:00Z", "bankroll": 1050.0},
    ]
    merged = merge_equity_records([a, b])
    assert len(merged) == 3
    ts_list = [r["timestamp"] for r in merged]
    assert ts_list == sorted(ts_list)


def test_move_archives_to_backup_clears_audit_dir(tmp_path: Path) -> None:
    """Archive dosyaları move sonrası aktif dizinden kalkar, backup'a girer."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    arch1 = audit_dir / "trade_history.archive.20260520_120000.jsonl"
    arch2 = audit_dir / "trade_history.archive.20260520_130000.jsonl"
    arch1.write_text("{}\n")
    arch2.write_text("{}\n")
    # Aktif dokunulmaz
    active = audit_dir / "trade_history.jsonl"
    active.write_text("{}\n")

    backup_root = tmp_path / "_pre_merge_test"
    moved = move_archives_to_backup(audit_dir, backup_root, "trade_history.jsonl")

    assert moved == 2
    assert not arch1.exists()
    assert not arch2.exists()
    assert active.exists()  # Aktif korundu
    assert (backup_root / arch1.name).exists()
    assert (backup_root / arch2.name).exists()
