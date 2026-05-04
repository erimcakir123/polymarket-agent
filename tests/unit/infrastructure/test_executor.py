"""executor.py için birim testler."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.config.settings import Mode
from src.infrastructure.executor import Executor, _best_price_from_book


def _mock_ob_resp(best_ask: float) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock(return_value=None)
    # DESC-sorted asks (last = lowest = best); ASC-sorted bids (last = highest = best)
    r.json.return_value = {
        "asks": [{"price": "0.99", "size": "10"}, {"price": f"{best_ask}", "size": "100"}],
        "bids": [{"price": "0.01", "size": "10"}, {"price": f"{best_ask - 0.01:.3f}", "size": "100"}],
    }
    return r


def test_best_price_from_book_asks_desc_uses_last() -> None:
    book = {"asks": [{"price": "0.99", "size": "10"}, {"price": "0.50", "size": "5"}, {"price": "0.48", "size": "20"}]}
    assert _best_price_from_book(book, "BUY") == 0.48


def test_best_price_from_book_bids_asc_uses_last() -> None:
    book = {"bids": [{"price": "0.01", "size": "10"}, {"price": "0.40", "size": "5"}, {"price": "0.46", "size": "20"}]}
    assert _best_price_from_book(book, "SELL") == 0.46


def test_best_price_empty_returns_none() -> None:
    assert _best_price_from_book({"asks": []}, "BUY") is None


def test_executor_dry_run_returns_sim_order() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "simulated"
    assert out["order_id"].startswith("sim_")
    assert out["mode"] == "dry_run"


def test_executor_paper_returns_sim_order() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.PAPER, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "simulated"
    assert out["mode"] == "paper"


def test_executor_live_requires_clob_client() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    with pytest.raises(ValueError, match="clob_client"):
        Executor(mode=Mode.LIVE, http_get=http)  # clob_client yok


def test_executor_live_uses_clob_client() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    clob = MagicMock()
    clob.place_order.return_value = {"order_id": "live_abc", "status": "placed"}
    ex = Executor(mode=Mode.LIVE, http_get=http, clob_client=clob)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["order_id"] == "live_abc"
    assert out["status"] == "placed"
    assert out["mode"] == "live"
    clob.place_order.assert_called_once()


def test_executor_live_exit_uses_market_sell() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    clob = MagicMock()
    clob.place_market_sell.return_value = {"order_id": "exit_xyz", "status": "placed"}
    ex = Executor(mode=Mode.LIVE, http_get=http, clob_client=clob)
    pos = MagicMock(token_id="tok", shares=100, slug="a-vs-b")
    out = ex.exit_position(pos, reason="scale_out")
    assert out["order_id"] == "exit_xyz"
    assert out["mode"] == "live"
    assert out["reason"] == "scale_out"


def test_executor_stale_price_rejects() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.25))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "error"
    assert out["reason"] == "stale_price"


def test_executor_small_drift_adjusts_price() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.415))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.40, size_usdc=40.0)
    assert out["status"] == "simulated"
    assert abs(out["price"] - 0.415) < 1e-6


def test_executor_rejects_fill_above_entry_price_cap() -> None:
    """Scanner 0.85 gecti → CLOB fill 0.89 → cap 0.88 → reject (88¢ bug fix)."""
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.89))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(
        token_id="tok", side="BUY", price=0.85, size_usdc=40.0,
        max_entry_price=0.88,
    )
    assert out["status"] == "error"
    assert out["reason"] == "entry_price_cap"
    assert out["fill_price"] == 0.89
    assert out["cap"] == 0.88


def test_executor_allows_fill_at_exactly_entry_price_cap_minus_epsilon() -> None:
    """Fill < cap → approve."""
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.87))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(
        token_id="tok", side="BUY", price=0.85, size_usdc=40.0,
        max_entry_price=0.88,
    )
    assert out["status"] == "simulated"


def test_executor_no_max_entry_price_param_backward_compatible() -> None:
    """max_entry_price verilmezse eski davranis korunur."""
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.92))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    out = ex.place_order(token_id="tok", side="BUY", price=0.90, size_usdc=40.0)
    assert out["status"] == "simulated"  # cap yok, drift %2.2 < %5 → gecer


def test_executor_exit_position_dry_run() -> None:
    http = MagicMock(return_value=_mock_ob_resp(best_ask=0.40))
    ex = Executor(mode=Mode.DRY_RUN, http_get=http)
    pos = MagicMock(token_id="tok", shares=100, slug="a-vs-b")
    out = ex.exit_position(pos, reason="scale_out")
    assert out["status"] == "simulated"
    assert out["reason"] == "scale_out"
