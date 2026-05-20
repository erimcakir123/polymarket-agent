"""Dashboard widget tutarlılık integration testi (2026-05-20, Phase 4c).

Bug bağlamı: Dashboard'da 4 widget vardı ama hesaplamaları farklı kaynaklardan
geldikleri için tutarsızdı (realized=$127.51 dashboard vs $102.02 audit log).

Bu test bilinen sahte state kurar ve TÜM widget API'larının matematiksel olarak
reconcile olduğunu doğrular:

  Total Equity (m-balance) = bankroll + invested + open_pnl
  Open P&L (m-open-pnl)    = sum(open positions unrealized)
  Realized P&L (m-realized)= sum(audit exits + audit partials)
  Locked (m-locked)        = sum(open positions size_usdc)
  Peak Cash (m-peak)       = max(peak_bankroll, bankroll, initial)
  Open positions count     = len(positions.json positions)

Eski adı "Peak Balance" — Phase 4a-ii'de "Peak Cash" oldu (gerçeği yansıtması için).
"""
from __future__ import annotations

import json
from pathlib import Path

from src.config.settings import AppConfig
from src.presentation.dashboard.app import create_app


def _seed_state(tmp_path: Path) -> dict:
    """Tutarlı bir state kur — bilinen sayılarla."""
    initial = 1000.0
    audit_full_exit_pnl = 50.0
    audit_partial_pnl = 25.0
    audit_realized_total = audit_full_exit_pnl + audit_partial_pnl  # 75.0
    # 1 açık pozisyon: $40 invested, current 0.60, entry 0.40 → unrealized=$20
    open_size = 40.0
    open_shares = 100.0
    open_current = 0.60
    open_unrealized = open_shares * open_current - open_size  # 20.0
    bankroll = initial + audit_realized_total - open_size  # 1000 + 75 - 40 = 1035
    total_equity = bankroll + open_size + open_unrealized  # 1035 + 40 + 20 = 1095

    logs = tmp_path / "logs"
    (logs / "session").mkdir(parents=True)
    (logs / "audit").mkdir(parents=True)
    (logs / "runtime").mkdir(parents=True)
    data = tmp_path / "data"
    data.mkdir()

    # positions.json
    (data / "positions.json").write_text(json.dumps({
        "realized_pnl": audit_realized_total,
        "high_water_mark": 1080.0,  # peak_cash session olmadığı için bu da görünür
        "positions": {
            "0xOP": {
                "condition_id": "0xOP",
                "token_id": "tok-OP",
                "direction": "BUY_YES",
                "entry_price": 0.40,
                "size_usdc": open_size,
                "shares": open_shares,
                "current_price": open_current,
                "bid_price": 0.59,
                "slug": "open-trade",
                "entry_timestamp": "2026-05-20T10:00:00Z",
                "entry_reason": "tennis",
                "confidence": "A",
                "sport_tag": "tennis_atp",
            },
        },
    }), encoding="utf-8")

    # session/equity_history.jsonl — son entry bankroll'u içerir
    eq_path = logs / "session" / "equity_history.jsonl"
    eq_path.write_text(json.dumps({
        "bankroll": bankroll,
        "realized_pnl": audit_realized_total,  # session değeri audit ile match
        "unrealized_pnl": open_unrealized,
        "invested": open_size,
        "open_positions": 1,
    }) + "\n", encoding="utf-8")

    # session/trade_history.jsonl — dashboard widget audit'ten okur
    tr_path = logs / "session" / "trade_history.jsonl"
    records = [
        {"condition_id": "0xEX1", "entry_timestamp": "2026-05-20T08:00:00Z",
         "exit_price": 0.70, "exit_pnl_usdc": audit_full_exit_pnl,
         "exit_timestamp": "2026-05-20T09:00:00Z",
         "partial_exits": []},
        {"condition_id": "0xEX2", "entry_timestamp": "2026-05-20T08:30:00Z",
         "exit_price": None,
         "partial_exits": [{
             "realized_pnl_usdc": audit_partial_pnl, "sell_pct": 0.4, "tier": 1,
             "timestamp": "2026-05-20T09:30:00Z", "price": 0.55,
         }]},
    ]
    tr_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    return {
        "initial": initial,
        "bankroll": bankroll,
        "audit_realized": audit_realized_total,
        "open_unrealized": open_unrealized,
        "open_size": open_size,
        "total_equity": total_equity,
        "open_count": 1,
        "logs_dir": logs,
    }


def _client(logs_dir: Path):
    app = create_app(config=AppConfig(initial_bankroll=1000.0), logs_dir=logs_dir)
    app.config["TESTING"] = True
    return app.test_client()


def test_all_widgets_reconcile_after_phase4_fixes(tmp_path: Path):
    """Phase 3 + 4 sonrası: tüm widget değerleri mathematically reconcile."""
    expected = _seed_state(tmp_path)
    client = _client(expected["logs_dir"])

    summary = client.get("/api/summary").get_json()
    positions = client.get("/api/positions").get_json()
    trades = client.get("/api/trades").get_json()

    # ── Widget 1: Total Equity (m-balance = data.total_equity) ──
    assert summary["equity"]["total_equity"] == expected["total_equity"], (
        f"Total Equity widget {summary['equity']['total_equity']} != "
        f"expected {expected['total_equity']}"
    )

    # ── Widget 2: Open P&L = sum(open positions unrealized) ──
    assert summary["equity"]["open_pnl"] == expected["open_unrealized"]

    # ── Widget 3: Realized P&L = sum(audit exits + partials) — DRIFT-IMMUNE ──
    # Phase 3: dashboard widget audit'ten okur, snapshot drift'inden bağımsız.
    assert summary["equity"]["realized_pnl"] == expected["audit_realized"]

    # ── Widget 4: Locked = sum(open positions size_usdc) ──
    assert summary["equity"]["locked"] == expected["open_size"]

    # ── Widget 5: Peak Cash = max(peak_bankroll, bankroll, initial) ──
    # Session peak = bankroll (tek snapshot), bankroll < initial+realized koşulu
    # için max session value vs initial vs current bankroll.
    expected_peak = max(expected["bankroll"], expected["initial"])
    assert summary["equity"]["peak_balance"] == expected_peak, (
        f"Peak Cash {summary['equity']['peak_balance']} != {expected_peak}"
    )

    # ── Widget 6: Open positions count ──
    assert summary["slots"]["current"] == expected["open_count"]
    assert len(positions) == expected["open_count"]

    # ── Cross-check: bankroll + invested + open_pnl = total_equity (formül identity) ──
    e = summary["equity"]
    assert abs(e["bankroll"] + e["locked"] + e["open_pnl"] - e["total_equity"]) < 0.01

    # ── Cross-check: exited tab event toplamı = realized widget değeri ──
    exit_event_total = 0.0
    for ev in trades:
        if ev.get("partial"):
            exit_event_total += float(ev.get("exit_pnl_usdc") or 0.0)
        elif ev.get("exit_price") is not None:
            exit_event_total += float(ev.get("exit_pnl_usdc") or 0.0)
    assert abs(exit_event_total - e["realized_pnl"]) < 0.01, (
        f"Exited tab toplamı {exit_event_total} != realized widget {e['realized_pnl']}"
    )


def test_realized_widget_immune_to_positions_json_drift(tmp_path: Path):
    """positions.json.realized_pnl kasten drifted; widget audit'ten doğru okumalı."""
    expected = _seed_state(tmp_path)
    # positions.json'ı bozulmuş gibi yeniden yaz: realized = $200 (gerçek $75)
    pos_path = tmp_path / "data" / "positions.json"
    pos = json.loads(pos_path.read_text(encoding="utf-8"))
    pos["realized_pnl"] = 200.00
    pos_path.write_text(json.dumps(pos), encoding="utf-8")

    client = _client(expected["logs_dir"])
    summary = client.get("/api/summary").get_json()

    # Widget hala $75 (audit'ten), $200'a sızmadı
    assert summary["equity"]["realized_pnl"] == 75.00
