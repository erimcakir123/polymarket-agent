"""Kelly criterion sizing — fractional Kelly with max cap.

Binary market (Polymarket): pay `price` per share, win 1.0 on YES, 0 on NO.
- net win per $ staked = (1-price)/price
- net loss per $ staked = 1

Kelly fraction: f* = (p - price) / (1 - price), clamped at 0.

Fractional Kelly (multiplier < 1) variance'ı düşürür. Pratik 0.25x-0.5x.
max_pct bankroll güvenlik kapağı — Kelly aşırı agresif olamaz.

Tüm hesap saf math (domain).
"""
from __future__ import annotations

_MIN_DENOM = 1e-6


def kelly_fraction(p: float, price: float) -> float:
    """P(win) ve fiyat → optimal stake fraction. No edge / extreme price → 0."""
    if price <= 0 or price >= 1.0 - _MIN_DENOM:
        return 0.0
    if p <= price:
        return 0.0
    return (p - price) / (1.0 - price)


def bet_size(
    p: float,
    price: float,
    bankroll: float,
    kelly_multiplier: float,
    max_pct: float,
) -> float:
    """Fractional Kelly stake USDC, max_pct kapaklı."""
    if bankroll <= 0:
        return 0.0
    f = kelly_fraction(p, price)
    raw = bankroll * f * kelly_multiplier
    cap = bankroll * max_pct
    return min(raw, cap)
