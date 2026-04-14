"""liquidity.py için birim testler (TDD §6.17)."""
from __future__ import annotations

from src.domain.guards.liquidity import check_entry, check_exit


def _book(asks: list | None = None, bids: list | None = None) -> dict:
    return {"asks": asks or [], "bids": bids or []}


# ── check_entry ──

def test_entry_zero_size_ok() -> None:
    r = check_entry(_book(), size_usdc=0)
    assert r["ok"] is True


def test_entry_no_asks_blocked() -> None:
    r = check_entry(_book(asks=[]), size_usdc=40)
    assert r["ok"] is False
    assert "No asks" in r["reason"]


def test_entry_thin_depth_blocked() -> None:
    # 0.40 × 100 = 40 USDC derinlik < $100 min
    book = _book(asks=[{"price": "0.40", "size": "100"}])
    r = check_entry(book, size_usdc=40, min_depth_usdc=100)
    assert r["ok"] is False
    assert r["depth"] == 40.0


def test_entry_sufficient_depth_ok() -> None:
    # 0.40 × 500 = $200 derinlik
    book = _book(asks=[{"price": "0.40", "size": "500"}])
    r = check_entry(book, size_usdc=40, min_depth_usdc=100)
    assert r["ok"] is True
    assert r["recommended_size"] == 40
    # impact 40/200 = 0.20 → NOT > 0.20 → full size kept
    assert r["impact_ratio"] == 0.20


def test_entry_large_order_halved() -> None:
    # 0.40 × 100 = $40 derinlik, order $20 → impact 0.50 > 0.20 → halve
    # Ama önce min_depth_usdc'yi düşürelim
    book = _book(asks=[{"price": "0.40", "size": "100"}])
    r = check_entry(book, size_usdc=20, min_depth_usdc=10)
    assert r["ok"] is True
    assert r["recommended_size"] == 10.0  # halved


# ── check_exit ──

def test_exit_zero_shares_ok() -> None:
    r = check_exit(_book(), shares_to_sell=0)
    assert r["fillable"] is True


def test_exit_no_bids_skip() -> None:
    r = check_exit(_book(bids=[]), shares_to_sell=100)
    assert r["fillable"] is False
    assert r["strategy"] == "skip"


def test_exit_full_fillable_market() -> None:
    # Bids ASC: last = best = 0.40 × 200 = yeterli derinlik
    book = _book(bids=[{"price": "0.01", "size": "10"}, {"price": "0.40", "size": "200"}])
    r = check_exit(book, shares_to_sell=100)
    assert r["fillable"] is True
    assert r["strategy"] == "market"
    assert r["recommended_price"] == 0.40


def test_exit_partial_fill_limit() -> None:
    # Best bid 0.40, available 85 shares → fill_ratio 0.85 > 0.80 → limit
    book = _book(bids=[{"price": "0.01", "size": "10"}, {"price": "0.40", "size": "85"}])
    r = check_exit(book, shares_to_sell=100, min_fill_ratio=0.80)
    assert r["fillable"] is True
    assert r["strategy"] == "limit"


def test_exit_low_fill_split() -> None:
    book = _book(bids=[{"price": "0.01", "size": "10"}, {"price": "0.40", "size": "30"}])
    r = check_exit(book, shares_to_sell=100, min_fill_ratio=0.80)
    assert r["fillable"] is False
    assert r["strategy"] == "split"


def test_exit_floor_price_filter() -> None:
    # Best bid 0.40, floor 0.40 × 0.95 = 0.38. 0.35 fiyatlı bids sayılmamalı.
    book = _book(bids=[{"price": "0.35", "size": "1000"}, {"price": "0.40", "size": "50"}])
    r = check_exit(book, shares_to_sell=100, min_fill_ratio=0.80)
    # 50 available, 50/100 = 0.5 < 0.80 → split
    assert r["fillable"] is False
    assert r["strategy"] == "split"
