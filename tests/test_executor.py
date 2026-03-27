import pytest
from unittest.mock import MagicMock


def test_dry_run_never_places_real_orders():
    from src.executor import Executor
    from src.config import Mode
    executor = Executor(mode=Mode.DRY_RUN, clob_client=None)
    result = executor.place_order("tok_yes", "BUY", 0.55, 20.0)
    assert result["status"] == "simulated"
    assert result["mode"] == "dry_run"


def test_paper_mode_simulates():
    from src.executor import Executor
    from src.config import Mode
    executor = Executor(mode=Mode.PAPER, clob_client=None)
    result = executor.place_order("tok_yes", "BUY", 0.55, 20.0)
    assert result["status"] == "simulated"
    assert result["mode"] == "paper"


def test_live_mode_requires_client():
    from src.executor import Executor
    from src.config import Mode
    with pytest.raises(ValueError, match="CLOB client required"):
        Executor(mode=Mode.LIVE, clob_client=None)


def test_exit_position_dry_run():
    """exit_position must exist and work in dry_run mode."""
    from src.executor import Executor
    from src.config import Mode

    ex = Executor(mode=Mode.DRY_RUN)
    pos = MagicMock()
    pos.token_id = "tok_abc123"
    pos.shares = 50.0
    pos.slug = "test-market"
    pos.entry_price = 0.60
    pos.current_price = 0.75

    result = ex.exit_position(pos, reason="take_profit", mode=Mode.DRY_RUN)
    assert result["status"] == "simulated"
    assert result["reason"] == "take_profit"


def test_exit_position_live_calls_place_exit_order():
    """In live mode, exit_position should delegate to _execute_live_exit."""
    from src.executor import Executor
    from src.config import Mode
    from unittest.mock import patch

    mock_client = MagicMock()
    ex = Executor(mode=Mode.LIVE, clob_client=mock_client)

    pos = MagicMock()
    pos.token_id = "tok_abc123"
    pos.shares = 50.0
    pos.slug = "test-market"

    with patch.object(ex, '_execute_live_exit', return_value={"order_id": "live_123", "status": "placed", "mode": "live"}) as mock_exit:
        result = ex.exit_position(pos, reason="stop_loss", mode=Mode.LIVE)
        mock_exit.assert_called_once_with(pos.token_id, pos.shares)
        assert result["status"] == "placed"


def test_order_manager_tracks_pending():
    from src.order_manager import OrderManager
    om = OrderManager(stale_after_cycles=2)
    om.add_pending("order_1", "0xabc", "BUY_YES", 0.55, 20.0)
    assert len(om.pending_orders) == 1
    om.tick_cycle()
    om.tick_cycle()
    stale = om.get_stale_orders()
    assert "order_1" in [o["order_id"] for o in stale]
