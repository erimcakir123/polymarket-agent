from src.domain.trade.loss_tracking import closed_at_loss_cids


def test_closed_at_loss_cids_net_negative_final_marked():
    events = [
        {"kind": "entry", "condition_id": "A", "entry_price": 0.6},
        {"kind": "partial", "condition_id": "A", "realized_pnl_usdc": -3.0},
        {"kind": "final", "condition_id": "A", "exit_pnl_usdc": -10.0},
    ]
    assert closed_at_loss_cids(events) == {"A"}


def test_closed_at_loss_cids_net_positive_not_marked():
    events = [
        {"kind": "entry", "condition_id": "B"},
        {"kind": "final", "condition_id": "B", "exit_pnl_usdc": 5.0},
    ]
    assert closed_at_loss_cids(events) == set()


def test_closed_at_loss_cids_open_no_final_not_marked():
    events = [{"kind": "entry", "condition_id": "C"}]
    assert closed_at_loss_cids(events) == set()


def test_closed_at_loss_cids_ignores_missing_condition_id():
    events = [{"kind": "final", "exit_pnl_usdc": -1.0}]
    assert closed_at_loss_cids(events) == set()


def test_closed_at_loss_cids_reentry_net_negative_marked():
    """Aynı cid'e 2 episode (ind-nyl deseni): toplam net < 0 → işaretli."""
    events = [
        {"kind": "entry", "condition_id": "RE"},
        {"kind": "final", "condition_id": "RE", "exit_pnl_usdc": -10.56},
        {"kind": "entry", "condition_id": "RE"},
        {"kind": "final", "condition_id": "RE", "exit_pnl_usdc": -24.93},
    ]
    assert closed_at_loss_cids(events) == {"RE"}
