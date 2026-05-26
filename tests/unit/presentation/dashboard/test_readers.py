"""presentation/dashboard/readers.py için birim testler.

ARCH_GUARD Kural 1 kontrolü: bu modül infra import etmemeli.

Dizin yapısı (yeni):
  logs_dir/audit/trade_history.jsonl, equity_history.jsonl
  logs_dir/runtime/skipped_trades.jsonl
  logs_dir/../data/positions.json, circuit_breaker_state.json, stock_queue.json
"""
from __future__ import annotations

import json
from pathlib import Path

from src.presentation.dashboard import readers


# ── Dizin setup helper ───────────────────────────────────────────────────────

def _mk_logs(tmp_path: Path) -> tuple[Path, Path]:
    """logs_dir ve data_dir oluştur, döner."""
    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    (logs_dir / "audit").mkdir(parents=True)
    (logs_dir / "runtime").mkdir(parents=True)
    (logs_dir / "session").mkdir(parents=True)
    data_dir.mkdir()
    return logs_dir, data_dir


# ── Katman ihlali kontrolü ──

def test_readers_module_has_no_infra_imports() -> None:
    """readers.py infrastructure/domain/strategy/orchestration import etmemeli."""
    path = Path(readers.__file__)
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from src.infrastructure",
        "import src.infrastructure",
        "from src.domain",
        "import src.domain",
        "from src.strategy",
        "import src.strategy",
        "from src.orchestration",
        "import src.orchestration",
    ):
        assert forbidden not in source, f"Layer violation: {forbidden}"


# ── read_positions ──

def test_read_positions_missing_returns_default(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    out = readers.read_positions(logs_dir)
    assert out == {"positions": {}, "realized_pnl": 0.0, "high_water_mark": 0.0}


def test_read_positions_valid_file(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = {"positions": {"k1": {"slug": "a"}}, "realized_pnl": 42.0, "high_water_mark": 1200.0}
    (data_dir / "positions.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_positions(logs_dir)
    assert out["realized_pnl"] == 42.0
    assert "k1" in out["positions"]


# ── read_replay_simulation ──

def test_read_replay_simulation_missing_returns_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    out = readers.read_replay_simulation(logs_dir)
    assert out == {}


def test_read_replay_simulation_indexes_by_cid_and_entry_ts(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    blob = {
        "schema_version": 1,
        "trades": [
            {
                "condition_id": "0xAAA",
                "entry_timestamp": "2026-05-25T10:00:00Z",
                "slug": "atp-x-set-totals-4pt5",
                "actual_pnl_usdc": -9.84,
                "fixes": [
                    {"label": "bimodal_sl_exempt", "if_held_pnl_usdc": 11.25,
                     "delta_usdc": 21.09},
                ],
            },
            {
                "condition_id": "0xBBB",
                "entry_timestamp": "2026-05-25T11:00:00Z",
                "slug": "wta-y-set-handicap-home-1pt5",
                "actual_pnl_usdc": 0.88,
                "fixes": [{"label": "same_market_type_blocked", "delta_usdc": -0.88}],
            },
        ],
    }
    (data_dir / "replay_simulation.json").write_text(
        json.dumps(blob), encoding="utf-8",
    )
    out = readers.read_replay_simulation(logs_dir)
    assert len(out) == 2
    a = out[("0xAAA", "2026-05-25T10:00:00Z")]
    assert a["actual_pnl_usdc"] == -9.84
    assert a["fixes"][0]["label"] == "bimodal_sl_exempt"
    b = out[("0xBBB", "2026-05-25T11:00:00Z")]
    assert b["fixes"][0]["label"] == "same_market_type_blocked"


def test_read_replay_simulation_skips_entries_without_keys(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    blob = {"trades": [{"slug": "x", "fixes": []}]}  # missing cid + entry_ts
    (data_dir / "replay_simulation.json").write_text(
        json.dumps(blob), encoding="utf-8",
    )
    assert readers.read_replay_simulation(logs_dir) == {}


def test_read_replay_simulation_corrupt_returns_empty(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "replay_simulation.json").write_text("not-json", encoding="utf-8")
    assert readers.read_replay_simulation(logs_dir) == {}


def test_read_positions_corrupt_returns_default(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "positions.json").write_text("not json", encoding="utf-8")
    out = readers.read_positions(logs_dir)
    assert out["positions"] == {}


# ── JSONL tail readers ──

def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")


def test_read_trades_missing_returns_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_trades(logs_dir) == []


def test_read_trades_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"slug": f"m-{i}"} for i in range(30)]
    _write_jsonl(logs_dir / "session" / "trade_history.jsonl", rows)
    out = readers.read_trades(logs_dir, n=10)
    assert len(out) == 10
    assert out[-1]["slug"] == "m-29"
    assert out[0]["slug"] == "m-20"


def test_read_trades_archive_files_not_read(tmp_path: Path) -> None:
    """Arşiv dosyaları (trade_history.archive.*.jsonl) dashboard kaynağı DEĞİL.

    Pre-wipe era kayıtları audit arşivinde durur ama mevcut realized_pnl onları
    içermez (startup reconcile GUARD-4). Dashboard arşivleri okumamalı, aksi
    halde realized_pnl ile UI arasında tutarsızlık doğar.
    """
    logs_dir, _ = _mk_logs(tmp_path)
    _write_jsonl(
        logs_dir / "audit" / "trade_history.archive.20260511_115858.jsonl",
        [{
            "slug": "pre-wipe-trade", "condition_id": "cid-old",
            "exit_price": 0.01, "exit_pnl_usdc": -40.93,
            "exit_timestamp": "2026-05-11T03:00:00Z",
            "entry_timestamp": "2026-05-10T20:00:00Z", "partial_exits": [],
        }],
    )

    out = readers.read_trades(logs_dir, n=100)
    assert out == []


def test_read_trades_session_and_audit_dedupe_by_entry_timestamp(
    tmp_path: Path,
) -> None:
    """Aynı (cid, entry_timestamp) iki kaynakta → tek satır; daha zengin kazanır.

    Tipik senaryo: session ve audit mirror'ı genellikle aynı satırı içerir.
    Crash sonrası birinde update gecikmişse, daha zengin exit data taşıyan
    kazanır (partial_exit sayısı + full-close).
    """
    logs_dir, _ = _mk_logs(tmp_path)
    cid = "0xabc123"
    ts = "2026-05-12T20:00:00Z"
    # session: sadece entry kaydı (henüz exit yok)
    _write_jsonl(logs_dir / "session" / "trade_history.jsonl", [{
        "slug": "match-a", "condition_id": cid, "entry_timestamp": ts,
        "exit_price": None, "partial_exits": [],
    }])
    # audit: aynı entry'nin partial_exit'li hali (daha zengin)
    _write_jsonl(logs_dir / "audit" / "trade_history.jsonl", [{
        "slug": "match-a", "condition_id": cid, "entry_timestamp": ts,
        "exit_price": None,
        "partial_exits": [{
            "tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 5.0,
            "timestamp": "2026-05-12T20:30:00Z", "price": 0.70,
        }],
    }])

    out = readers.read_trades(logs_dir, n=100)
    assert len(out) == 1
    assert len(out[0]["partial_exits"]) == 1


def test_read_trades_same_condition_different_entry_kept_separately(
    tmp_path: Path,
) -> None:
    """SL sonrası re-entry: aynı cid, farklı entry_timestamp → her iki trade dahil.

    Bot stop_loss sonrası aynı market'e yeniden girebilir (sl_reentry_count).
    Her giriş ayrı trade kaydıdır; dedupe by cid alone yanlış olur ve ilk
    SL'yi düşürür.
    """
    logs_dir, _ = _mk_logs(tmp_path)
    cid = "0xabc123"
    _write_jsonl(logs_dir / "session" / "trade_history.jsonl", [
        {  # 1. entry: SL ile kapandı
            "slug": "match-a", "condition_id": cid,
            "entry_timestamp": "2026-05-12T20:00:00Z",
            "entry_price": 0.40,
            "exit_price": 0.21, "exit_pnl_usdc": -16.62,
            "exit_reason": "stop_loss",
            "exit_timestamp": "2026-05-12T20:30:00Z",
            "partial_exits": [],
        },
        {  # 2. entry: aynı market, yeni giriş
            "slug": "match-a", "condition_id": cid,
            "entry_timestamp": "2026-05-12T21:00:00Z",
            "entry_price": 0.23,
            "exit_price": 0.01, "exit_pnl_usdc": -11.68,
            "exit_reason": "graduated_sl",
            "exit_timestamp": "2026-05-12T22:30:00Z",
            "partial_exits": [],
        },
    ])

    out = readers.read_trades(logs_dir, n=100)
    assert len(out) == 2
    pnls = sorted(t["exit_pnl_usdc"] for t in out)
    assert pnls == [-16.62, -11.68]


def test_read_trades_includes_partial_exits_from_session(tmp_path: Path) -> None:
    """Session'daki kısmi exit kayıtları realized_pnl ile tutarlı olarak dahil."""
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "positions.json").write_text(
        json.dumps({"positions": {}, "realized_pnl": 7.66, "high_water_mark": 1000.0}),
        encoding="utf-8",
    )
    _write_jsonl(logs_dir / "session" / "trade_history.jsonl", [{
        "slug": "sabres", "condition_id": "cid-sabres",
        "exit_price": None, "exit_pnl_usdc": 0.0,
        "entry_timestamp": "2026-05-12T23:00:00Z",
        "partial_exits": [{
            "tier": 1, "sell_pct": 0.4, "realized_pnl_usdc": 7.66,
            "timestamp": "2026-05-12T23:30:00Z", "price": 0.60,
        }],
    }])

    out = readers.read_trades(logs_dir, n=100)
    assert len(out) == 1
    assert out[0]["slug"] == "sabres"


def test_read_equity_history_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"bankroll": 1000 + i} for i in range(5)]
    _write_jsonl(logs_dir / "session" / "equity_history.jsonl", rows)
    out = readers.read_equity_history(logs_dir, n=100)
    assert len(out) == 5
    assert out[-1]["bankroll"] == 1004


def test_read_skipped_tail(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    rows = [{"slug": f"s-{i}", "skip_reason": "no_edge"} for i in range(3)]
    _write_jsonl(logs_dir / "runtime" / "skipped_trades.jsonl", rows)
    out = readers.read_skipped(logs_dir)
    assert len(out) == 3
    assert out[0]["skip_reason"] == "no_edge"


# ── read_eligible_queue ──

def test_read_eligible_queue_missing_empty(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_eligible_queue(logs_dir) == []


def test_read_eligible_queue_list(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = [{"slug": "a"}, {"slug": "b"}]
    (data_dir / "stock_queue.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_eligible_queue(logs_dir)
    assert len(out) == 2


def test_read_eligible_queue_non_list_returns_empty(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    (data_dir / "stock_queue.json").write_text('{"not": "list"}', encoding="utf-8")
    assert readers.read_eligible_queue(logs_dir) == []


# ── read_breaker ──

def test_read_breaker_missing_returns_empty_dict(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.read_breaker(logs_dir) == {}


def test_read_breaker_valid(tmp_path: Path) -> None:
    logs_dir, data_dir = _mk_logs(tmp_path)
    data = {"daily_realized_pnl_pct": -0.05, "consecutive_losses": 2}
    (data_dir / "circuit_breaker_state.json").write_text(json.dumps(data), encoding="utf-8")
    out = readers.read_breaker(logs_dir)
    assert out["consecutive_losses"] == 2


# ── bot_is_alive ──

def test_bot_is_alive_no_pid_file(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    assert readers.bot_is_alive(logs_dir) is False


def test_bot_is_alive_invalid_pid_content(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "agent.pid").write_text("not a number", encoding="utf-8")
    assert readers.bot_is_alive(logs_dir) is False


def test_bot_is_alive_nonexistent_pid(tmp_path: Path) -> None:
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "agent.pid").write_text("999999", encoding="utf-8")
    assert readers.bot_is_alive(logs_dir) is False
