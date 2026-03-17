import pytest


def test_kelly_basic():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.70, market_price=0.55, bankroll=100.0)
    assert 0 < bet <= 15.0  # max 15% of 100


def test_kelly_caps_at_max_usdc():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.90, market_price=0.50, bankroll=10000.0)
    assert bet <= 75.0  # max_single_bet_usdc


def test_kelly_caps_at_max_pct():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.90, market_price=0.50, bankroll=200.0)
    assert bet <= 30.0  # 15% of 200


def test_kelly_returns_zero_no_edge():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.50, market_price=0.55, bankroll=100.0)
    assert bet == 0.0


def test_kelly_buy_no():
    from src.risk_manager import kelly_position_size
    bet = kelly_position_size(ai_prob=0.30, market_price=0.55, bankroll=100.0, direction="BUY_NO")
    assert bet > 0  # AI says NO is underpriced


def test_risk_manager_vetoes_max_positions():
    from src.risk_manager import RiskManager
    from src.config import RiskConfig
    from src.models import Signal, Direction
    rm = RiskManager(RiskConfig(max_positions=2))
    open_positions = {"m1": {}, "m2": {}}
    signal = Signal(condition_id="m3", direction=Direction.BUY_YES,
                    ai_probability=0.75, market_price=0.60, edge=0.15, confidence="high")
    result = rm.evaluate(signal, bankroll=100.0, open_positions=open_positions)
    assert result.approved is False
    assert "max_positions" in result.reason


def test_risk_manager_cooldown():
    from src.risk_manager import RiskManager
    from src.config import RiskConfig
    from src.models import Signal, Direction
    rm = RiskManager(RiskConfig())
    rm.consecutive_losses = 3
    signal = Signal(condition_id="m1", direction=Direction.BUY_YES,
                    ai_probability=0.75, market_price=0.60, edge=0.15, confidence="high")
    result = rm.evaluate(signal, bankroll=100.0, open_positions={})
    assert result.approved is False
    assert "cooldown" in result.reason.lower()
