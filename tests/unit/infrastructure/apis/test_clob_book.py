"""ClobBook — Polymarket orderbook fetch + TTL cache."""
from unittest.mock import MagicMock

from src.infrastructure.apis.clob_book import ClobBook


def _resp(status: int, payload: dict):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


def _book(asks=None, bids=None) -> dict:
    return {"asks": asks or [], "bids": bids or []}


def test_fetch_returns_parsed_bids_asks() -> None:
    http = MagicMock(return_value=_resp(200, _book(
        asks=[{"price": "0.65", "size": "100"}],
        bids=[{"price": "0.63", "size": "200"}],
    )))
    book = ClobBook(http_get=http, cache_ttl_sec=5)
    out = book.fetch("tok1")
    assert out["asks"] == [{"price": "0.65", "size": "100"}]
    assert out["bids"] == [{"price": "0.63", "size": "200"}]


def test_cache_hit_no_extra_http() -> None:
    http = MagicMock(return_value=_resp(200, _book(asks=[{"price": "0.65", "size": "100"}])))
    book = ClobBook(http_get=http, cache_ttl_sec=60)
    book.fetch("tok1")
    book.fetch("tok1")
    assert http.call_count == 1, "second call must hit cache"


def test_cache_expired_refetches() -> None:
    http = MagicMock(return_value=_resp(200, _book()))
    book = ClobBook(http_get=http, cache_ttl_sec=0)
    book.fetch("tok1")
    book.fetch("tok1")
    assert http.call_count == 2, "expired cache must refetch"


def test_http_error_returns_empty_book() -> None:
    http = MagicMock(side_effect=Exception("boom"))
    book = ClobBook(http_get=http, cache_ttl_sec=5)
    out = book.fetch("tok1")
    assert out == {"asks": [], "bids": []}


def test_different_tokens_cached_separately() -> None:
    http = MagicMock(return_value=_resp(200, _book()))
    book = ClobBook(http_get=http, cache_ttl_sec=60)
    book.fetch("tok1")
    book.fetch("tok2")
    assert http.call_count == 2
