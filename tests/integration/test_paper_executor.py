"""Integration: PaperExecutor end-to-end (book → strategy → fill → audit)."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.config.settings import PaperConfig
from src.orchestration.paper_executor import PaperExecutor


def _book_resp(asks, bids):
    m = MagicMock()
    m.status_code = 200
    m.raise_for_status = MagicMock()
    m.json.return_value = {"asks": asks, "bids": bids}
    return m


def _ask(p, s):
    return {"price": str(p), "size": str(s)}


def _bid(p, s):
    return _ask(p, s)


def test_paper_buy_filled_writes_audit() -> None:
    with tempfile.TemporaryDirectory() as td:
        audit = Path(td) / "exec.jsonl"
        # Polymarket asks DESC; best ask at end (0.65)
        book = _book_resp(asks=[_ask(0.70, 1000), _ask(0.65, 100)], bids=[_bid(0.62, 200)])
        http = MagicMock(return_value=book)
        px = PaperExecutor(config=PaperConfig(), audit_path=audit, http_get=http)
        result = px.place_buy(token_id="tok1", target_price=0.65, target_size_usdc=50.0)
        assert result["status"] == "FILLED"
        assert result["filled_size_usdc"] == 50.0
        assert audit.exists()
        assert audit.read_text(encoding="utf-8").strip() != ""


def test_paper_buy_below_min_order_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=Path(td) / "exec.jsonl",
            http_get=MagicMock(return_value=_book_resp([], [])),
        )
        result = px.place_buy(token_id="tok1", target_price=0.65, target_size_usdc=0.5)
        assert result["status"] == "REJECTED"
        assert "min_order" in result["reason"]


def test_paper_sell_partial_keeps_remaining_shares() -> None:
    with tempfile.TemporaryDirectory() as td:
        # bids ASC; best at end (0.65). Only 30 shares demand.
        book = _book_resp(asks=[], bids=[_bid(0.65, 30)])
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=Path(td) / "exec.jsonl",
            http_get=MagicMock(return_value=book),
        )
        result = px.place_sell(token_id="tok1", target_price=0.65, shares=100.0)
        assert result["status"] == "PARTIAL_FILL"
        assert result["filled_shares"] == 30.0


def test_paper_sell_no_bids_rejected_stuck() -> None:
    with tempfile.TemporaryDirectory() as td:
        px = PaperExecutor(
            config=PaperConfig(),
            audit_path=Path(td) / "exec.jsonl",
            http_get=MagicMock(return_value=_book_resp([], [])),
        )
        result = px.place_sell(token_id="tok1", target_price=0.65, shares=50.0)
        assert result["status"] == "REJECTED"
        assert result["filled_shares"] == 0.0
