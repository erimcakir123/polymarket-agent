import pytest


def test_generate_lp_orders():
    from src.liquidity_provider import LiquidityProvider
    from src.config import LPConfig
    lp = LiquidityProvider(LPConfig(spread_cents=1, max_exposure_pct=0.05, min_spread_cents=3))
    orders = lp.generate_orders(
        token_id="tok_yes", midpoint=0.55, spread=0.04, bankroll=100.0
    )
    assert len(orders) == 2
    assert orders[0]["side"] == "BUY"
    assert orders[1]["side"] == "SELL"
    assert orders[0]["price"] < orders[1]["price"]


def test_skip_narrow_spread():
    from src.liquidity_provider import LiquidityProvider
    from src.config import LPConfig
    lp = LiquidityProvider(LPConfig(min_spread_cents=3))
    orders = lp.generate_orders(
        token_id="tok_yes", midpoint=0.55, spread=0.02, bankroll=100.0
    )
    assert len(orders) == 0


def test_max_exposure_cap():
    from src.liquidity_provider import LiquidityProvider
    from src.config import LPConfig
    lp = LiquidityProvider(LPConfig(max_exposure_pct=0.05))
    orders = lp.generate_orders(
        token_id="tok_yes", midpoint=0.50, spread=0.05, bankroll=100.0
    )
    for order in orders:
        assert order["size_usdc"] <= 5.0
