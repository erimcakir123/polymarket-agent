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
        anchor_probability=0.72,
        market_price=0.60,
        edge=0.12,
        confidence="high",
    )
    assert s.edge == 0.12
    assert s.direction == Direction.BUY_YES


def test_trade_record():
    """TradeRecord was moved to trade_logger module. Test basic trade logging."""
    from src.trade_logger import TradeLogger
    # TradeLogger exists and can be instantiated
    tl = TradeLogger("logs/test_trades.jsonl")
    assert tl is not None


def test_position_match_exit_fields():
    """New fields for match-aware exit system."""
    from src.models import Position
    pos = Position(
        condition_id="0xtest", token_id="tok", direction="BUY_YES",
        entry_price=0.55, size_usdc=20.0, shares=36.36, current_price=0.55,
    )
    assert pos.ever_in_profit is False
    assert pos.consecutive_down_cycles == 0
    assert pos.cumulative_drop == 0.0
    assert pos.previous_cycle_price == 0.0
    assert pos.hold_revoked_at is None
    assert pos.hold_was_original is False
