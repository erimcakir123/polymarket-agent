"""Order executor — dry_run/paper simulate; live gerçek CLOB'a yollar.

Live mode wire'ı Faz 3'te: `ClobOrderClient` DI ile verilir, yoksa RuntimeError.
Stale-price guard her mode'da aktif (scanner fiyatı CLOB'dan fazla sapmasın).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

import requests

from src.config.settings import Mode

logger = logging.getLogger(__name__)

_CLOB_BOOK_URL = "https://clob.polymarket.com/book"
_DEFAULT_TIMEOUT = 10

# Scanner fiyatı ile CLOB live fiyat farkı > bu oran → reject
STALE_PRICE_MAX_DRIFT = 0.05


def _default_http_get(url: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


def _best_price_from_book(book: dict, side: str) -> float | None:
    """Polymarket non-standard sort: asks DESC / bids ASC → [-1] best."""
    levels = book.get("asks" if side == "BUY" else "bids", [])
    if not levels:
        return None
    try:
        return float(levels[-1].get("price", 0)) or None
    except (TypeError, ValueError, KeyError):
        return None


class Executor:
    def __init__(
        self,
        mode: Mode,
        http_get: Callable[..., Any] = _default_http_get,
        clob_client: Any = None,
    ) -> None:
        self.mode = mode
        self._http = http_get
        self._clob = clob_client
        if mode == Mode.LIVE and clob_client is None:
            raise ValueError("LIVE mode requires clob_client (ClobOrderClient)")

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size_usdc: float,
        max_entry_price: float | None = None,
    ) -> dict:
        # Stale-price guard (dry/paper/live hepsinde)
        stale = self._check_stale_price(token_id, side, price)
        if stale["reject"]:
            return stale["result"]
        price = stale["adjusted_price"]

        # Max entry price guard — CLOB fill adjustment gate'i atlatmasin.
        # Scanner fiyati < cap geciyor, ama drift sonrasi clob_fill > cap olabilir.
        if max_entry_price is not None and price >= max_entry_price:
            logger.warning("ENTRY_PRICE_CAP_REJECT: %s side=%s fill=%.3f cap=%.3f",
                           token_id[:16], side, price, max_entry_price)
            return {
                "order_id": f"rej_{uuid.uuid4().hex[:8]}",
                "status": "error", "reason": "entry_price_cap",
                "mode": self.mode.value, "token_id": token_id, "side": side,
                "fill_price": price, "cap": max_entry_price,
            }

        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            return self._simulate_order(token_id, side, price, size_usdc)

        # LIVE
        book = self._fetch_book(token_id)
        from src.infrastructure.apis.clob_client import choose_order_strategy
        strategy = choose_order_strategy(book, side, price, size_usdc)
        logger.info("Hybrid order: %s @ $%.2f type=%s",
                    strategy["strategy"], strategy["price"], strategy["order_type"])
        resp = self._clob.place_order(
            token_id=token_id, side=side,
            price=strategy["price"], size_usdc=size_usdc,
            order_type=strategy["order_type"],
        )
        return {**resp, "mode": "live", "size_usdc": size_usdc}

    def exit_position(self, pos: Any, reason: str = "") -> dict:
        slug = getattr(pos, "slug", "") or getattr(pos, "token_id", "")
        shares = getattr(pos, "shares", 0)
        logger.info("EXIT_POSITION: %s reason=%s mode=%s shares=%.2f",
                    slug[:40], reason, self.mode.value, shares)

        if self.mode in (Mode.DRY_RUN, Mode.PAPER):
            return {
                "order_id": f"sim_exit_{uuid.uuid4().hex[:8]}",
                "status": "simulated",
                "mode": self.mode.value,
                "reason": reason,
            }

        resp = self._clob.place_market_sell(token_id=pos.token_id, shares=shares)
        return {**resp, "mode": "live", "reason": reason}

    def _check_stale_price(self, token_id: str, side: str, price: float) -> dict:
        """Returns {reject: bool, result: dict, adjusted_price: float}."""
        clob_fill = self._fetch_best_price(token_id, side)
        if clob_fill is None or clob_fill <= 0 or price <= 0:
            return {"reject": False, "adjusted_price": price, "result": {}}
        drift = abs(clob_fill - price) / price
        if drift > STALE_PRICE_MAX_DRIFT:
            logger.warning("STALE_PRICE_REJECT: %s side=%s scanner=%.3f clob=%.3f drift=%.1f%%",
                           token_id[:16], side, price, clob_fill, drift * 100)
            return {
                "reject": True,
                "adjusted_price": price,
                "result": {
                    "order_id": f"rej_{uuid.uuid4().hex[:8]}",
                    "status": "error", "reason": "stale_price",
                    "mode": self.mode.value, "token_id": token_id, "side": side,
                    "scanner_price": price, "clob_price": clob_fill,
                    "drift": round(drift, 4),
                },
            }
        if abs(clob_fill - price) > 0.001:
            logger.info("CLOB fill adjust: %s %.3f → %.3f", token_id[:16], price, clob_fill)
            price = clob_fill
        return {"reject": False, "adjusted_price": price, "result": {}}

    def _simulate_order(self, token_id: str, side: str, price: float, size_usdc: float) -> dict:
        oid = f"sim_{uuid.uuid4().hex[:8]}"
        logger.info("[%s] sim %s %s @ $%.3f, size=$%.2f",
                    self.mode.value, side, token_id[:8], price, size_usdc)
        return {
            "order_id": oid, "status": "simulated",
            "mode": self.mode.value, "token_id": token_id,
            "side": side, "price": price, "size_usdc": size_usdc,
        }

    def _fetch_book(self, token_id: str) -> dict:
        try:
            resp = self._http(_CLOB_BOOK_URL, params={"token_id": token_id}, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("CLOB book fetch failed for %s: %s", token_id[:16], e)
            return {"asks": [], "bids": []}

    def _fetch_best_price(self, token_id: str, side: str) -> float | None:
        return _best_price_from_book(self._fetch_book(token_id), side)
