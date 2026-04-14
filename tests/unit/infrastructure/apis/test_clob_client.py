"""clob_client.py için birim testler (py-clob-client runtime import)."""
from __future__ import annotations

from src.infrastructure.apis.clob_client import (
    LIMIT_OFFSET_CENTS,
    LIQUID_DEPTH_USDC,
    choose_order_strategy,
)


def _book(asks=None, bids=None) -> dict:
    return {"asks": asks or [], "bids": bids or []}


def test_liquid_book_uses_market_fok() -> None:
    # Derinlik $2000, order $40 (< %20) → market FOK
    book = _book(asks=[{"price": "0.50", "size": "4000"}])
    r = choose_order_strategy(book, side="BUY", price=0.50, size_usdc=40.0)
    assert r["strategy"] == "market"
    assert r["order_type"] == "FOK"


def test_illiquid_book_uses_limit_gtc() -> None:
    # Derinlik $40 < $500 eşiği → limit GTC best_ask - 0.01
    book = _book(asks=[{"price": "0.40", "size": "100"}])
    r = choose_order_strategy(book, side="BUY", price=0.40, size_usdc=40.0)
    assert r["strategy"] == "limit"
    assert r["order_type"] == "GTC"
    # Best ask = 0.40 → limit 0.39
    assert r["price"] == 0.39


def test_large_order_ratio_forces_limit() -> None:
    # Derinlik $1000 (likit eşikten büyük), order $300 (> %20) → limit
    book = _book(asks=[{"price": "0.50", "size": "2000"}])
    r = choose_order_strategy(book, side="BUY", price=0.50, size_usdc=300.0)
    assert r["strategy"] == "limit"


def test_sell_side_uses_bids() -> None:
    # Sell likit: bids $2000, order $40 → market FOK
    book = _book(bids=[{"price": "0.50", "size": "4000"}])
    r = choose_order_strategy(book, side="SELL", price=0.50, size_usdc=40.0)
    assert r["strategy"] == "market"


def test_sell_illiquid_limit_above_best_bid() -> None:
    book = _book(bids=[{"price": "0.40", "size": "100"}])
    r = choose_order_strategy(book, side="SELL", price=0.40, size_usdc=40.0)
    assert r["strategy"] == "limit"
    # Best bid 0.40 → limit 0.41 (+ offset)
    assert r["price"] == 0.41


def test_empty_book_limit_fallback() -> None:
    book = _book(asks=[])
    r = choose_order_strategy(book, side="BUY", price=0.50, size_usdc=40.0)
    assert r["strategy"] == "limit"
    # Empty → fallback to input price
    assert r["price"] == round(0.50 - LIMIT_OFFSET_CENTS, 2)


def test_constants() -> None:
    assert LIQUID_DEPTH_USDC == 500.0
    assert LIMIT_OFFSET_CENTS == 0.01
