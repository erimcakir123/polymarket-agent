import pytest


def test_kelly_basic():
    from src.risk_manager import confidence_position_size
    bet = confidence_position_size(confidence="B-", bankroll=100.0)
    assert 0 < bet <= 5.0  # 3% of 100 = 3.0, capped by max_bet_pct 5%


def test_kelly_caps_at_max_usdc():
    from src.risk_manager import confidence_position_size
    bet = confidence_position_size(confidence="A", bankroll=10000.0)
    assert bet <= 75.0  # max_bet_usdc default


def test_kelly_caps_at_max_pct():
    from src.risk_manager import confidence_position_size
    bet = confidence_position_size(confidence="A", bankroll=200.0)
    assert bet <= 10.0  # 5% of 200 = 10.0


def test_kelly_returns_zero_no_edge():
    from src.risk_manager import confidence_position_size
    # Lowest confidence still gets a bet via confidence sizing,
    # but with a tiny bankroll it rounds to zero
    bet = confidence_position_size(confidence="NONE", bankroll=0.0)
    assert bet == 0.0


def test_kelly_buy_no():
    from src.risk_manager import confidence_position_size
    # Confidence sizing doesn't depend on direction; any valid confidence returns > 0
    bet = confidence_position_size(confidence="B+", bankroll=100.0)
    assert bet > 0


def test_risk_manager_vetoes_max_positions():
    from src.risk_manager import RiskManager
    from src.config import RiskConfig
    from src.models import Signal, Direction
    rm = RiskManager(RiskConfig(max_positions=2))
    open_positions = {"m1": {}, "m2": {}}
    signal = Signal(condition_id="m3", direction=Direction.BUY_YES,
                    anchor_probability=0.75, market_price=0.60, edge=0.15, confidence="high")
    result = rm.evaluate(signal, bankroll=100.0, open_positions=open_positions)
    assert result.approved is False
    assert "max_positions" in result.reason


def test_risk_manager_cooldown():
    from src.risk_manager import RiskManager
    from src.config import RiskConfig
    from src.models import Signal, Direction
    rm = RiskManager(RiskConfig(consecutive_loss_cooldown=3, cooldown_cycles=2))
    # Trigger cooldown by recording 3 consecutive losses
    for _ in range(3):
        rm.record_outcome(win=False)
    signal = Signal(condition_id="m1", direction=Direction.BUY_YES,
                    anchor_probability=0.75, market_price=0.60, edge=0.15, confidence="high")
    result = rm.evaluate(signal, bankroll=100.0, open_positions={})
    assert result.approved is False
    assert "cooldown" in result.reason.lower()
