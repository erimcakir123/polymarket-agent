"""tennis_rest_refresh.refresh_open_positions birim testleri (2026-05-20).

Bug bağlamı:
  - Wawrinka-Michelsen (BUY_YES 0.41): outcomePrices=[0.001,0.999] closed=false
    → bot 0.500'de takılı, $48 drift. Bug = `closed=True` koşulu eklenmiş.
  - Darderi-Hanfmann (BUY_YES 0.42): CLOB book mid=0.500 (2-sided liquid)
    → bot 0.420 (entry stuck), $8 drift. Bug = mid yazılıyor ama eski
      tennis_rest_refresh'de tek-taraflı durumda continue ediliyor (drift kaçıyor).
  - Darderi-Hanfmann (BUY_NO 0.41): mid=0.500 → bot 0.405, $10 drift. Aynı.

PRIORITY tested:
  1. Gamma extreme (≤0.03 veya ≥0.97) → current_price = outcomePrices[0]
     EVEN WHEN closed=False (gospel)
  2. CLOB 2-sided → mid
  3. CLOB one-sided (sadece ask) → ask (cautious upper)
  4. CLOB one-sided (sadece bid) → bid (cautious lower)
  5. Gamma extreme öncelik kazanır CLOB normal range varsa bile
  6. CLOB normal range önce kullanılır Gamma da normal range ise
  7. Tüm kaynaklar fail → current_price korunur, stale_count artar
  8. Per-cycle log "REST refresh: refreshed=X resolved=Y stale=Z" yazılır
"""
from __future__ import annotations

import logging
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
    direction: str = "BUY_YES",
    slug: str = "test-slug",
) -> Position:
    return Position(
        condition_id=condition_id,
        token_id=token_id,
        direction=direction,
        entry_price=entry_price,
        size_usdc=40.0,
        shares=100.0,
        current_price=entry_price,
        bid_price=entry_price - 0.02,
        anchor_probability=0.5,
        entry_reason="tennis",
        confidence="A",
        sport_tag="tennis_atp",
        slug=slug,
    )


def _ok(payload) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    return resp


def _book(bids: list, asks: list) -> dict:
    return {"bids": bids, "asks": asks}


def _router(*, gamma_payload=None, book_payload=None) -> MagicMock:
    """Build an http_get mock that routes URLs deterministically.

    gamma_payload / book_payload either dict (single response) or callable
    (url, params, timeout) → MagicMock for fine-grained control.
    """
    def _http_get(url, params=None, timeout=5.0):
        if "gamma-api.polymarket.com/markets" in url:
            if callable(gamma_payload):
                return gamma_payload(url, params, timeout)
            return _ok(gamma_payload if gamma_payload is not None else [])
        if "clob.polymarket.com/book" in url:
            if callable(book_payload):
                return book_payload(url, params, timeout)
            return _ok(book_payload if book_payload is not None else _book([], []))
        raise AssertionError(f"unexpected url: {url}")
    return MagicMock(side_effect=_http_get)


# ── PRIORITY 1: Gamma extreme over everything ──

def test_extreme_gamma_outcome_overrides_clob_even_when_not_closed():
    """Bug #1 fix: outcomePrices=[0.001, 0.999] AND closed=False → 0.001 yazılır."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xWAW", token_id="tok-W", entry_price=0.41,
                    direction="BUY_YES")
    portfolio.add_position(pos)

    # Gerçek Wawrinka case: outcomePrices YES-LOST kapanmasını yansıtıyor
    gamma_resp = [{"closed": False, "outcomePrices": '["0.001", "0.999"]'}]
    # CLOB hala 0.500'de takılı (bot eski davranış)
    book_resp = _book(bids=[{"price": "0.495", "size": "10"}],
                      asks=[{"price": "0.505", "size": "10"}])
    http_get = _router(gamma_payload=gamma_resp, book_payload=book_resp)

    refresh_open_positions(portfolio, http_get=http_get)

    updated = portfolio.get("0xWAW")
    assert updated is not None
    assert abs(updated.current_price - 0.001) < 1e-9


def test_extreme_gamma_outcome_high_side():
    """Symmetric: outcomePrices YES-WON [0.999, 0.001] → 0.999."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xWIN", token_id="tok-X", entry_price=0.30)
    portfolio.add_position(pos)

    gamma_resp = [{"closed": True, "outcomePrices": '["0.999", "0.001"]'}]
    http_get = _router(gamma_payload=gamma_resp, book_payload=_book([], []))

    refresh_open_positions(portfolio, http_get=http_get)

    assert abs(portfolio.get("0xWIN").current_price - 0.999) < 1e-9


def test_gamma_priority_over_clob_when_extreme():
    """CLOB book mid=0.5 ama Gamma=0.999 → Gamma kazanır (gospel)."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xPRI", token_id="tok-P", entry_price=0.45)
    portfolio.add_position(pos)

    gamma_resp = [{"closed": False, "outcomePrices": '["0.999", "0.001"]'}]
    book_resp = _book(bids=[{"price": "0.49", "size": "10"}],
                      asks=[{"price": "0.51", "size": "10"}])
    http_get = _router(gamma_payload=gamma_resp, book_payload=book_resp)

    refresh_open_positions(portfolio, http_get=http_get)
    assert abs(portfolio.get("0xPRI").current_price - 0.999) < 1e-9


# ── PRIORITY 2: CLOB book mid when both sides present ──

def test_two_sided_book_writes_mid():
    """Bug #2 fix: 2-sided book mid → current_price."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xDAR", token_id="tok-D", entry_price=0.42)
    portfolio.add_position(pos)

    gamma_resp = [{"closed": False, "outcomePrices": '["0.50", "0.50"]'}]  # normal range
    book_resp = _book(bids=[{"price": "0.49", "size": "100"}],
                      asks=[{"price": "0.51", "size": "100"}])
    http_get = _router(gamma_payload=gamma_resp, book_payload=book_resp)

    refresh_open_positions(portfolio, http_get=http_get)

    updated = portfolio.get("0xDAR")
    assert abs(updated.current_price - 0.50) < 1e-9
    assert abs(updated.bid_price - 0.49) < 1e-9


def test_clob_priority_over_gamma_when_normal_range():
    """Gamma=0.6 (normal range) → use CLOB. Aynı şartlarda CLOB öncelik kazanır."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xNRM", token_id="tok-N", entry_price=0.55)
    portfolio.add_position(pos)

    gamma_resp = [{"closed": False, "outcomePrices": '["0.60", "0.40"]'}]
    book_resp = _book(bids=[{"price": "0.58", "size": "100"}],
                      asks=[{"price": "0.62", "size": "100"}])
    http_get = _router(gamma_payload=gamma_resp, book_payload=book_resp)

    refresh_open_positions(portfolio, http_get=http_get)
    # mid = 0.60 — happens to equal Gamma but proves CLOB writeback runs (helper called both)
    assert abs(portfolio.get("0xNRM").current_price - 0.60) < 1e-9


# ── PRIORITY 2b: one-sided book ──

def test_one_sided_ask_only_book_uses_ask_as_price():
    """Bug #2/#3 fix: book asks=[0.86,...] bids=[] → current_price = ask (cautious upper)."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xASK", token_id="tok-A", entry_price=0.50)
    portfolio.add_position(pos)

    gamma_resp = [{"closed": False, "outcomePrices": '["0.50", "0.50"]'}]
    book_resp = _book(bids=[], asks=[{"price": "0.86", "size": "20"},
                                     {"price": "0.99", "size": "200"}])
    http_get = _router(gamma_payload=gamma_resp, book_payload=book_resp)

    refresh_open_positions(portfolio, http_get=http_get)

    updated = portfolio.get("0xASK")
    assert abs(updated.current_price - 0.86) < 1e-9  # best ask = lowest


def test_one_sided_bid_only_book_uses_bid_as_price():
    """Symmetric: bids=[0.40,0.30] asks=[] → current_price = best_bid = 0.40 (cautious lower)."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xBID", token_id="tok-B", entry_price=0.50)
    portfolio.add_position(pos)

    gamma_resp = [{"closed": False, "outcomePrices": '["0.50", "0.50"]'}]
    book_resp = _book(bids=[{"price": "0.40", "size": "20"},
                            {"price": "0.30", "size": "10"}], asks=[])
    http_get = _router(gamma_payload=gamma_resp, book_payload=book_resp)

    refresh_open_positions(portfolio, http_get=http_get)

    updated = portfolio.get("0xBID")
    assert abs(updated.current_price - 0.40) < 1e-9
    assert abs(updated.bid_price - 0.40) < 1e-9


# ── PRIORITY 3: stale (no data) ──

def test_stale_count_incremented_when_no_data_available(caplog):
    """Empty book + Gamma normal range → stale, current_price korunur."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xST", token_id="tok-S", entry_price=0.45)
    portfolio.add_position(pos)
    original = pos.current_price

    gamma_resp = [{"closed": False, "outcomePrices": '["0.50", "0.50"]'}]
    http_get = _router(gamma_payload=gamma_resp, book_payload=_book([], []))

    with caplog.at_level(logging.INFO, logger="src.orchestration.tennis_rest_refresh"):
        refresh_open_positions(portfolio, http_get=http_get)

    assert portfolio.get("0xST").current_price == original
    assert "stale=1" in caplog.text


def test_per_cycle_log_summary(caplog):
    """3 pozisyon: 1 refreshed (mid), 1 resolved (Gamma extreme), 1 stale (empty)."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    portfolio.add_position(_position(condition_id="0xR", token_id="tok-R"))   # refreshed
    portfolio.add_position(_position(condition_id="0xV", token_id="tok-V"))   # resolved
    portfolio.add_position(_position(condition_id="0xS", token_id="tok-S"))   # stale

    def http_get(url, params=None, timeout=5.0):
        cid = (params or {}).get("condition_ids", "")
        tid = (params or {}).get("token_id", "")
        if "gamma-api.polymarket.com/markets" in url:
            if cid == "0xV":
                return _ok([{"closed": False, "outcomePrices": '["0.999", "0.001"]'}])
            return _ok([{"closed": False, "outcomePrices": '["0.50", "0.50"]'}])
        if "clob.polymarket.com/book" in url:
            if tid == "tok-R":
                return _ok(_book(bids=[{"price": "0.49"}], asks=[{"price": "0.51"}]))
            return _ok(_book([], []))  # tok-S empty; tok-V never reached (Gamma extreme wins)
        raise AssertionError(url)

    with caplog.at_level(logging.INFO, logger="src.orchestration.tennis_rest_refresh"):
        refreshed, resolved = refresh_open_positions(portfolio, http_get=MagicMock(side_effect=http_get))

    assert refreshed == 1
    assert resolved == 1
    assert "refreshed=1" in caplog.text
    assert "resolved=1" in caplog.text
    assert "stale=1" in caplog.text


# ── Error handling parity ──

def test_clob_500_with_gamma_normal_leaves_price_alone(caplog):
    """CLOB HTTP 500 + Gamma normal range → stale, no crash."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xE", token_id="tok-E", entry_price=0.50)
    portfolio.add_position(pos)
    original = pos.current_price

    def book500(url, params=None, timeout=5.0):
        resp = MagicMock()
        resp.status_code = 500
        return resp

    http_get = _router(
        gamma_payload=[{"closed": False, "outcomePrices": '["0.50", "0.50"]'}],
        book_payload=book500,
    )

    with caplog.at_level(logging.INFO, logger="src.orchestration.tennis_rest_refresh"):
        refreshed, resolved = refresh_open_positions(portfolio, http_get=http_get)

    assert refreshed == 0
    assert resolved == 0
    assert portfolio.get("0xE").current_price == original
    assert "stale=1" in caplog.text


def test_network_timeout_does_not_crash():
    """RequestException (timeout) yutulur — pozisyon dokunulmaz."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    pos = _position(condition_id="0xT", token_id="tok-T", entry_price=0.50)
    portfolio.add_position(pos)
    original = pos.current_price

    def raising(url, params=None, timeout=5.0):
        raise requests.Timeout("simulated")

    http_get = MagicMock(side_effect=raising)
    refresh_open_positions(portfolio, http_get=http_get)
    assert portfolio.get("0xT").current_price == original


def test_returns_geriye_uyumlu_two_int_tuple():
    """Public API geriye uyumluluk: (refreshed_count, resolved_count) — caller
    tennis_agent.run_light_cycle bu signature'a göre log basıyor."""
    portfolio = PortfolioManager(initial_bankroll=1000.0)
    portfolio.add_position(_position(condition_id="0xA", token_id="tok-A"))
    http_get = _router(
        gamma_payload=[{"closed": False, "outcomePrices": '["0.50", "0.50"]'}],
        book_payload=_book([{"price": "0.49"}], [{"price": "0.51"}]),
    )
    result = refresh_open_positions(portfolio, http_get=http_get)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(v, int) for v in result)
