"""Startup reconciliation — trade_history.jsonl vs portfolio snapshot uyumsuzluk düzeltimi."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import AppConfig
from src.domain.portfolio.manager import PortfolioManager
from src.orchestration.startup import _reconcile_realized_pnl, bootstrap


def _make_logger_with_records(records: list[dict]) -> MagicMock:
    logger = MagicMock()
    logger.read_all.return_value = records
    # SPEC-A3: corrupt-row tracking attributes — varsayılan temiz log davranışı.
    logger.corrupt_lines = 0
    logger.corrupt_threshold_exceeded = False
    return logger


def test_reconcile_no_change_when_snapshot_matches_log():
    """Snapshot ve log eşit ise dokunulmaz (delta < 0.01)."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -30.0
    pm.bankroll = 970.0
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.4, "exit_pnl_usdc": -30.0},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert pm.realized_pnl == -30.0
    assert pm.bankroll == 970.0


def test_reconcile_snapshot_wins_when_nonzero_SPEC_Z8():
    """SPEC-Z8 (2026-05-25): snapshot.realized != 0 ise log override etmez.
    positions.json single source of truth — log audit/forensic.
    Log -82, snapshot -46 → snapshot KORUNUR (-46 kalır)."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -46.0
    pm.bankroll = 954.0
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.27, "exit_pnl_usdc": -17.07, "partial_exits": []},
        {"exit_price": 0.27, "exit_pnl_usdc": -19.32, "partial_exits": []},
        {"exit_price": 0.34, "exit_pnl_usdc": -15.31, "partial_exits": []},
        {"exit_price": 0.29, "exit_pnl_usdc": -15.48, "partial_exits": []},
        {"exit_price": 0.41, "exit_pnl_usdc": -14.97, "partial_exits": []},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    # SPEC-Z8: snapshot win — değişmez
    assert abs(pm.realized_pnl - (-46.0)) < 0.01
    assert abs(pm.bankroll - 954.0) < 0.01


def test_reconcile_fresh_snapshot_uses_log():
    """SPEC-Z8: snapshot.realized == 0 (fresh start) → log'a güven."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = 0.0
    pm.bankroll = 1000.0
    trade_logger = _make_logger_with_records([
        {"exit_price": 0.50, "exit_pnl_usdc": 25.0, "partial_exits": []},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    # Fresh snapshot: log wins
    assert abs(pm.realized_pnl - 25.0) < 0.01


def test_reconcile_includes_partial_exits():
    """Partial exit'ler de toplama dahil."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = 0.0
    pm.bankroll = 1000.0
    trade_logger = _make_logger_with_records([
        {
            "exit_price": None,
            "exit_pnl_usdc": 0.0,
            "partial_exits": [
                {"tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0, "timestamp": "t1"},
                {"tier": 2, "sell_pct": 0.5, "realized_pnl_usdc": 8.0, "timestamp": "t2"},
            ],
        },
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert abs(pm.realized_pnl - 13.0) < 0.01


def test_reconcile_empty_log_leaves_zero():
    """Boş log + zero snapshot → noop."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    trade_logger = _make_logger_with_records([])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    assert pm.realized_pnl == 0.0
    assert pm.bankroll == 1000.0


def test_bootstrap_writes_phantom_entries_for_orphan_positions(tmp_path: Path, caplog) -> None:
    """SPEC-D: data/positions.json'da pozisyon var ama audit boş → phantom-restored entry yazılır."""
    import logging as _logging
    caplog.set_level(_logging.WARNING)
    cfg = AppConfig()

    pos_data = {
        "positions": {
            "orphan_cid_xyz": {
                "condition_id": "orphan_cid_xyz",
                "token_id": "tok",
                "direction": "BUY_YES",
                "entry_price": 0.4,
                "size_usdc": 50.0,
                "shares": 125.0,
                "current_price": 0.45,
                "anchor_probability": 0.55,
                "event_id": "e1",
                "slug": "test-orphan-2026-05-09",
                "sport_tag": "nba",
                "entry_reason": "consensus",
                "confidence": "A",
                "bookmaker_prob": 0.6,
            }
        },
        "realized_pnl": 25.0,
        "high_water_mark": 1025.0,
    }
    (tmp_path / "positions.json").write_text(json.dumps(pos_data), encoding="utf-8")

    audit_path = tmp_path / "trade_history.jsonl"
    audit_path.write_text("", encoding="utf-8")

    bootstrap(cfg, logs_dir=tmp_path, trade_history_path=audit_path)

    assert any("Orphan positions detected" in rec.message for rec in caplog.records)

    audit_lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
    audit_records = [json.loads(line) for line in audit_lines if line.strip()]
    assert len(audit_records) == 1
    assert audit_records[0]["condition_id"] == "orphan_cid_xyz"
    assert "phantom" in (audit_records[0].get("entry_reason") or "").lower()


def test_reconcile_aborts_on_corrupt_threshold(caplog):
    """SPEC-A3 GUARD-2: trade_history corrupt threshold geçtiyse reconcile snapshot'a güvenir."""
    import logging as _logging
    caplog.set_level(_logging.WARNING)
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = -50.0
    pm.bankroll = 950.0
    # Bozuk log → records mevcut ama threshold aşıldı flag'i set
    trade_logger = _make_logger_with_records([{"exit_price": 0.4, "exit_pnl_usdc": -123.0}])
    trade_logger.corrupt_lines = 4
    trade_logger.corrupt_threshold_exceeded = True

    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)

    # Snapshot dokunulmadı — log'a güvenilmedi
    assert pm.realized_pnl == -50.0
    assert pm.bankroll == 950.0
    assert any(
        "corrupt_lines" in rec.message and "trusting snapshot" in rec.message
        for rec in caplog.records
    )


def test_reconcile_skipped_when_records_have_no_exit_data_phantom():
    """GUARD-3 (SPEC-D): records var ama exit verisi yok (hepsi phantom-restored) → snapshot'a güven."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = 42.68  # snapshot dolu
    pm.bankroll = 1042.68
    # 3 phantom entry — exit_price=None, partial_exits boş veya yok
    trade_logger = _make_logger_with_records([
        {"condition_id": "c1", "slug": "s1", "exit_price": None, "partial_exits": []},
        {"condition_id": "c2", "slug": "s2", "exit_price": None},  # partial_exits key yok
        {"condition_id": "c3", "slug": "s3", "exit_price": None, "partial_exits": None},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    # Snapshot korunur (zerolama yok)
    assert pm.realized_pnl == 42.68
    assert pm.bankroll == 1042.68


def test_reconcile_skipped_when_phantom_plus_real_exit_log_less_than_snapshot():
    """GUARD-4 (SPEC-E): phantom-restored + real exit kayıtları var, log < snapshot → snapshot win."""
    pm = PortfolioManager(initial_bankroll=1000.0)
    pm.realized_pnl = 58.31  # snapshot ($42.67 historical + $15.64 real)
    pm.bankroll = 1058.31
    trade_logger = _make_logger_with_records([
        # 19 phantom-restored entry
        *[{"condition_id": f"p{i}", "exit_price": None, "entry_reason": "phantom-restored:consensus"} for i in range(19)],
        # 1 real exit
        {"condition_id": "real1", "exit_price": 0.97, "exit_pnl_usdc": 10.83, "entry_reason": "consensus"},
        # 1 real partial scale-out
        {"condition_id": "real1", "exit_price": None, "partial_exits": [{"realized_pnl_usdc": 4.81}], "entry_reason": "consensus"},
    ])
    _reconcile_realized_pnl(pm, trade_logger, initial_bankroll=1000.0)
    # Snapshot korunur ($58.31) — log sum sadece $15.64 ama phantom flag GUARD-4 tetikler
    assert pm.realized_pnl == 58.31
    assert pm.bankroll == 1058.31
