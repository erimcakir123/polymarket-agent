"""Sıçrama reddi iki-taraflı kotasyonla doğrulanır.

Gerçek çöküş (ask+bid birlikte düşer, tutarlı kota) kabul edilir; tek taraflı
bayat baskı (KBO: ask fırlar ama bid yerinde) reddedilir.
"""
from src.infrastructure.websocket.price_feed import PriceFeed


def _feed():
    return PriceFeed(on_price_update=None, max_spike_pct=0.50,
                     max_spike_corroboration_spread=0.10)


def test_corroborated_collapse_accepted():
    pf = _feed()
    pf._update_price("t", yes_price=0.48, bid_price=0.47)   # baseline
    # Gerçek çöküş: ask ve bid birlikte ~0'a (tutarlı iki-taraflı kota)
    pf._update_price("t", yes_price=0.02, bid_price=0.01)
    assert abs(pf._prices["t"].yes_price - 0.02) < 1e-9   # kabul edildi


def test_one_sided_stale_spike_rejected():
    pf = _feed()
    pf._update_price("t", yes_price=0.61, bid_price=0.60)  # baseline
    # KBO: ask 0.97'ye fırladı ama bid hâlâ 0.60 (geniş spread → sahte)
    pf._update_price("t", yes_price=0.97, bid_price=0.60)
    assert abs(pf._prices["t"].yes_price - 0.61) < 1e-9   # reddedildi, eski kaldı


def test_small_move_always_accepted():
    pf = _feed()
    pf._update_price("t", yes_price=0.50, bid_price=0.49)
    pf._update_price("t", yes_price=0.52, bid_price=0.51)  # %50 altı → her zaman kabul
    assert abs(pf._prices["t"].yes_price - 0.52) < 1e-9
