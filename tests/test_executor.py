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


def test_order_manager_tracks_pending():
    from src.order_manager import OrderManager
    om = OrderManager(stale_after_cycles=2)
    om.add_pending("order_1", "0xabc", "BUY_YES", 0.55, 20.0)
    assert len(om.pending_orders) == 1
    om.tick_cycle()
    om.tick_cycle()
    stale = om.get_stale_orders()
    assert "order_1" in [o["order_id"] for o in stale]
