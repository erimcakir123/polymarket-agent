"""Dashboard route'ları için birim testler — Flask test client ile.

Routes thin handlers; her endpoint readers + computed çağırır.
Layer violation kontrolü: routes.py infrastructure import etmemeli.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.config.settings import AppConfig
from src.presentation.dashboard import routes as routes_module
from src.presentation.dashboard.app import create_app


# ── Katman ihlali kontrolü ──

def test_routes_module_has_no_infra_imports() -> None:
    path = Path(routes_module.__file__)
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from src.infrastructure", "import src.infrastructure",
        "from src.domain", "import src.domain",
        "from src.strategy", "import src.strategy",
        "from src.orchestration", "import src.orchestration",
    ):
        assert forbidden not in source, f"Layer violation: {forbidden}"


# ── Helpers ──

def _logs(tmp_path: Path) -> Path:
    """Standart logs_dir; data/ → tmp_path/data/, audit/ → logs/audit/."""
    return tmp_path / "logs"


def _client(tmp_path: Path):
    app = create_app(config=AppConfig(), logs_dir=_logs(tmp_path))
    app.config["TESTING"] = True
    return app.test_client()


def _write_positions(tmp_path: Path, positions: dict, realized: float = 0.0, hwm: float = 1000.0) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "positions.json").write_text(json.dumps({
        "positions": positions, "realized_pnl": realized, "high_water_mark": hwm,
    }), encoding="utf-8")


# ── Index ──

def test_index_returns_html(tmp_path: Path) -> None:
    r = _client(tmp_path).get("/")
    assert r.status_code == 200
    assert b"Polymarket Agent" in r.data or b"PolyAgent" in r.data


# ── /api/status ──

def test_status_cold_returns_bot_not_alive(tmp_path: Path) -> None:
    r = _client(tmp_path).get("/api/status")
    data = r.get_json()
    assert data["bot_alive"] is False
    assert data["mode"] == "dry_run"


# /api/equity, /api/slots, /api/loss_protection → consolidated to /api/summary.
# Computation correctness tested in test_computed.py; route delivery tested below.


def test_summary_cold_state_has_three_sections(tmp_path: Path) -> None:
    # session yok (reboot sonrası) → bankroll=0, Safe status
    data = _client(tmp_path).get("/api/summary").get_json()
    assert set(data.keys()) >= {"equity", "slots", "loss_protection"}
    assert data["equity"]["bankroll"] == 0.0  # session yok → sıfır
    assert data["slots"]["current"] == 0
    assert data["loss_protection"]["status"] == "Safe"
    assert data["loss_protection"]["stop_at_pct"] == 8.0  # abs(-0.08) * 100


def _write_session_equity(tmp_path: Path, entries: list[dict]) -> None:
    """test/session/equity_history.jsonl yaz."""
    import json as _json
    session_dir = tmp_path / "logs" / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / "equity_history.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(_json.dumps(e) + "\n")


def _write_session_trades(tmp_path: Path, trades: list[dict]) -> None:
    """test/session/trade_history.jsonl yaz."""
    import json as _json
    session_dir = tmp_path / "logs" / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / "trade_history.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for t in trades:
            f.write(_json.dumps(t) + "\n")


def test_summary_reflects_session_equity(tmp_path: Path) -> None:
    """Balance widget session equity'den okumalı; realized_pnl audit'ten gelir."""
    _write_session_equity(tmp_path, [
        {"bankroll": 1042.0, "realized_pnl": 42.0, "unrealized_pnl": 8.0,
         "invested": 40.0, "open_positions": 1},
    ])
    # realized_pnl widget audit log'undan hesaplanır (SPEC paritesi).
    _write_session_trades(tmp_path, [
        {"condition_id": "0xT1", "entry_timestamp": "ts1",
         "exit_price": 0.6, "exit_pnl_usdc": 42.0, "partial_exits": []},
    ])
    data = _client(tmp_path).get("/api/summary").get_json()
    assert data["equity"]["bankroll"] == 1042.0
    assert data["equity"]["realized_pnl"] == 42.0
    assert data["equity"]["open_pnl"] == 8.0


def test_summary_slots_still_uses_positions(tmp_path: Path) -> None:
    """Slot sayısı positions.json'dan gelmeye devam etmeli."""
    _write_positions(tmp_path, {
        "c1": {"direction": "BUY_YES", "entry_price": 0.4,
               "current_price": 0.5, "size_usdc": 40.0, "shares": 100.0,
               "entry_reason": "normal"}
    })
    data = _client(tmp_path).get("/api/summary").get_json()
    assert data["slots"]["current"] == 1
    assert data["slots"]["by_reason"] == {"normal": 1}


# ── /api/positions ──

def test_positions_empty(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/positions").get_json() == {}


def test_positions_with_data(tmp_path: Path) -> None:
    _write_positions(tmp_path, {
        "c1": {"slug": "x", "direction": "BUY_YES", "entry_price": 0.4,
               "current_price": 0.5, "size_usdc": 40.0, "shares": 100.0}
    })
    data = _client(tmp_path).get("/api/positions").get_json()
    assert "c1" in data


# ── /api/trades ──

def test_trades_empty(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/trades").get_json() == []


def test_trades_returns_only_closed(tmp_path: Path) -> None:
    session_dir = _logs(tmp_path) / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    closed = json.dumps({"slug": "c-closed", "exit_price": 0.55,
                         "exit_timestamp": "2026-04-14T12:00:00Z"})
    open_trade = json.dumps({"slug": "c-open", "exit_price": None,
                             "exit_timestamp": ""})
    (session_dir / "trade_history.jsonl").write_text(
        closed + "\n" + open_trade + "\n", encoding="utf-8",
    )
    data = _client(tmp_path).get("/api/trades").get_json()
    assert len(data) == 1
    assert data[0]["slug"] == "c-closed"


def test_trades_attaches_replay_simulation_when_present(tmp_path: Path) -> None:
    """exit_event'lerin replay_simulation alanı data/replay_simulation.json'dan zenginleşir."""
    session_dir = _logs(tmp_path) / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    closed = json.dumps({
        "slug": "atp-x-set-handicap-home-1pt5",
        "condition_id": "0xAAA",
        "entry_timestamp": "2026-05-25T10:00:00Z",
        "exit_price": 0.32,
        "exit_pnl_usdc": -9.84,
        "exit_timestamp": "2026-05-25T18:14:07Z",
        "direction": "BUY_YES",
        "size_usdc": 20.0,
        "shares": 31.25,
    })
    (session_dir / "trade_history.jsonl").write_text(
        closed + "\n", encoding="utf-8",
    )
    sim = {
        "schema_version": 1,
        "trades": [{
            "condition_id": "0xAAA",
            "entry_timestamp": "2026-05-25T10:00:00Z",
            "slug": "atp-x-set-handicap-home-1pt5",
            "actual_pnl_usdc": -9.84,
            "fixes": [{"label": "bimodal_sl_exempt",
                       "if_held_pnl_usdc": 11.25, "delta_usdc": 21.09}],
        }],
    }
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "replay_simulation.json").write_text(
        json.dumps(sim), encoding="utf-8",
    )
    data = _client(tmp_path).get("/api/trades").get_json()
    assert len(data) == 1
    event = data[0]
    assert event.get("replay_simulation") is not None
    assert event["replay_simulation"]["fixes"][0]["label"] == "bimodal_sl_exempt"
    assert event["replay_simulation"]["fixes"][0]["delta_usdc"] == 21.09


def test_trades_no_replay_simulation_when_file_missing(tmp_path: Path) -> None:
    """File yoksa replay_simulation eklenmemeli (mevcut alan değişmez)."""
    session_dir = _logs(tmp_path) / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    closed = json.dumps({
        "slug": "x", "condition_id": "0xZ", "entry_timestamp": "t",
        "exit_price": 0.5, "exit_pnl_usdc": 1.0,
        "exit_timestamp": "2026-05-25T10:00:00Z",
    })
    (session_dir / "trade_history.jsonl").write_text(closed + "\n", encoding="utf-8")
    data = _client(tmp_path).get("/api/trades").get_json()
    assert len(data) == 1
    assert "replay_simulation" not in data[0]


# ── /api/equity_history ──

def test_equity_history_empty(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/equity_history").get_json() == []


def test_equity_history_returns_snapshots(tmp_path: Path) -> None:
    session_dir = _logs(tmp_path) / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"timestamp": "t", "bankroll": 1000.0, "realized_pnl": 0.0,
                       "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0})
    (session_dir / "equity_history.jsonl").write_text(line + "\n", encoding="utf-8")
    data = _client(tmp_path).get("/api/equity_history").get_json()
    assert len(data) == 1
    assert data[0]["bankroll"] == 1000.0


# ── /api/skipped ──

def test_skipped_empty(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/skipped").get_json() == []


def test_skipped_returns_records(tmp_path: Path) -> None:
    runtime_dir = _logs(tmp_path) / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"slug": "s1", "skip_reason": "no_edge",
                       "timestamp": "t", "sport_tag": "tennis_atp"})
    (runtime_dir / "skipped_trades.jsonl").write_text(line + "\n", encoding="utf-8")
    data = _client(tmp_path).get("/api/skipped").get_json()
    assert len(data) == 1
    assert data[0]["skip_reason"] == "no_edge"


# ── /api/stock ──

def test_stock_empty(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/stock").get_json() == []


def test_stock_returns_entries(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "stock_queue.json").write_text(
        json.dumps([{"slug": "q1", "sport_tag": "basketball_nba"}]), encoding="utf-8",
    )
    data = _client(tmp_path).get("/api/stock").get_json()
    assert len(data) == 1
    assert data[0]["slug"] == "q1"
