"""Integration: tennis dashboard endpoint'leri — Flask test client + fixture state.

Stage 9 acceptance: dashboard widget'ları doldurmak için gereken her veri kaynağı
ayrı ayrı doğrulanır. Part E artifacts'ından bağımsız: tmp_path altında kendi
fake state'ini kurar.

Coverage:
  - / (index)
  - /api/status, /api/summary, /api/equity_history, /api/positions,
    /api/trades, /api/skipped, /api/stock, /api/stats, /api/sport_roi,
    /api/trades/history
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.config.settings import AppConfig
from src.presentation.dashboard.app import create_app


FAKE_CONDITION = "0xdash000000000000000000000000000000000000000000000000000000fixture"
FAKE_SLUG = "atp-fixture-test-2026-05-20-first-set-winner"


def _write_state(tmp_path: Path) -> None:
    """Tüm dashboard kaynaklarını tmp_path altına yaz."""
    data_dir = tmp_path / "data"
    logs_session = tmp_path / "logs" / "session"
    logs_audit = tmp_path / "logs" / "audit"
    logs_runtime = tmp_path / "logs" / "runtime"
    for d in (data_dir, logs_session, logs_audit, logs_runtime):
        d.mkdir(parents=True, exist_ok=True)

    # positions.json — 1 açık pozisyon
    (data_dir / "positions.json").write_text(json.dumps({
        "realized_pnl": 5.0,
        "high_water_mark": 500.0,
        "positions": {
            FAKE_CONDITION: {
                "condition_id": FAKE_CONDITION, "token_id": "tok1",
                "direction": "BUY_YES", "entry_price": 0.5,
                "size_usdc": 40.0, "shares": 80.0, "slug": FAKE_SLUG,
                "current_price": 0.55, "entry_reason": "tennis",
                "confidence": "A", "anchor_probability": 0.5,
                "sport_tag": "tennis_atp", "question": "Test Q",
            },
        },
    }), encoding="utf-8")

    # bot_status.json
    (data_dir / "bot_status.json").write_text(json.dumps({
        "mode": "paper", "cycle": "light", "stage": "idle",
        "stage_at": "2026-05-20T01:00:00Z",
        "next_heavy_at": "2026-05-20T01:30:00Z",
        "light_alive": True,
    }), encoding="utf-8")

    # stock_queue.json
    (data_dir / "stock_queue.json").write_text(json.dumps([
        {"market": {"slug": "queued-1", "sport_tag": "tennis_atp",
                    "question": "Q", "yes_price": 0.4, "no_price": 0.6,
                    "liquidity": 10000, "volume_24h": 5000,
                    "match_start_iso": "2026-05-20T12:00:00Z"},
         "first_seen_iso": "2026-05-20T00:00:00Z",
         "last_skip_reason": "no_edge"},
    ]), encoding="utf-8")

    # equity_history.jsonl (session — dashboard kaynağı)
    snap = {"timestamp": "2026-05-20T01:00:00+00:00", "bankroll": 505.0,
            "realized_pnl": 5.0, "unrealized_pnl": 4.0,
            "invested": 40.0, "open_positions": 1}
    (logs_session / "equity_history.jsonl").write_text(
        json.dumps(snap) + "\n", encoding="utf-8",
    )

    # trade_history.jsonl — session (kapalı 1 trade)
    closed = {
        "slug": FAKE_SLUG, "condition_id": FAKE_CONDITION,
        "event_id": "evt1", "token_id": "tok1", "question": "Test Q",
        "sport_tag": "tennis_atp", "sport_category": "tennis",
        "league": "atp", "direction": "BUY_YES", "entry_price": 0.5,
        "size_usdc": 40.0, "shares": 80.0, "confidence": "A",
        "bookmaker_prob": 0.0, "anchor_probability": 0.5,
        "entry_reason": "tennis",
        "entry_timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_price": 0.6, "exit_reason": "manual_test",
        "exit_pnl_usdc": 8.0, "exit_pnl_pct": 0.2,
        "exit_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (logs_session / "trade_history.jsonl").write_text(
        json.dumps(closed) + "\n", encoding="utf-8",
    )
    (logs_audit / "trade_history.jsonl").write_text(
        json.dumps(closed) + "\n", encoding="utf-8",
    )

    # skipped_trades.jsonl (runtime/ — reader oraya bakar)
    skipped = {"slug": "skipped-1", "skip_reason": "no_edge",
               "timestamp": "2026-05-20T01:00:00Z", "sport_tag": "tennis_atp"}
    (logs_runtime / "skipped_trades.jsonl").write_text(
        json.dumps(skipped) + "\n", encoding="utf-8",
    )


@pytest.fixture
def client(tmp_path: Path):
    _write_state(tmp_path)
    app = create_app(config=AppConfig(), logs_dir=tmp_path / "logs")
    app.config["TESTING"] = True
    return app.test_client()


def test_index_returns_html(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert b"PolyAgent" in r.data or b"Polymarket" in r.data


def test_status_has_required_keys(client) -> None:
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.get_json()
    assert {"mode", "bot_alive", "cycle", "stage", "stage_at",
            "next_heavy_at", "light_alive"} <= set(data.keys())


def test_summary_reflects_session_equity(client) -> None:
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.get_json()
    assert {"equity", "slots", "loss_protection"} <= set(data.keys())
    assert data["equity"]["bankroll"] == 505.0
    assert data["slots"]["current"] == 1
    assert data["loss_protection"]["status"] in {"Safe", "Caution", "Warning", "Stopped"}


def test_equity_history_returns_snapshot(client) -> None:
    r = client.get("/api/equity_history")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["bankroll"] == 505.0


def test_positions_returns_open_entry(client) -> None:
    r = client.get("/api/positions")
    assert r.status_code == 200
    data = r.get_json()
    assert FAKE_CONDITION in data
    assert data[FAKE_CONDITION]["slug"] == FAKE_SLUG


def test_trades_returns_exit_event(client) -> None:
    r = client.get("/api/trades")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["slug"] == FAKE_SLUG
    assert data[0]["exit_price"] == 0.6


def test_skipped_returns_entry(client) -> None:
    r = client.get("/api/skipped")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["skip_reason"] == "no_edge"


def test_stock_returns_queued(client) -> None:
    r = client.get("/api/stock")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["slug"] == "queued-1"


def test_stats_has_win_loss_keys(client) -> None:
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert set(data.keys()) == {"wins", "losses"}
    assert data["wins"] == 1  # +8 USDC win


def test_sport_roi_groups_tennis(client) -> None:
    r = client.get("/api/sport_roi")
    assert r.status_code == 200
    data = r.get_json()
    assert "summary" in data and "leagues" in data
    assert data["summary"]["total_trades"] == 1
    assert any(g["league"] == "tennis" for g in data["leagues"])


def test_trades_history_returns_monthly_payload(client) -> None:
    r = client.get("/api/trades/history?month_offset=0")
    assert r.status_code == 200
    data = r.get_json()
    assert {"trades", "month_label", "month_offset",
            "has_older", "total_in_month"} <= set(data.keys())
    assert data["month_offset"] == 0
