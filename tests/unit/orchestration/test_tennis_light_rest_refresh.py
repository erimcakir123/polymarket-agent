"""tennis_rest_refresh.refresh_open_positions birim testleri (2026-05-20).

Senaryolar:
  - test_light_cycle_refreshes_prices_via_rest: book mid → current_price güncellenir
  - test_light_cycle_detects_resolved_market_via_empty_book: boş book + Gamma
    closed=true → current_price = resolved outcomePrice (RESOLVED exit trigger)
  - test_light_cycle_continues_on_rest_error: HTTP 500 / timeout → fiyat dokunulmaz,
    exception propagate olmaz

WS callback'i karıştırmaz — sadece REST refresh pathway'i test eder.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests

from src.domain.portfolio.manager import PortfolioManager
from src.models.position import Position
from src.orchestration.tennis_rest_refresh import refresh_open_positions


def _position(
    *,
    condition_id: str = "0xCID1",
    token_id: str = "tok1",
    entry_price: float = 0.40,
) -> Position:
    return Position(
        condition_id=condition_id,
        token_id=token_id,
        direction="BUY_YES",
        entry_price=entry_price,
        size_usdc=40.0,
        shares=100.0,
        current_price=entry_price,
        bid_price=entry_price - 0.02,
        anchor_probability=0.5,
        entry_reason="tennis",
        confidence="A",
        sport_tag="tennis_atp",
    )


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    return resp


def _bookendpoint(bids: list, asks: list) -> dict:
    return {"bids": bids, "asks": asks}


def test_light_cycle_refreshes_prices_via_rest() -> None:
    """Book hem bid hem ask içeriyorsa mid → current_price + best_bid → bid_price."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(token_id="tok-A", entry_price=0.40)
    portfolio.add_position(pos)

    # Polymarket REST yanıtı — bid 0.48, ask 0.50 → mid 0.49
    book = _bookendpoint(
        bids=[{"price": "0.48", "size": "100"}, {"price": "0.47", "size": "50"}],
        asks=[{"price": "0.50", "size": "80"}, {"price": "0.51", "size": "40"}],
    )
    http_get = MagicMock(return_value=_ok_response(book))

    refreshed, resolved = refresh_open_positions(portfolio, http_get=http_get)

    assert refreshed == 1
    assert resolved == 0
    updated = portfolio.get("0xCID1")
    assert updated is not None
    assert abs(updated.current_price - 0.49) < 1e-9
    assert abs(updated.bid_price - 0.48) < 1e-9


def test_light_cycle_detects_resolved_market_via_empty_book() -> None:
    """Boş book + Gamma closed=true → outcomePrices[0] → current_price (RESOLVED trigger)."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xRESOLVED", token_id="tok-R", entry_price=0.45)
    portfolio.add_position(pos)

    empty_book = _bookendpoint(bids=[], asks=[])
    # outcomePrices ["1", "0"] → YES kazandı (current_price 1.0 olmalı)
    gamma_resp = _ok_response([{
        "closed": True,
        "outcomePrices": '["1", "0"]',
    }])

    def http_get(url: str, params: dict | None = None, timeout: float = 5.0) -> MagicMock:
        if "clob.polymarket.com/book" in url:
            return _ok_response(empty_book)
        if "gamma-api.polymarket.com/markets" in url:
            return gamma_resp
        raise AssertionError(f"unexpected url: {url}")

    refreshed, resolved = refresh_open_positions(portfolio, http_get=http_get)

    assert refreshed == 0
    assert resolved == 1
    updated = portfolio.get("0xRESOLVED")
    assert updated is not None
    assert updated.current_price == 1.0


def test_light_cycle_continues_on_rest_error() -> None:
    """REST 500 / RequestException → fiyat dokunulmaz, exception bubble OLMAZ."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(token_id="tok-X", entry_price=0.50)
    portfolio.add_position(pos)
    original_price = pos.current_price
    original_bid = pos.bid_price

    def http_get(url: str, params: dict | None = None, timeout: float = 5.0) -> MagicMock:
        # İlk pozisyon: HTTP 500 (helper warning loglar, continue eder)
        resp = MagicMock()
        resp.status_code = 500
        return resp

    # Hata cycle'ı çökertmemeli
    refreshed, resolved = refresh_open_positions(portfolio, http_get=http_get)
    assert refreshed == 0
    assert resolved == 0
    # Fiyat değişmemiş olmalı
    assert portfolio.get("0xCID1").current_price == original_price
    assert portfolio.get("0xCID1").bid_price == original_bid

    # Network timeout senaryosu — RequestException de yutulmalı
    def raising_http(url: str, params: dict | None = None, timeout: float = 5.0):
        raise requests.Timeout("simulated timeout")

    refreshed2, resolved2 = refresh_open_positions(portfolio, http_get=raising_http)
    assert refreshed2 == 0
    assert resolved2 == 0
    assert portfolio.get("0xCID1").current_price == original_price


def test_light_cycle_empty_book_not_closed_leaves_price_alone() -> None:
    """Edge: boş book + Gamma closed=false → current_price dokunulmaz (resolved değil)."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xPRE", token_id="tok-P", entry_price=0.45)
    portfolio.add_position(pos)
    original = pos.current_price

    empty_book = _bookendpoint(bids=[], asks=[])
    gamma_resp = _ok_response([{"closed": False, "outcomePrices": '["0.5", "0.5"]'}])

    def http_get(url: str, params: dict | None = None, timeout: float = 5.0) -> MagicMock:
        if "clob.polymarket.com/book" in url:
            return _ok_response(empty_book)
        return gamma_resp

    refreshed, resolved = refresh_open_positions(portfolio, http_get=http_get)
    assert refreshed == 0
    assert resolved == 0
    assert portfolio.get("0xPRE").current_price == original


def test_light_cycle_partial_book_one_sided_leaves_price_alone() -> None:
    """Edge: book asymmetric (sadece ask, bid boş) → mid hesaplanmaz, fiyat dokunulmaz.

    Bu durum Polymarket'te resolved-but-not-yet-marked-closed market'lerde gözlenir
    (asks 0.86-0.99 ama bids boş). Helper bunu "resolved sinyali değil, hesaplanamaz"
    olarak yorumlar — sadece (0,0) tam boş book Gamma'ya gider.
    """
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(token_id="tok-S", entry_price=0.50)
    portfolio.add_position(pos)
    original = pos.current_price

    one_sided = _bookendpoint(
        bids=[],
        asks=[{"price": "0.86", "size": "20"}, {"price": "0.99", "size": "200"}],
    )
    http_get = MagicMock(return_value=_ok_response(one_sided))

    refreshed, resolved = refresh_open_positions(portfolio, http_get=http_get)
    assert refreshed == 0
    assert resolved == 0
    assert portfolio.get("0xCID1").current_price == original
    # Gamma'ya gitmemiş olmalı — sadece book çağrısı
    assert http_get.call_count == 1
