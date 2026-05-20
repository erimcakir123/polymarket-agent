"""Tennis light cycle REST price refresh — WS güvensiz olduğu için 60sn'de bir
Polymarket CLOB book'tan canlı bid/ask çeker ve açık pozisyonların current_price'ını
günceller.

Bug bağlamı (2026-05-20): WS price_feed bağlı olsa da bazı pozisyonlarda
current_price ile gerçek Polymarket mid arasında 10¢'e kadar drift gözlendi;
bitmiş maçlarda book boşaldığında bot resolution'ı görmeden RESOLVED exit
guard'ı tetiklenmiyordu. Bu modül her light cycle başında REST snapshot çekerek
WS'yi top up eder + tamamen boş book için Gamma /markets'ten `closed=true` +
outcomePrices kontrolü yapar (resolved exit tetikleyici).

Pattern:
  - exit_processor.run_light ÖNCESİ çağrılır (tennis_agent.run_light_cycle)
  - HTTP hatası asla cycle'ı çökertmez (her token bağımsız try/except)
  - Yeni config key yok (timeout sabitler modül-üstü)
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import requests

from src.domain.portfolio.manager import PortfolioManager

logger = logging.getLogger(__name__)

CLOB_REST_BOOK_URL = "https://clob.polymarket.com/book"
GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
REST_TIMEOUT_SEC = 5.0


HttpGet = Callable[..., Any]


def _default_http_get(url: str, params: dict | None = None, timeout: float = REST_TIMEOUT_SEC) -> Any:
    return requests.get(url, params=params or {}, timeout=timeout)


def _best_ask(asks: list) -> float:
    """Best ask = LOWEST price. Polymarket sort-agnostic defansif min()."""
    prices = []
    for a in asks or []:
        try:
            p = float(a.get("price", 0))
            if p > 0:
                prices.append(p)
        except (TypeError, ValueError, KeyError):
            continue
    return min(prices) if prices else 0.0


def _best_bid(bids: list) -> float:
    """Best bid = HIGHEST price. Defansif max()."""
    prices = []
    for b in bids or []:
        try:
            p = float(b.get("price", 0))
            if p > 0:
                prices.append(p)
        except (TypeError, ValueError, KeyError):
            continue
    return max(prices) if prices else 0.0


def _fetch_book(token_id: str, http_get: HttpGet) -> tuple[float, float] | None:
    """REST /book?token_id=... → (best_bid, best_ask). None = HTTP/parse hatası.

    (0.0, 0.0) → book tamamen boş (resolved/delisted sinyali — caller Gamma kontrolüne döner).
    """
    try:
        resp = http_get(CLOB_REST_BOOK_URL, params={"token_id": token_id}, timeout=REST_TIMEOUT_SEC)
        if resp.status_code != 200:
            logger.warning("REST /book %s returned %d", token_id[:16], resp.status_code)
            return None
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("REST /book %s failed: %s", token_id[:16], exc)
        return None
    return _best_bid(data.get("bids", []) or []), _best_ask(data.get("asks", []) or [])


def _resolved_yes_price(condition_id: str, http_get: HttpGet) -> float | None:
    """Gamma /markets?condition_ids=X → closed=True ise YES çözüm fiyatı (0.0 veya 1.0).

    None = market kapalı değil / response parse edilemedi (caller current_price'a dokunmaz).
    """
    try:
        resp = http_get(GAMMA_MARKETS_URL, params={"condition_ids": condition_id}, timeout=REST_TIMEOUT_SEC)
        if resp.status_code != 200:
            logger.warning("Gamma /markets %s returned %d", condition_id[:10], resp.status_code)
            return None
        items = resp.json() or []
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Gamma /markets %s failed: %s", condition_id[:10], exc)
        return None
    if not isinstance(items, list) or not items:
        return None
    market = items[0]
    if not bool(market.get("closed", False)):
        return None
    # outcomePrices JSON string olarak gelir: '["1", "0"]' veya '["0", "1"]'
    raw = market.get("outcomePrices")
    if isinstance(raw, str):
        try:
            import json
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if not isinstance(raw, list) or not raw:
        return None
    try:
        return float(raw[0])  # YES outcome = ilk eleman
    except (TypeError, ValueError):
        return None


def refresh_open_positions(
    portfolio: PortfolioManager,
    http_get: HttpGet | None = None,
) -> tuple[int, int]:
    """Tüm açık pozisyonlar için REST book çek + current_price/bid_price güncelle.

    Book hem bid hem ask içeriyorsa mid = (bid + ask) / 2 → current_price'a yazılır.
    Book tamamen boşsa Gamma /markets kontrolü: closed=True ise outcomePrices[0]
    (YES çözüm fiyatı, 0.0 veya 1.0) current_price'a yazılır → RESOLVED exit
    guard'ı bir sonraki tick'te tetiklenir.

    Returns:
        (refreshed_count, resolved_count): kaç pozisyonun fiyatı güncellendi,
        kaçı resolved olarak işaretlendi.
    """
    get = http_get or _default_http_get
    refreshed = 0
    resolved = 0
    for pos in list(portfolio.positions.values()):
        if not pos.token_id:
            continue
        book = _fetch_book(pos.token_id, get)
        if book is None:
            continue
        bid, ask = book
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2.0
            pos.current_price = mid
            pos.bid_price = bid
            refreshed += 1
            continue
        if bid == 0.0 and ask == 0.0:
            # Book tamamen boş → market resolved/delisted olabilir.
            yes_price = _resolved_yes_price(pos.condition_id, get)
            if yes_price is not None:
                # outcomePrices direction-agnostic — Position.effective_price kararı
                # direction'a göre verir. Sadece YES referansını yazıyoruz (ARCH Kural 7).
                pos.current_price = yes_price
                resolved += 1
    return refreshed, resolved
