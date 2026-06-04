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


# ── Audit fallback (Z11, 2026-05-29) ─────────────────────────────────────────
# Tek-nokta-ariza koruma: session/equity_history.jsonl bilinmeyen sebeple
# silinirse (gizemli scheduler, manual_resolve script vs.) dashboard $0
# gostermek yerine audit/equity_history.jsonl'a fallback yapar.
# read_trades zaten ayni pattern'i kullaniyor (session + audit cift-yedek).


def _write_audit_equity(logs_dir: Path, entries: list[dict]) -> None:
    path = logs_dir / "audit" / "equity_history.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def test_read_balance_session_missing_audit_has_data_falls_back_to_audit(tmp_path: Path) -> None:
    """Session yok, audit dolu -> audit son entry'sinden balance gelir.
    (Mid-run session corruption: $0 gostermek yerine kanonik audit verisi)."""
    logs_dir, _ = _mk_logs(tmp_path)
    _write_audit_equity(logs_dir, [
        {"bankroll": 971.34, "realized_pnl": 236.34, "unrealized_pnl": -2.73,
         "invested": 265.0, "open_positions": 6},
    ])
    out = readers.read_balance_from_session(logs_dir)
    assert out["has_data"] is True
    assert out["bankroll"] == 971.34
    assert out["realized_pnl"] == 236.34
    assert out["open_positions"] == 6


def test_read_balance_session_empty_audit_has_data_falls_back_to_audit(tmp_path: Path) -> None:
    """Session bos dosya, audit dolu -> audit fallback (corrupt session senaryosu)."""
    logs_dir, _ = _mk_logs(tmp_path)
    (logs_dir / "session" / "equity_history.jsonl").write_text("", encoding="utf-8")
    _write_audit_equity(logs_dir, [
        {"bankroll": 1100.0, "realized_pnl": 100.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
    ])
    out = readers.read_balance_from_session(logs_dir)
    assert out["has_data"] is True
    assert out["bankroll"] == 1100.0


def test_read_balance_session_priority_over_audit(tmp_path: Path) -> None:
    """Hem session hem audit dolu -> session oncelik (en taze veri)."""
    logs_dir, _ = _mk_logs(tmp_path)
    _write_equity(logs_dir, [
        {"bankroll": 1050.0, "realized_pnl": 50.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
    ])
    _write_audit_equity(logs_dir, [
        {"bankroll": 999.0, "realized_pnl": -1.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
    ])
    out = readers.read_balance_from_session(logs_dir)
    assert out["bankroll"] == 1050.0  # session wins


def test_read_balance_both_missing_returns_empty(tmp_path: Path) -> None:
    """Ne session ne audit -> _EMPTY (true clean state, e.g. fresh reboot --wipe)."""
    logs_dir, _ = _mk_logs(tmp_path)
    out = readers.read_balance_from_session(logs_dir)
    assert out["has_data"] is False
    assert out["bankroll"] == 0.0


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


# ── computed.realized_pnl_from_trades + trades override ──────────────────────

def test_realized_pnl_from_trades_empty_returns_zero() -> None:
    assert computed.realized_pnl_from_trades([]) == 0.0
    assert computed.realized_pnl_from_trades(None) == 0.0  # type: ignore[arg-type]


def test_realized_pnl_from_trades_sums_full_and_partial_exits() -> None:
    trades = [
        # Full close trade
        {"exit_price": 0.50, "exit_pnl_usdc": -10.0, "partial_exits": []},
        # Trade with both partial exits and full close
        {
            "exit_price": 0.80, "exit_pnl_usdc": 5.0,
            "partial_exits": [
                {"realized_pnl_usdc": 3.0},
                {"realized_pnl_usdc": 2.5},
            ],
        },
        # Partial-only (no full close yet)
        {
            "exit_price": None,
            "partial_exits": [{"realized_pnl_usdc": 1.5}],
        },
    ]
    # -10 + (5 + 3 + 2.5) + 1.5 = 2.0
    assert computed.realized_pnl_from_trades(trades) == 2.0


def test_equity_summary_realized_from_trades_SPEC_Z10() -> None:
    """SPEC-Z10 (2026-05-25): realized widget = trades toplamı (EXITED tab ile AYNI).
    Snapshot priority kaldırıldı — kullanıcı kararı: tek source."""
    sb = {
        "has_data": True,
        "bankroll": 968.16,
        "realized_pnl": -4.88,  # snapshot dikkate alınmaz
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": 0,
        "peak_bankroll": 1000.0,
    }
    trades = [
        {"exit_price": 0.50, "exit_pnl_usdc": -10.0, "partial_exits": []},
        {"exit_price": 0.30, "exit_pnl_usdc": -6.18, "partial_exits": []},
    ]
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0, trades=trades)
    # SPEC-Z10: trades toplamı kazanır
    assert out["realized_pnl"] == -16.18


def test_equity_summary_no_trades_falls_back_to_snapshot_SPEC_Z10() -> None:
    """SPEC-Z10: trades=None ise snapshot fallback (sadece bu durumda)."""
    sb = {
        "has_data": True,
        "bankroll": 1000.0,
        "realized_pnl": 25.0,
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": 0,
        "peak_bankroll": 1000.0,
    }
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0, trades=None)
    assert out["realized_pnl"] == 25.0


def test_equity_summary_from_session_no_trades_falls_back_to_session() -> None:
    """trades=None → session_balance.realized_pnl kullanılır (geriye uyumlu)."""
    sb = {
        "has_data": True,
        "bankroll": 1050.0,
        "realized_pnl": 50.0,
        "unrealized_pnl": 0.0,
        "invested": 0.0,
        "open_positions": 0,
        "peak_bankroll": 1100.0,
    }
    out = computed.equity_summary_from_session(sb, initial_bankroll=1000.0)
    assert out["realized_pnl"] == 50.0


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
    """Session varsa session değeri kullanılmalı — positions.json görmezden gelinmeli.

    SPEC-Z17: realized_pnl widget'ı trade_events.jsonl'den replay edilir
    (reboot-scoped). positions.json'daki kalıcı sayaç (lifetime) kullanılmaz.
    """
    logs_dir, data_dir = _mk_logs(tmp_path)
    # positions.json'da kirli lifetime değer
    _write_positions(tmp_path, realized=107.37)
    # session'da bankroll snapshot
    _write_equity(logs_dir, [
        {"bankroll": 1032.0, "realized_pnl": 32.0, "unrealized_pnl": 0.0,
         "invested": 0.0, "open_positions": 0},
    ])
    # trade_events.jsonl'de son reboot'tan beri biriken exit'ler (= 32.0)
    events = [
        {"kind": "entry", "condition_id": "c1", "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "entry_timestamp": "2026-05-20T00:00:00Z", "entry_price": 0.50},
        {"kind": "final", "condition_id": "c1", "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "exit_price": 0.80, "exit_pnl_usdc": 32.0,
         "exit_reason": "take_profit",
         "exit_timestamp": "2026-05-20T01:00:00Z"},
    ]
    with open(logs_dir / "audit" / "trade_events.jsonl", "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    client = _client(tmp_path)
    data = client.get("/api/summary").get_json()

    assert data["equity"]["bankroll"] == 1032.0
    assert data["equity"]["realized_pnl"] == 32.0
    # positions.json'daki 107.37 değil — lifetime kirliliği UI'ya sızmıyor!
    assert data["equity"]["realized_pnl"] != 107.37
