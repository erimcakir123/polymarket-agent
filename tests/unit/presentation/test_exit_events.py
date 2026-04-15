"""computed.exit_events — full + partial exit flatten testleri."""
from __future__ import annotations

from src.presentation.dashboard.computed import exit_events


def _trade(**kwargs):
    base = {
        "slug": "mlb-x-y-2026-04-15",
        "sport_tag": "mlb",
        "direction": "BUY_YES",
        "entry_price": 0.60,
        "question": "X vs Y",
        "size_usdc": 50.0,
        "exit_price": None,
        "exit_pnl_usdc": 0.0,
        "exit_reason": "",
        "exit_timestamp": "",
        "partial_exits": [],
    }
    base.update(kwargs)
    return base


def test_no_partials_only_full_exit_yielded():
    t = _trade(exit_price=0.70, exit_pnl_usdc=5.0, exit_reason="near_resolve",
              exit_timestamp="2026-04-15T10:00:00+00:00")
    result = exit_events([t])
    assert len(result) == 1
    assert result[0]["partial"] is False
    assert result[0]["exit_pnl_usdc"] == 5.0


def test_partial_yields_separate_event_with_partial_flag():
    t = _trade(partial_exits=[
        {"tier": 1, "sell_pct": 0.40, "realized_pnl_usdc": 3.0,
         "timestamp": "2026-04-15T11:00:00+00:00"},
    ])
    result = exit_events([t])
    assert len(result) == 1
    ev = result[0]
    assert ev["partial"] is True
    assert ev["exit_reason"] == "scale_out_tier_1"
    assert ev["exit_pnl_usdc"] == 3.0
    assert ev["sell_pct"] == 0.40
    assert ev["exit_price"] is None
    assert ev["slug"] == "mlb-x-y-2026-04-15"


def test_full_plus_partial_both_yielded():
    t = _trade(
        exit_price=0.75, exit_pnl_usdc=7.5, exit_reason="graduated_sl",
        exit_timestamp="2026-04-15T12:00:00+00:00",
        partial_exits=[
            {"tier": 1, "sell_pct": 0.40, "realized_pnl_usdc": 3.0,
             "timestamp": "2026-04-15T11:00:00+00:00"},
        ],
    )
    result = exit_events([t])
    assert len(result) == 2
    partials = [e for e in result if e["partial"]]
    fulls = [e for e in result if not e["partial"]]
    assert len(partials) == 1 and len(fulls) == 1


def test_sort_descending_by_timestamp():
    trades = [
        _trade(slug="a", exit_price=0.70, exit_timestamp="2026-04-15T09:00:00+00:00"),
        _trade(slug="b", exit_price=0.70, exit_timestamp="2026-04-15T15:00:00+00:00"),
        _trade(slug="c", exit_price=0.70, exit_timestamp="2026-04-15T12:00:00+00:00"),
    ]
    result = exit_events(trades)
    assert [e["slug"] for e in result] == ["b", "c", "a"]


def test_position_still_open_with_partial_yields_event():
    """Regression: tam exit yok (exit_price=None) ama partial var → yine gösterilir."""
    t = _trade(
        exit_price=None,
        partial_exits=[
            {"tier": 1, "sell_pct": 0.40, "realized_pnl_usdc": 5.40,
             "timestamp": "2026-04-15T13:00:00+00:00"},
        ],
    )
    result = exit_events([t])
    assert len(result) == 1
    assert result[0]["partial"] is True
    assert result[0]["exit_pnl_usdc"] == 5.40


def test_empty_partials_list_no_crash():
    t = _trade(partial_exits=None)
    result = exit_events([t])
    assert result == []
