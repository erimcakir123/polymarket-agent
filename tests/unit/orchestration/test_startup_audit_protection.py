"""SPEC-H 2026-05-10 + 2026-05-20 fix — startup ve reboot audit'i KORUR.

Audit dosyaları append-only kalıcı arşiv. Bootstrap onları DOKUNMAZ;
arşivleme SADECE explicit --wipe / WIPE_AUDIT=1 ile yapılır.

Bu test dosyası iki invariant'ı garanti eder:
  1. `bootstrap()` audit dosyalarını rename/silme/truncate ETMEZ.
  2. `archive_audit_on_demand()` wipe_audit=False ise NO-OP.
     wipe_audit=True (veya WIPE_AUDIT=1 env) ise sadece o zaman arşivler.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from scripts.reboot import archive_audit_on_demand
from src.config.settings import AppConfig, Mode
from src.orchestration.startup import bootstrap


def _make_config() -> AppConfig:
    """Minimum geçerli AppConfig (defaults).

    bootstrap sadece config.mode, config.initial_bankroll ve config.circuit_breaker.*
    okur — diğer alanlar relevant değil.
    """
    return AppConfig(mode=Mode.DRY_RUN, initial_bankroll=1000.0)


def test_bootstrap_does_not_archive_audit_by_default(tmp_path: Path) -> None:
    """SPEC-H invariant: bootstrap() audit dosyalarına DOKUNMAZ.

    Senaryo: logs/audit/trade_history.jsonl içerikli, bootstrap çağrılıyor.
    Beklenen: dosya yerinde, içerik aynen, hiçbir .archive.* dosyası oluşmaz.
    """
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True)
    audit_file = audit_dir / "trade_history.jsonl"
    audit_content = '{"slug":"x","condition_id":"a","exit_price":1.0,"exit_pnl_usdc":5.0,"entry_timestamp":"2026-05-20T10:00:00Z"}\n'
    audit_file.write_text(audit_content, encoding="utf-8")
    original_mtime = audit_file.stat().st_mtime

    config = _make_config()
    state = bootstrap(
        config=config,
        logs_dir=tmp_path / "data",
        trade_history_path=audit_file,
    )

    # 1. Dosya hâlâ var
    assert audit_file.exists()
    # 2. İçerik bozulmamış
    assert audit_file.read_text(encoding="utf-8") == audit_content
    # 3. mtime değişmedi (yazma yok)
    assert audit_file.stat().st_mtime == original_mtime
    # 4. Hiçbir archive dosyası oluşmadı
    archives = list(audit_dir.glob("*.archive.*.jsonl"))
    assert archives == [], f"Bootstrap audit'i arşivledi: {archives}"
    # 5. State dönüyor (smoke)
    assert state.config.mode == Mode.DRY_RUN


def test_bootstrap_archives_audit_when_explicit_wipe_flag_set(tmp_path: Path) -> None:
    """archive_audit_on_demand(wipe_audit=True) explicit çağrıldığında arşivler.

    Bootstrap NE FONKSIYONU çağırır NE de wipe flag taşır — wipe protokolünün
    sahibi reboot.py'dir. Bu test, gate'in pozitif tarafını doğrular:
    explicit wipe_audit=True verildiğinde dosyalar archive edilir.
    """
    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.write_text('{"x": 1}\n', encoding="utf-8")

    # Default: no-op
    no_archive = archive_audit_on_demand(
        wipe_audit=False,
        audit_files=[audit_file],
        timestamp="20260520_120000",
    )
    assert no_archive is False
    assert audit_file.exists()
    assert not list(tmp_path.glob("*.archive.*.jsonl"))

    # Explicit wipe: archive
    did_archive = archive_audit_on_demand(
        wipe_audit=True,
        audit_files=[audit_file],
        timestamp="20260520_120000",
    )
    assert did_archive is True
    assert not audit_file.exists()
    archived = tmp_path / "trade_history.archive.20260520_120000.jsonl"
    assert archived.exists()
    assert archived.read_text(encoding="utf-8") == '{"x": 1}\n'


def test_archive_audit_on_demand_respects_env_var(tmp_path: Path) -> None:
    """WIPE_AUDIT=1 env var de wipe_audit=True gibi arşivlemeyi tetikler."""
    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.write_text('{"x": 1}\n', encoding="utf-8")

    with patch.dict(os.environ, {"WIPE_AUDIT": "1"}):
        did_archive = archive_audit_on_demand(
            wipe_audit=False,           # flag yok ama env=1
            audit_files=[audit_file],
            timestamp="20260520_130000",
        )

    assert did_archive is True
    assert not audit_file.exists()
    assert (tmp_path / "trade_history.archive.20260520_130000.jsonl").exists()


def test_archive_audit_on_demand_skips_when_env_unset(tmp_path: Path) -> None:
    """Env var yok + flag False → no-op (default reboot davranışı)."""
    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.write_text('{"x": 1}\n', encoding="utf-8")
    original_mtime = audit_file.stat().st_mtime

    # WIPE_AUDIT env'i temizle (varsa)
    env_clean = {k: v for k, v in os.environ.items() if k != "WIPE_AUDIT"}
    with patch.dict(os.environ, env_clean, clear=True):
        did_archive = archive_audit_on_demand(
            wipe_audit=False,
            audit_files=[audit_file],
            timestamp="20260520_140000",
        )

    assert did_archive is False
    assert audit_file.exists()
    assert audit_file.stat().st_mtime == original_mtime
    assert not list(tmp_path.glob("*.archive.*.jsonl"))
