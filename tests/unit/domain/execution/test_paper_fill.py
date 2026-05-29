"""paper_fill — pure orderbook walker. Domain layer, no I/O."""
from src.domain.execution.paper_fill import FillStatus, walk_buy, walk_sell


def _ask(price: float, size: float) -> dict:
    return {"price": str(price), "size": str(size)}


def _bid(price: float, size: float) -> dict:
    return _ask(price, size)


def test_walk_buy_full_fill_at_target() -> None:
    asks = [_ask(0.65, 100.0)]
    r = walk_buy(asks, 0.65, 50.0, 0.02, 0.95)
    assert r.status == FillStatus.FILLED
    assert r.filled_size_usdc == 50.0
    assert abs(r.weighted_avg_price - 0.65) < 1e-9


def test_walk_buy_partial_through_levels_weighted_avg() -> None:
    asks = [_ask(0.66, 100.0), _ask(0.65, 30.0)]  # DESC: 0.66 then 0.65; best=last (0.65)
    r = walk_buy(asks, 0.66, 50.0, 0.02, 0.95)
    assert r.status == FillStatus.FILLED
    assert r.filled_size_usdc == 50.0
    expected_shares = 30.0 + (50.0 - 30 * 0.65) / 0.66
    assert abs(r.filled_shares - expected_shares) < 1e-6


def test_walk_buy_rejected_when_below_min_fill_ratio() -> None:
    asks = [_ask(0.65, 30.0)]
    r = walk_buy(asks, 0.65, 100.0, 0.02, 0.95)
    assert r.status == FillStatus.REJECTED
    assert r.filled_size_usdc == 0.0


def test_walk_buy_rejected_when_slippage_exceeded() -> None:
    asks = [_ask(0.70, 100.0)]
    r = walk_buy(asks, 0.65, 50.0, 0.02, 0.95)
    assert r.status == FillStatus.REJECTED


def test_walk_buy_partial_within_slippage_still_rejected_if_below_min_fill() -> None:
    asks = [_ask(0.72, 1000.0), _ask(0.65, 20.0)]  # DESC; best=0.65
    r = walk_buy(asks, 0.65, 100.0, 0.02, 0.95)
    assert r.status == FillStatus.REJECTED


def test_walk_buy_empty_asks_rejected() -> None:
    r = walk_buy([], 0.65, 50.0, 0.02, 0.95)
    assert r.status == FillStatus.REJECTED


def test_walk_sell_full_fill() -> None:
    bids = [_bid(0.65, 100.0)]
    r = walk_sell(bids, 0.65, 50.0, 0.05)
    assert r.status == FillStatus.FILLED
    assert r.filled_shares == 50.0


def test_walk_sell_partial_fill_returns_partial() -> None:
    bids = [_bid(0.65, 30.0)]
    r = walk_sell(bids, 0.65, 100.0, 0.05)
    assert r.status == FillStatus.PARTIAL_FILL
    assert r.filled_shares == 30.0


def test_walk_sell_no_bids_rejected() -> None:
    r = walk_sell([], 0.65, 50.0, 0.05)
    assert r.status == FillStatus.REJECTED


def test_walk_sell_first_bid_below_slippage_rejected() -> None:
    bids = [_bid(0.30, 1000.0)]
    r = walk_sell(bids, 0.65, 50.0, 0.05)
    assert r.status == FillStatus.REJECTED


def test_walk_sell_zero_shares_is_filled_zero() -> None:
    r = walk_sell([_bid(0.65, 100.0)], 0.65, 0.0, 0.05)
    assert r.status == FillStatus.FILLED
    assert r.filled_shares == 0.0


def test_walk_buy_weighted_avg_multiple_levels() -> None:
    asks = [_ask(0.67, 100.0), _ask(0.66, 10.0), _ask(0.65, 10.0)]  # DESC; best=0.65
    r = walk_buy(asks, 0.67, 50.0, 0.05, 0.95)
    assert r.status == FillStatus.FILLED
    assert r.filled_size_usdc == 50.0
    total_shares = 10.0 + 10.0 + (50.0 - 6.50 - 6.60) / 0.67
    assert abs(r.filled_shares - total_shares) < 1e-6
