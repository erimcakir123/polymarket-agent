# src/trailing_sigma.py
"""σ-based trailing stop — volatility-adjusted trailing using rolling standard deviation.
Spec: docs/superpowers/specs/2026-03-23-profit-max-risk-opt-v2-design.md #3

ALL price parameters must be effective (direction-adjusted) prices.
Caller converts: BUY_YES=raw, BUY_NO=1-raw.
"""


def calculate_sigma_trailing_stop(
    peak_pnl_pct: float,
    price_history: list[float],
    current_price: float,
    peak_price: float,
    entry_price: float,
) -> dict:
    if peak_pnl_pct < 0.30 or len(price_history) < 5:
        return {"active": False}

    changes = [price_history[i] - price_history[i - 1] for i in range(1, len(price_history))]
    if not changes:
        return {"active": False}

    mean_change = sum(changes) / len(changes)
    sigma = (sum((c - mean_change) ** 2 for c in changes) / len(changes)) ** 0.5

    if peak_pnl_pct < 0.40:
        z = 3.0
    elif peak_pnl_pct < 0.60:
        z = 2.5
    elif peak_pnl_pct < 0.80:
        z = 2.0
    else:
        z = 1.5

    trail_distance = z * sigma
    stop_price = peak_price - trail_distance
    stop_price = max(stop_price, entry_price)

    triggered = current_price <= stop_price and stop_price > 0

    return {
        "active": True,
        "sigma": sigma,
        "z_score": z,
        "trail_distance": trail_distance,
        "stop_price": stop_price,
        "peak_price": peak_price,
        "triggered": triggered,
        "reason": f"σ-trail: {current_price:.3f} {'<' if triggered else '>='} stop {stop_price:.3f}",
    }
