import pytest


def test_add_position():
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xabc", "tok_yes", "BUY_YES", 0.55, 20.0, 36.36, "test-market")
    assert "0xabc" in pf.positions
    assert pf.positions["0xabc"].entry_price == 0.55


def test_stop_loss_triggered():
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xabc", "tok_yes", "BUY_YES", 0.50, 20.0, 40.0, "test")
    pf.update_price("0xabc", 0.30)  # 60% loss > 30% threshold
    stops = pf.check_stop_losses(stop_loss_pct=0.30)
    assert "0xabc" in stops


def test_take_profit_triggered():
    from src.portfolio import Portfolio
    pf = Portfolio()
    pf.add_position("0xabc", "tok_yes", "BUY_YES", 0.50, 20.0, 40.0, "test")
    pf.update_price("0xabc", 0.80)  # 60% gain > 40% threshold
    takes = pf.check_take_profits(take_profit_pct=0.40)
    assert "0xabc" in takes


def test_high_water_mark():
    from src.portfolio import Portfolio
    pf = Portfolio(initial_bankroll=100.0)
    pf.update_bankroll(150.0)
    assert pf.high_water_mark == 150.0
    pf.update_bankroll(120.0)
    assert pf.high_water_mark == 150.0  # doesn't decrease


def test_drawdown_breaker():
    from src.portfolio import Portfolio
    pf = Portfolio(initial_bankroll=100.0)
    pf.update_bankroll(200.0)  # HWM = 200
    pf.update_bankroll(90.0)   # 55% drawdown
    assert pf.is_drawdown_breaker_active(halt_pct=0.50)
