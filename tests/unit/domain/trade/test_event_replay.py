"""SPEC-Z17: event replay — pure function, deterministic."""
from src.domain.trade.event_replay import replay_events


def test_empty_events_returns_empty_list() -> None:
    assert replay_events([]) == []


def test_single_entry_event_creates_open_trade() -> None:
    events = [{
        "kind": "entry", "condition_id": "cid1", "slug": "s1",
        "question": "q", "sport_tag": "tennis", "source": "model",
        "direction": "BUY_YES", "entry_price": 0.45, "entry_timestamp": "t1",
        "size_usdc": 50.0, "shares": 100.0, "confidence": "A",
    }]
    trades = replay_events(events)
    assert len(trades) == 1
    assert trades[0]["condition_id"] == "cid1"
    assert trades[0]["entry_price"] == 0.45
    assert trades[0]["exit_price"] is None
    assert trades[0]["partial_exits"] == []


def test_partial_event_appended_to_trade() -> None:
    events = [
        {"kind": "entry", "condition_id": "c1", "entry_price": 0.5, "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "direction": "BUY_YES", "entry_timestamp": "t0",
         "size_usdc": 50, "shares": 100, "confidence": "A"},
        {"kind": "partial", "condition_id": "c1", "tier": 1, "sell_pct": 0.4,
         "realized_pnl_usdc": -3.0, "timestamp": "t1", "price": 0.4},
    ]
    trades = replay_events(events)
    assert len(trades) == 1
    assert len(trades[0]["partial_exits"]) == 1
    assert trades[0]["partial_exits"][0]["realized_pnl_usdc"] == -3.0


def test_final_event_closes_trade() -> None:
    events = [
        {"kind": "entry", "condition_id": "c1", "entry_price": 0.5, "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "direction": "BUY_YES", "entry_timestamp": "t0",
         "size_usdc": 50, "shares": 100, "confidence": "A"},
        {"kind": "final", "condition_id": "c1", "exit_price": 1.0,
         "exit_reason": "near_resolve", "exit_pnl_usdc": 25.0,
         "exit_timestamp": "t2"},
    ]
    trades = replay_events(events)
    assert trades[0]["exit_price"] == 1.0
    assert trades[0]["exit_pnl_usdc"] == 25.0


def test_orphan_partial_creates_synth_trade() -> None:
    """Entry yok ama partial geldi → synth kayit (orphan recovery)."""
    events = [{"kind": "partial", "condition_id": "orphan1",
               "slug": "s", "question": "q", "sport_tag": "tennis",
               "source": "model", "tier": 1, "sell_pct": 0.3,
               "realized_pnl_usdc": -2.0, "timestamp": "t", "price": 0.5}]
    trades = replay_events(events)
    assert len(trades) == 1
    assert trades[0]["entry_reason"] == "synth-from-event:Z17"
    assert trades[0]["entry_price"] is None


def test_orphan_final_overlay_when_no_entry() -> None:
    events = [{"kind": "final", "condition_id": "o1",
               "slug": "s", "question": "q", "sport_tag": "tennis",
               "source": "model", "exit_price": 0.0,
               "exit_reason": "stale", "exit_pnl_usdc": -10.0,
               "exit_timestamp": "t"}]
    trades = replay_events(events)
    assert trades[0]["exit_pnl_usdc"] == -10.0
    assert trades[0]["entry_price"] is None


def test_double_final_keeps_first_only() -> None:
    """Ayni cid icin iki final event geldi: ilk uygulanir, ikinci ATLANIR."""
    events = [
        {"kind": "entry", "condition_id": "c1", "entry_price": 0.5, "slug": "s",
         "question": "q", "sport_tag": "tennis", "source": "model",
         "direction": "BUY_YES", "entry_timestamp": "t0",
         "size_usdc": 50, "shares": 100, "confidence": "A"},
        {"kind": "final", "condition_id": "c1", "exit_price": 1.0,
         "exit_reason": "near_resolve", "exit_pnl_usdc": 5.0,
         "exit_timestamp": "t1"},
        {"kind": "final", "condition_id": "c1", "exit_price": 1.0,
         "exit_reason": "duplicate", "exit_pnl_usdc": 5.0,
         "exit_timestamp": "t2"},
    ]
    trades = replay_events(events)
    assert trades[0]["exit_pnl_usdc"] == 5.0  # tek kez sayilir
    assert trades[0]["exit_reason"] == "near_resolve"  # ilk final korunur
