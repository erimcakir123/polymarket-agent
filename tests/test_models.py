import pytest
from datetime import datetime, timezone


def test_market_data_creation():
    from src.models import MarketData
    m = MarketData(
        condition_id="0xabc", question="Will X happen?",
        yes_price=0.65, no_price=0.35,
        yes_token_id="tok_yes", no_token_id="tok_no",
        volume_24h=100000, liquidity=20000,
        slug="will-x-happen", tags=["politics"],
        end_date_iso="2026-12-01T00:00:00Z",
    )
    assert m.yes_price + m.no_price == pytest.approx(1.0)
    assert m.condition_id == "0xabc"


def test_position_pnl():
    from src.models import Position
    p = Position(
        condition_id="0xabc", token_id="tok_yes",
        direction="BUY_YES", entry_price=0.50,
        size_usdc=20.0, shares=40.0,
        current_price=0.65, slug="test-market",
    )
    assert p.unrealized_pnl_usdc == pytest.approx(6.0)
    assert p.unrealized_pnl_pct == pytest.approx(0.30)


def test_signal_creation():
    from src.models import Signal, Direction
    s = Signal(
        condition_id="0xabc",
        direction=Direction.BUY_YES,
        ai_probability=0.72,
        market_price=0.60,
        edge=0.12,
        confidence="high",
    )
    assert s.edge == 0.12
    assert s.direction == Direction.BUY_YES


def test_trade_record():
    from src.models import TradeRecord
    t = TradeRecord(
        condition_id="0xabc", slug="test",
        direction="BUY_YES", size_usdc=15.0,
        price=0.55, edge=0.08, confidence="medium",
        mode="dry_run", status="executed",
    )
    assert t.mode == "dry_run"
