"""scripts/reboot.py için integration testler — process spawn olmadan, file+mock tabanlı."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts.reboot import (
    archive_audit_logs,
    clear_runtime_logs,
    clear_session_logs,
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


def test_clear_runtime_logs_removes_rotated_files(tmp_path: Path) -> None:
    """2026-05-11 BUG FIX: rotate'lenmiş bot.log.1, .2, .3 dosyaları da silinmeli.
    Aksi halde 'clean start' sözleşmesi ihlal olur (RotatingFileHandler 10MB×5 = 50MB)."""
    log_file = tmp_path / "bot.log"
    log_file.write_bytes(b"current\n")
    rotated_1 = tmp_path / "bot.log.1"
    rotated_1.write_bytes(b"old1\n" * 1000)
    rotated_2 = tmp_path / "bot.log.2"
    rotated_2.write_bytes(b"old2\n" * 1000)
    rotated_3 = tmp_path / "bot.log.3"
    rotated_3.write_bytes(b"old3\n" * 1000)

    clear_runtime_logs(log_files=[log_file])

    # Ana dosya truncate edilir, rotate'lenmiş suffix'ler silinir
    assert log_file.exists()
    assert log_file.stat().st_size == 0
    assert not rotated_1.exists()
    assert not rotated_2.exists()
    assert not rotated_3.exists()


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


# ─── clear_session_logs ──────────────────────────────────────────────────────

def test_clear_session_logs_deletes_jsonl_files(tmp_path: Path) -> None:
    """Session log .jsonl dosyaları silinir."""
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "trade_history.jsonl").write_text('{"x":1}\n', encoding="utf-8")
    (session_dir / "equity_history.jsonl").write_text('{"y":2}\n', encoding="utf-8")
    (session_dir / "exits.jsonl").write_text('{"z":3}\n', encoding="utf-8")

    clear_session_logs(session_dir=session_dir)

    assert not (session_dir / "trade_history.jsonl").exists()
    assert not (session_dir / "equity_history.jsonl").exists()
    assert not (session_dir / "exits.jsonl").exists()


def test_clear_session_logs_missing_dir_no_error(tmp_path: Path) -> None:
    """Session dizini yoksa hata fırlatmaz."""
    missing = tmp_path / "no_session"
    clear_session_logs(session_dir=missing)  # should not raise


def test_clear_session_logs_audit_untouched(tmp_path: Path) -> None:
    """clear_session_logs audit/ dosyalarına dokunmaz."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    (audit_dir / "trade_history.jsonl").write_text('{"audit":true}\n', encoding="utf-8")

    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "trade_history.jsonl").write_text('{"session":true}\n', encoding="utf-8")

    clear_session_logs(session_dir=session_dir)

    # Session silindi
    assert not (session_dir / "trade_history.jsonl").exists()
    # Audit korundu
    assert (audit_dir / "trade_history.jsonl").read_text(encoding="utf-8") == '{"audit":true}\n'


def test_reboot_clears_session_and_audit() -> None:
    """2026-05-23 politika: Reboot TAM WIPE — session + audit + runtime hepsi arşive.

    SPEC-Z13 (2026-06-03): archive_audit_logs MOCK ZORUNLU — yoksa test
    production logs/audit/*.jsonl dosyalarını gerçekten arşive taşıyıp wipe eder.
    """
    with (
        patch("scripts.reboot.kill_processes"),
        patch("scripts.reboot.clear_runtime_logs"),
        patch("scripts.reboot.clear_session_logs") as mock_session,
        patch("scripts.reboot.clear_audit_logs") as mock_audit,
        patch("scripts.reboot.archive_audit_logs") as mock_archive,
        patch("scripts.reboot.reset_state"),
        patch("scripts.reboot.start_dashboard"),
        patch("scripts.reboot.start_bot"),
        patch("scripts.reboot.time.sleep"),
    ):
        reboot("dry_run", skip_confirm=True)

    mock_session.assert_called_once()
    mock_audit.assert_called_once()
    mock_archive.assert_called()  # production'a sızma testi


def test_reload_does_not_clear_session_or_audit(tmp_path: Path) -> None:
    """Reload: ne session ne audit dokunulur."""
    with (
        patch("scripts.reboot.kill_processes"),
        patch("scripts.reboot.start_dashboard"),
        patch("scripts.reboot.start_bot"),
        patch("scripts.reboot.clear_session_logs") as mock_session,
        patch("scripts.reboot.clear_audit_logs") as mock_audit,
        patch("scripts.reboot.time.sleep"),
    ):
        reload_bot("dry_run")

    mock_session.assert_not_called()
    mock_audit.assert_not_called()


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
        patch("scripts.reboot.clear_session_logs"),  # SPEC-Z13: prod log dokunma
        patch("scripts.reboot.clear_audit_logs"),    # SPEC-Z13: prod audit dokunma
        patch("scripts.reboot.archive_audit_logs"),  # SPEC-Z13: prod forensic dokunma
        patch("scripts.reboot.reset_state"),
        patch("scripts.reboot.time.sleep"),
    ):
        reboot("dry_run", skip_confirm=True)  # 1. çağrı: PID 7777 + 7778 oluşur
        reboot("dry_run", skip_confirm=True)  # 2. çağrı: 7777 + 7778 kill edilmeli

    assert 7777 in killed_pids, f"Agent PID 7777 kill edilmedi. Killed: {killed_pids}"
    assert 7778 in killed_pids, f"Dashboard PID 7778 kill edilmedi. Killed: {killed_pids}"


# ─── archive_audit_logs (2026-05-11 fix) ─────────────────────────────────────

def test_archive_audit_logs_copies_nonempty_file(tmp_path: Path) -> None:
    """SPEC-Z7 (2026-05-25): rename → copy. Audit korunur, dashboard exited tab
    boşalmaz (otomatik trigger durumunda). Reboot mode reset_state ile sonradan siler."""
    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.write_text('{"pnl": -86.80}\n', encoding="utf-8")

    archive_audit_logs(audit_files=[audit_file], timestamp="20260511_124500")

    # SPEC-Z7: orijinal KORUNUR (ground truth for dashboard)
    assert audit_file.exists()
    assert audit_file.read_text(encoding="utf-8") == '{"pnl": -86.80}\n'
    # Archive de oluşur (forensic snapshot)
    archived = tmp_path / "trade_history.archive.20260511_124500.jsonl"
    assert archived.exists()
    assert archived.read_text(encoding="utf-8") == '{"pnl": -86.80}\n'


def test_archive_audit_logs_skips_empty_file(tmp_path: Path) -> None:
    """Bos audit dosyasi rename edilmez (no-op)."""
    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.touch()

    archive_audit_logs(audit_files=[audit_file], timestamp="20260511_124500")

    # Bos dosya yerinde kaldi
    assert audit_file.exists()
    assert audit_file.stat().st_size == 0
    archived = tmp_path / "trade_history.archive.20260511_124500.jsonl"
    assert not archived.exists()


def test_archive_audit_logs_skips_missing_file(tmp_path: Path) -> None:
    """Olmayan audit dosyasi sessizce atlanir."""
    audit_file = tmp_path / "missing.jsonl"
    archive_audit_logs(audit_files=[audit_file], timestamp="20260511_124500")
    assert not audit_file.exists()


def test_reboot_calls_archive_audit_logs() -> None:
    """Reboot komutu archive_audit_logs cagiriyor (clean start fix)."""
    with (
        patch("scripts.reboot.kill_processes"),
        patch("scripts.reboot.clear_runtime_logs"),
        patch("scripts.reboot.clear_session_logs"),
        patch("scripts.reboot.archive_audit_logs") as mock_archive,
        patch("scripts.reboot.reset_state"),
        patch("scripts.reboot.start_bot"),
        patch("scripts.reboot.start_dashboard"),
        patch("scripts.reboot.time.sleep"),
        patch("scripts.reboot._read_open_condition_ids", return_value=set()),
    ):
        reboot("dry_run", skip_confirm=True)

    mock_archive.assert_called_once()


def test_reboot_archives_full_audit_not_split() -> None:
    """2026-05-22: reboot full clean slate ister → archive_audit_logs'a
    open_condition_ids=None geçer. Eski "open positions kept" davranışı
    (2026-05-21 fix) artık kullanılmıyor — reset_state() zaten positions.json'ı
    siliyor, kayıt tutmanın anlamı yok.
    """
    with (
        patch("scripts.reboot.kill_processes"),
        patch("scripts.reboot.clear_runtime_logs"),
        patch("scripts.reboot.clear_session_logs"),
        patch("scripts.reboot.archive_audit_logs") as mock_archive,
        patch("scripts.reboot.reset_state"),
        patch("scripts.reboot.start_bot"),
        patch("scripts.reboot.start_dashboard"),
        patch("scripts.reboot.time.sleep"),
    ):
        reboot("dry_run", skip_confirm=True)

    mock_archive.assert_called_once()
    _, kwargs = mock_archive.call_args
    assert kwargs.get("open_condition_ids") is None, (
        "reboot() archive_audit_logs'a open_condition_ids=None geçmeli "
        "(full archive). Şu an: " + repr(kwargs.get("open_condition_ids"))
    )


def test_archive_audit_logs_splits_open_positions(tmp_path: Path) -> None:
    """2026-05-21 fix: trade_history.jsonl açık pozisyonların kayıtları yeni
    audit'te tutulur, kapanmış trade'ler arşive taşınır.

    Senaryo: positions.json reset_state ile silinmeden ÖNCE archive çağrılır.
    Açık cid'ler (partial_exits taşıyan veya hala açık) yeni audit'te kalır.
    Kapanmış trade'ler (exit_price set) arşive gider.
    """
    from scripts.reboot import archive_audit_logs

    audit_file = tmp_path / "trade_history.jsonl"
    open_cid = "0xopen_partial"
    closed_cid = "0xclosed"
    audit_file.write_text(
        '{"condition_id": "0xopen_partial", "partial_exits": [{"tier": 1}]}\n'
        '{"condition_id": "0xclosed", "exit_price": 0.83, "exit_pnl_usdc": 3.57}\n',
        encoding="utf-8",
    )

    archive_audit_logs(
        audit_files=[audit_file],
        timestamp="20260521_020000",
        open_condition_ids={open_cid},
    )

    # Audit dosyası YAŞIYOR ve sadece açık pozisyon kaydını içeriyor
    assert audit_file.exists()
    audit_content = audit_file.read_text(encoding="utf-8")
    assert open_cid in audit_content
    assert closed_cid not in audit_content

    # Archive dosyası kapanmış trade'i içeriyor
    archived = tmp_path / "trade_history.archive.20260521_020000.jsonl"
    assert archived.exists()
    archived_content = archived.read_text(encoding="utf-8")
    assert closed_cid in archived_content
    assert open_cid not in archived_content


def test_archive_audit_logs_all_closed_preserves_audit_spec_z8(tmp_path: Path) -> None:
    """SPEC-Z8 (2026-06-03 TODO-007 Katman A): keep boş olsa bile AUDIT DOKUNULMAZ.

    Eski davranış audit'i sıfırlardı; mistik scheduler stale open_cids ile
    çağırınca defter yıkılırdı (orphan exit semptomu). Yeni davranış: audit
    olduğu gibi korunur, archive kopyası ayrı yaratılır, pre-split backup alınır.
    """
    from scripts.reboot import archive_audit_logs

    audit_file = tmp_path / "trade_history.jsonl"
    original = (
        '{"condition_id": "0xa", "exit_price": 0.5}\n'
        '{"condition_id": "0xb", "exit_price": 0.7}\n'
    )
    audit_file.write_text(original, encoding="utf-8")

    archive_audit_logs(
        audit_files=[audit_file],
        timestamp="20260521_020000",
        open_condition_ids={"0xnonexistent"},
    )

    # SPEC-Z8: audit DOKUNULMADI — orijinal içerik korundu
    assert audit_file.exists()
    assert audit_file.read_text(encoding="utf-8") == original
    # Archive yine de yaratıldı (snapshot)
    archived = tmp_path / "trade_history.archive.20260521_020000.jsonl"
    assert archived.exists()
    assert "0xa" in archived.read_text(encoding="utf-8")
    assert "0xb" in archived.read_text(encoding="utf-8")
    # Katman C: pre-split backup oluştu
    backup = audit_file.with_suffix(".jsonl.bak.before_split_20260521_020000")
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original


def test_archive_audit_logs_open_cids_none_full_copy(tmp_path: Path) -> None:
    """SPEC-Z7: open_condition_ids=None ise full copy (eskiden rename idi).

    Audit dosyası KORUNUR (dashboard ground truth). Archive snapshot olarak
    forensic için yaratılır. Reboot mode reset_state ile asıl temizlik yapar.
    """
    from scripts.reboot import archive_audit_logs

    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.write_text('{"condition_id": "0xa"}\n', encoding="utf-8")

    archive_audit_logs(
        audit_files=[audit_file], timestamp="20260521_020000",
    )

    # SPEC-Z7: orijinal korunur
    assert audit_file.exists()
    archived = tmp_path / "trade_history.archive.20260521_020000.jsonl"
    assert archived.exists()


def test_archive_audit_logs_split_preserves_open_kept_records(tmp_path: Path) -> None:
    """SPEC-Z8: keep dolu durumda audit sadece açık kayıtları içerir + backup alınır."""
    from scripts.reboot import archive_audit_logs

    audit_file = tmp_path / "trade_history.jsonl"
    original = (
        '{"condition_id": "0xopen", "entry_price": 0.4}\n'
        '{"condition_id": "0xclosed", "exit_price": 0.6}\n'
    )
    audit_file.write_text(original, encoding="utf-8")

    archive_audit_logs(
        audit_files=[audit_file], timestamp="20260603_000000",
        open_condition_ids={"0xopen"},
    )

    # Audit sadece açık kayıt
    assert "0xopen" in audit_file.read_text(encoding="utf-8")
    assert "0xclosed" not in audit_file.read_text(encoding="utf-8")
    # Archive sadece kapanan
    archived = tmp_path / "trade_history.archive.20260603_000000.jsonl"
    assert "0xclosed" in archived.read_text(encoding="utf-8")
    # Katman C: pre-split backup orijinali içerir
    backup = audit_file.with_suffix(".jsonl.bak.before_split_20260603_000000")
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original


def test_archive_audit_logs_writes_forensic_jsonl(tmp_path: Path, monkeypatch) -> None:
    """SPEC-Z8 Katman B: her archive_audit_logs çağrısı forensic JSONL yazar.

    Stack zinciri + caller PID + open_cids sample + audit_files. Detached
    subprocess'te print() kaybolduğu için kalıcı dosya zorunlu. Mistik
    scheduler yakalandığında bu dosya kanıt olur.
    """
    from scripts import reboot as rb

    forensic_path = tmp_path / "forensic.jsonl"
    monkeypatch.setattr(rb, "_ARCHIVE_FORENSIC_LOG", forensic_path)

    audit_file = tmp_path / "trade_history.jsonl"
    audit_file.write_text('{"condition_id": "0xa"}\n', encoding="utf-8")

    rb.archive_audit_logs(
        audit_files=[audit_file], timestamp="20260603_000000",
        open_condition_ids={"0xa"},
    )

    assert forensic_path.exists()
    lines = forensic_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    import json as _json
    entry = _json.loads(lines[0])
    # Zorunlu alanlar
    assert "ts_utc" in entry
    assert entry["pid"] > 0
    assert "parent" in entry
    assert entry["open_cids_count"] == 1
    assert entry["open_cids_sample"] == ["0xa"]
    assert entry["audit_files"] == [str(audit_file)]
    assert entry["stack_depth"] > 0
    assert all("file" in f and "line" in f and "function" in f for f in entry["stack"])
    # Caller frame test_ ile başlamalı (pytest)
    assert any("test_" in f["function"] for f in entry["stack"])


def test_read_open_condition_ids_returns_keys(tmp_path: Path) -> None:
    """positions.json'dan condition_id'leri çıkarır."""
    from scripts.reboot import _read_open_condition_ids

    positions_file = tmp_path / "positions.json"
    positions_file.write_text(
        '{"positions": {"0xabc": {"slug": "s1"}, "0xdef": {"slug": "s2"}}}',
        encoding="utf-8",
    )

    cids = _read_open_condition_ids(positions_file)
    assert cids == {"0xabc", "0xdef"}


def test_read_open_condition_ids_missing_file(tmp_path: Path) -> None:
    """positions.json yoksa boş set döner."""
    from scripts.reboot import _read_open_condition_ids

    cids = _read_open_condition_ids(tmp_path / "missing.json")
    assert cids == set()


def test_read_open_condition_ids_corrupt_file(tmp_path: Path) -> None:
    """positions.json bozuksa boş set döner (silent recovery, hata yutmaz logger
    yerine - bu script seviyesi, default tolerans)."""
    from scripts.reboot import _read_open_condition_ids

    positions_file = tmp_path / "positions.json"
    positions_file.write_text("not json {", encoding="utf-8")

    cids = _read_open_condition_ids(positions_file)
    assert cids == set()
