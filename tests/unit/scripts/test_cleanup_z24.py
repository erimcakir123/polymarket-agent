"""SPEC-Z26 tek-seferlik temizlik saf fonksiyon testleri."""
from scripts.cleanup_z24 import remove_events, removed_events, rebuild_equity


def test_remove_events_full_slug_drops_all_episodes():
    events = [
        {"kind": "entry", "slug": "S1", "condition_id": "c1", "entry_timestamp": "t0"},
        {"kind": "final", "slug": "S1", "condition_id": "c1", "exit_pnl_usdc": -1.0},
        {"kind": "entry", "slug": "KEEP", "condition_id": "c9", "entry_timestamp": "t0"},
    ]
    out = remove_events(events, full_slugs={"S1"}, episodes=[])
    assert [e["slug"] for e in out] == ["KEEP"]


def test_remove_events_episode_keeps_first_drops_targeted():
    events = [
        {"kind": "entry", "slug": "ML", "condition_id": "c", "entry_timestamp": "t1"},
        {"kind": "final", "slug": "ML", "condition_id": "c", "exit_pnl_usdc": -10.0,
         "exit_timestamp": "t1b"},
        {"kind": "entry", "slug": "ML", "condition_id": "c", "entry_timestamp": "t2"},
        {"kind": "final", "slug": "ML", "condition_id": "c", "exit_pnl_usdc": -24.0,
         "exit_timestamp": "t2b"},
    ]
    out = remove_events(events, full_slugs=set(), episodes=[("ML", "t2")])
    entries = [e["entry_timestamp"] for e in out if e["kind"] == "entry"]
    assert entries == ["t1"]
    assert len(out) == 2


def test_remove_events_episode_keeps_other_slugs_between():
    """Episode silinirken araya giren BAŞKA slug event'leri korunur."""
    events = [
        {"kind": "entry", "slug": "ML", "condition_id": "c", "entry_timestamp": "t2"},
        {"kind": "entry", "slug": "OTHER", "condition_id": "z", "entry_timestamp": "tx"},
        {"kind": "final", "slug": "ML", "condition_id": "c", "exit_pnl_usdc": -24.0,
         "exit_timestamp": "t2b"},
    ]
    out = remove_events(events, full_slugs=set(), episodes=[("ML", "t2")])
    assert [e["slug"] for e in out] == ["OTHER"]


def test_removed_events_returns_dropped_only():
    events = [
        {"kind": "entry", "slug": "S1", "condition_id": "c1", "entry_timestamp": "t0"},
        {"kind": "entry", "slug": "KEEP", "condition_id": "c9", "entry_timestamp": "t0"},
    ]
    dropped = removed_events(events, full_slugs={"S1"}, episodes=[])
    assert [e["slug"] for e in dropped] == ["S1"]


def test_rebuild_equity_subtracts_removed_realized():
    removed = [
        {"kind": "final", "exit_pnl_usdc": -24.0,
         "exit_timestamp": "2026-06-07T01:00:00+00:00",
         "entry_timestamp": "2026-06-07T00:00:00+00:00", "size_usdc": 50.0},
    ]
    snaps = [
        {"timestamp": "2026-06-07T02:00:00+00:00", "bankroll": 900.0, "realized_pnl": -24.0,
         "unrealized_pnl": 0.0, "invested": 0.0, "open_positions": 0},
    ]
    out = rebuild_equity(snaps, removed, initial_bankroll=1000.0)
    assert out[0]["realized_pnl"] == 0.0
    assert out[0]["bankroll"] == 924.0
    assert out[0]["unrealized_pnl"] == 0.0


def test_rebuild_equity_open_window_removes_invested():
    """Silinen pozisyon açıkken (entry<=T<final) invested + bankroll düzelir."""
    removed = [
        {"kind": "final", "exit_pnl_usdc": -24.0,
         "exit_timestamp": "2026-06-07T03:00:00+00:00",
         "entry_timestamp": "2026-06-07T00:00:00+00:00", "size_usdc": 50.0},
    ]
    snaps = [
        {"timestamp": "2026-06-07T01:00:00+00:00", "bankroll": 950.0, "realized_pnl": 0.0,
         "unrealized_pnl": -2.0, "invested": 50.0, "open_positions": 1},
    ]
    out = rebuild_equity(snaps, removed, initial_bankroll=1000.0)
    # T=01:00 → pozisyon açık: invested 50→0, bankroll 950+50=1000, open 1→0
    assert out[0]["invested"] == 0.0
    assert out[0]["bankroll"] == 1000.0
    assert out[0]["open_positions"] == 0
    assert out[0]["unrealized_pnl"] == -2.0  # titreme dokunulmaz
