"""SPEC-Z17: dashboard readers event log'dan trade replay eder."""
import json
from pathlib import Path

from src.presentation.dashboard import readers


def _mk(tmp_path: Path) -> Path:
    logs = tmp_path / "logs"
    (logs / "audit").mkdir(parents=True)
    (logs / "session").mkdir(parents=True)
    return logs


def test_read_trades_replays_from_event_log(tmp_path: Path) -> None:
    logs = _mk(tmp_path)
    events = [
        {"kind": "entry", "condition_id": "c1", "slug": "s",
         "question": "Foo vs Bar", "sport_tag": "tennis",
         "source": "model", "direction": "BUY_YES",
         "entry_price": 0.45, "entry_timestamp": "t0",
         "size_usdc": 50.0, "shares": 100.0, "confidence": "A",
         "bookmaker_prob": 0.5, "anchor_probability": 0.5,
         "num_bookmakers": 5.0, "has_sharp": True,
         "entry_reason": "normal"},
        {"kind": "partial", "condition_id": "c1", "slug": "s",
         "question": "Foo vs Bar", "sport_tag": "tennis",
         "source": "model", "tier": 1, "sell_pct": 0.4,
         "realized_pnl_usdc": 5.0, "timestamp": "t1", "price": 0.8},
        {"kind": "final", "condition_id": "c1", "slug": "s",
         "question": "Foo vs Bar", "sport_tag": "tennis",
         "source": "model", "exit_price": 1.0,
         "exit_reason": "near_resolve", "exit_pnl_usdc": 10.0,
         "exit_timestamp": "t2"},
    ]
    (logs / "audit" / "trade_events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )
    trades = readers.read_trades(logs, n=100)
    assert len(trades) == 1
    assert trades[0]["entry_price"] == 0.45
    assert trades[0]["exit_pnl_usdc"] == 10.0
    assert len(trades[0]["partial_exits"]) == 1


def test_read_trades_ignores_trade_history_jsonl(tmp_path: Path) -> None:
    """Z17 sonrası trade_history.jsonl YOK SAYILIR (truth = event log)."""
    logs = _mk(tmp_path)
    (logs / "audit" / "trade_history.jsonl").write_text(
        json.dumps({"condition_id": "LEGACY", "exit_pnl_usdc": 999.0}) + "\n",
        encoding="utf-8",
    )
    trades = readers.read_trades(logs, n=100)
    cids = [t.get("condition_id") for t in trades]
    assert "LEGACY" not in cids


def test_read_trades_empty_event_log(tmp_path: Path) -> None:
    logs = _mk(tmp_path)
    assert readers.read_trades(logs, n=100) == []


def test_session_and_audit_dedupe_via_event_signature(tmp_path: Path) -> None:
    """SPEC-Z17: aynı event hem session hem audit'te varsa tek sayılır."""
    logs = _mk(tmp_path)
    ev = {"kind": "final", "condition_id": "c1", "slug": "s",
          "question": "q", "sport_tag": "tennis", "source": "model",
          "exit_price": 1.0, "exit_reason": "r",
          "exit_pnl_usdc": 5.0, "exit_timestamp": "t"}
    payload = json.dumps(ev) + "\n"
    (logs / "audit" / "trade_events.jsonl").write_text(payload, encoding="utf-8")
    (logs / "session" / "trade_events.jsonl").write_text(payload, encoding="utf-8")
    trades = readers.read_trades(logs, n=100)
    assert len(trades) == 1
    assert trades[0]["exit_pnl_usdc"] == 5.0
