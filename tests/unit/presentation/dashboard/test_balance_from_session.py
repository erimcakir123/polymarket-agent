"""Balance widget session-only kaynak testleri.

Kapsam:
  - readers.read_balance_from_session → session/equity_history.jsonl
  - computed.equity_summary_from_session → türetme
  - computed.loss_protection_from_session → risk gauge
  - routes /api/summary → session'dan okur, positions.json'a bakmaz (balance için)

Reboot senaryosu: session yok → balance sıfır (audit/positions.json değeri değil).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.presentation.dashboard import computed, readers
from src.presentation.dashboard.app import create_app
from src.config.settings import AppConfig


# ── Helpers ─────────────────────────────────────────────────────────────────

def _mk_logs(tmp_path: Path) -> tuple[Path, Path]:
    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    (logs_dir / "session").mkdir(parents=True)
    (logs_dir / "audit").mkdir(parents=True)
    (logs_dir / "runtime").mkdir(parents=True)
    data_dir.mkdir()
    return logs_dir, data_dir


def _write_equity(logs_dir: Path, entries: list[dict]) -> None:
    path = logs_dir / "session" / "equity_history.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _write_trades(logs_dir: Path, trades: list[dict]) -> None:
    """Session trade_history.jsonl — realized_pnl widget audit'ten okur."""
    path = logs_dir / "session" / "trade_history.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for t in trades:
            f.write(json.dumps(t) + "\n")


def _write_positions(tmp_path: Path, realized: float = 107.37) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "positions.json").write_text(json.dumps({
        "positions": {},
        "realized_pnl": realized,
        "high_water_mark": 1107.37,
    }), encoding="utf-8")


def _client(tmp_path: Path):
    app = create_app(config=AppConfig(), logs_dir=tmp_path / "logs")
    app.config["TESTING"] = True
    return app.test_client()


# ── readers.read_balance_from_session ────────────────────────────────────────

def test_read_balance_session_missing_file_returns_empty(tmp_path: Path) -> None:
    """Session dosyası yoksa has_data=False, tüm sayısal değerler sıfır."""
    logs_dir, _ = _mk_logs(tmp_path)
    out = readers.read_balance_from_session(logs_dir)
    assert out["has_data"] is False
    assert out["bankroll"] == 0.0
    assert out["realized_pnl"] == 0.0
    assert out["unrealized_pnl"] == 0.0
    assert out["peak_bankroll"] == 0.0


def test_read_balance_session_empty_file_returns_empty(tmp_path: Path) -> None:
    """Boş dosya (reboot sonrası temizlenmiş) → has_data=False."""
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "session" / "equity_history.jsonl").write_text("", encoding="utf-8")
    out = readers.read_balance_from_session(logs_dir)
    assert out["has_data"] is False


def test_read_balance_session_reads_last_entry(tmp_path: Path) -> None:
    """Son entry doğru okunmalı — realized_pnl, bankroll, unrealized_pnl."""
    logs_dir, _ = _mk_logs(tmp_path)
    _write_equity(logs_dir, [
        {"bankroll": 1000.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
        {"bankroll": 1042.5, "realized_pnl": 42.5, "unrealized_pnl": 8.0,
         "invested": 40.0, "open_positions": 1},
    ])
    out = readers.read_balance_from_session(logs_dir)
    assert out["has_data"] is True
    assert out["bankroll"] == 1042.5
    assert out["realized_pnl"] == 42.5
    assert out["unrealized_pnl"] == 8.0
    assert out["invested"] == 40.0
    assert out["open_positions"] == 1


def test_read_balance_session_peak_is_max_bankroll(tmp_path: Path) -> None:
    """Peak: session boyunca görülen max bankroll."""
    logs_dir, _ = _mk_logs(tmp_path)
    _write_equity(logs_dir, [
        {"bankroll": 1000.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0},
        {"bankroll": 1150.0, "realized_pnl": 150.0, "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0},
        {"bankroll": 1080.0, "realized_pnl": 80.0, "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0},
    ])
    out = readers.read_balance_from_session(logs_dir)
    assert out["peak_bankroll"] == 1150.0
    assert out["bankroll"] == 1080.0  # son entry


def test_read_balance_session_single_entry_peak_equals_bankroll(tmp_path: Path) -> None:
    """Tek entry: peak = bankroll."""
    logs_dir, _ = _mk_logs(tmp_path)
    _write_equity(logs_dir, [
        {"bankroll": 1025.0, "realized_pnl": 25.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
    ])
    out = readers.read_balance_from_session(logs_dir)
    assert out["peak_bankroll"] == 1025.0
    assert out["bankroll"] == 1025.0


# ── computed.equity_summary_from_session ─────────────────────────────────────

def test_equity_summary_from_session_no_data_returns_zeros(tmp_path: Path) -> None:
    """has_data=False → tüm sayılar sıfır."""
    sb = {"has_data": False, "open_positions": 0}
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0)
    assert out["bankroll"] == 0.0
    assert out["realized_pnl"] == 0.0
    assert out["peak_balance"] == 0.0
    assert out["drawdown_pct"] == 0.0


def test_equity_summary_from_session_maps_fields(tmp_path: Path) -> None:
    """Session balance → equity summary alanları doğru eşleşmeli."""
    sb = {
        "has_data": True,
        "bankroll": 1050.0,
        "realized_pnl": 50.0,
        "unrealized_pnl": 12.0,
        "invested": 40.0,
        "open_positions": 1,
        "peak_bankroll": 1100.0,
    }
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0)
    assert out["bankroll"] == 1050.0
    assert out["realized_pnl"] == 50.0
    assert out["open_pnl"] == 12.0
    assert out["locked"] == 40.0
    assert out["position_count"] == 1
    # total_equity = 1050 + 40 + 12 = 1102
    assert out["total_equity"] == 1102.0
    # peak = max(1100, 1050, 1000) = 1100
    assert out["peak_balance"] == 1100.0


def test_equity_summary_from_session_peak_uses_initial_bankroll(tmp_path: Path) -> None:
    """Session henüz başlarken peak en az initial_bankroll olmalı."""
    sb = {
        "has_data": True,
        "bankroll": 980.0,
        "realized_pnl": -20.0,
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": 0,
        "peak_bankroll": 1000.0,
    }
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0)
    assert out["peak_balance"] == 1000.0


def test_equity_summary_from_session_drawdown_correct(tmp_path: Path) -> None:
    """Peak=1100, current_total=990 → drawdown=(1100-990)/1100=10%."""
    sb = {
        "has_data": True,
        "bankroll": 990.0,
        "realized_pnl": -10.0,
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": 0,
        "peak_bankroll": 1100.0,
    }
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0)
    assert round(out["drawdown_pct"], 2) == round((1100 - 990) / 1100 * 100, 2)


# ── computed.loss_protection_from_session ────────────────────────────────────

def test_loss_protection_from_session_safe_when_no_drawdown(tmp_path: Path) -> None:
    sb = {
        "has_data": True, "bankroll": 1000.0, "realized_pnl": 0.0,
        "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0,
        "peak_bankroll": 1000.0,
    }
    out = computed.loss_protection_from_session(sb, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Safe"
    assert out["down_pct"] == 0.0


def test_loss_protection_from_session_no_data_is_safe(tmp_path: Path) -> None:
    """Session yok → Safe (bot henüz hiç çalışmamış)."""
    sb = {"has_data": False, "open_positions": 0}
    out = computed.loss_protection_from_session(sb, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Safe"
    assert out["down_pct"] == 0.0


def test_loss_protection_from_session_stopped_at_threshold(tmp_path: Path) -> None:
    """Peak=1000, now=480 → drawdown=52% > stop_at_pct=50% → Stopped."""
    sb = {
        "has_data": True, "bankroll": 480.0, "realized_pnl": -520.0,
        "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0,
        "peak_bankroll": 1000.0,
    }
    out = computed.loss_protection_from_session(sb, initial_bankroll=1000.0, stop_at_pct=50.0)
    assert out["status"] == "Stopped"


# ── Reboot senaryosu: audit/positions.json değeri leak etmemeli ─────────────

def test_summary_reboot_scenario_no_session_shows_zero(tmp_path: Path) -> None:
    """Reboot sonrası: session yok, positions.json'da realized=107.37 olsa bile
    dashboard balance/realized_pnl sıfır göstermeli."""
    logs_dir, data_dir = _mk_logs(tmp_path)
    # positions.json'da audit'ten restore edilmiş eski değer var
    _write_positions(tmp_path, realized=107.37)
    # session/equity_history.jsonl YOK (reboot sildirdi)

    client = _client(tmp_path)
    data = client.get("/api/summary").get_json()

    # Balance widget session'dan gelmeli → sıfır
    assert data["equity"]["bankroll"] == 0.0, (
        f"Reboot sonrası bankroll sıfır olmalı, {data['equity']['bankroll']} geldi"
    )
    assert data["equity"]["realized_pnl"] == 0.0, (
        f"Reboot sonrası realized_pnl sıfır olmalı, {data['equity']['realized_pnl']} geldi"
    )


def test_summary_reboot_scenario_session_data_takes_priority(tmp_path: Path) -> None:
    """Session varsa session bankroll'u kullanılmalı; realized_pnl audit
    (session/trade_history.jsonl) toplamından okunur — positions.json görmezden
    gelinmeli (drift-immune SPOT)."""
    logs_dir, data_dir = _mk_logs(tmp_path)
    # positions.json'da farklı bir değer (drift simulation)
    _write_positions(tmp_path, realized=107.37)
    # session'da bankroll değeri
    _write_equity(logs_dir, [
        {"bankroll": 1032.0, "realized_pnl": 32.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
    ])
    # audit trade — realized widget'ı bu kaynaktan okur
    _write_trades(logs_dir, [
        {"condition_id": "0xT1", "entry_timestamp": "ts1",
         "exit_price": 0.6, "exit_pnl_usdc": 32.0, "partial_exits": []},
    ])

    client = _client(tmp_path)
    data = client.get("/api/summary").get_json()

    assert data["equity"]["bankroll"] == 1032.0
    assert data["equity"]["realized_pnl"] == 32.0
    # positions.json'daki 107.37 değil!
    assert data["equity"]["realized_pnl"] != 107.37
