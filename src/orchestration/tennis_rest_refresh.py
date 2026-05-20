"""Tennis light cycle REST price refresh — WS güvensiz olduğu için 60sn'de bir
Polymarket'tan canlı fiyat çeker ve açık pozisyonların current_price'ını günceller.

Bug bağlamı (2026-05-20): WS price_feed bağlı olsa da bazı pozisyonlarda
current_price ile gerçek Polymarket mid arasında 10¢'e kadar drift gözlendi;
bitmiş maçlarda book one-sided/boş olduğunda bot resolution'ı görmüyordu.
Bu modül her light cycle başında tek tek pozisyonları "ne pahasına olursa olsun
güncel bir fiyat" garantisiyle tazeler.

PRIORITY ORDER (her pozisyon, her cycle):
  1. Gamma /markets metadata — outcomePrices[0] EXTREME (<0.03 veya >0.97) ise
     resolved say, fiyatı outcomePrices[0]'a yaz. `closed` bayrağı BEKLENMEZ:
     Polymarket outcomePrices'i kapatmadan önce yapıştırır, bu bilgi "gospel".
  2. CLOB /book mid/best — bid+ask varsa mid; sadece ask → ask (cautious upper);
     sadece bid → bid (cautious lower); ikisi de yoksa price'a dokunma.
     `bid_price` HER ZAMAN best_bid'le yazılır (mid'e düşse bile).
  3. Hiçbir kaynak fiyat veremezse `current_price` korunur, WARN log basılır,
     `stale_count` artar.

Cycle log: "REST refresh: refreshed=X resolved=Y stale=Z" — caller değil bu
modül yazar, böylece tek-doğruluk-kaynağı log formatı korunur.

Pattern:
  - exit_processor.run_light ÖNCESİ çağrılır (tennis_agent.run_light_cycle)
  - HTTP hatası asla cycle'ı çökertmez (her token bağımsız try/except)
  - Yeni config key yok (timeout + extreme threshold modül-üstü)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

import requests

from src.domain.portfolio.manager import PortfolioManager

logger = logging.getLogger(__name__)

CLOB_REST_BOOK_URL = "https://clob.polymarket.com/book"
GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
REST_TIMEOUT_SEC = 5.0

# resolved.py ile aynı eşikler — Polymarket settled market doğal yapışma noktası.
EXTREME_LOW = 0.03
EXTREME_HIGH = 0.97


HttpGet = Callable[..., Any]


@dataclass
class RefreshStats:
    """Cycle-level özet — caller test/log için kullanır."""
    refreshed: int = 0   # Fiyat CLOB book'tan güncellendi (mid/ask/bid)
    resolved: int = 0    # Fiyat Gamma extreme outcomePrices'ten güncellendi
    stale: int = 0       # Hiçbir kaynak fiyat veremedi → current_price korundu


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

    (0.0, 0.0) → book tamamen boş; tek taraflılar (bid=0, ask>0) veya tersi
    de döndürülür — caller karar verir.
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


def _gamma_outcome_yes(condition_id: str, http_get: HttpGet) -> float | None:
    """Gamma /markets?condition_ids=X → outcomePrices[0] (YES outcome).

    `closed` bayrağına BAKMAZ — Polymarket extreme outcomePrices'i kapatmadan
    önce yapıştırır; o değer "gospel" (RESOLVED exit tetikleyici).
    None = response yok/parse hatası (caller current_price'a dokunmaz).
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
    raw = market.get("outcomePrices")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if not isinstance(raw, list) or not raw:
        return None
    try:
        return float(raw[0])  # YES outcome = ilk eleman
    except (TypeError, ValueError):
        return None


def _is_extreme(yes_price: float) -> bool:
    """Resolved-band kontrolü — resolved.py ile aynı 3¢/97¢ marjı."""
    return yes_price <= EXTREME_LOW or yes_price >= EXTREME_HIGH


def _refresh_one_position(pos, http_get: HttpGet, stats: RefreshStats) -> None:
    """Tek pozisyon için priority ladder. State mutation in-place."""
    if not pos.token_id:
        return

    # PRIORITY 1: Gamma extreme → RESOLVED. closed bayrağı beklenmez.
    yes_price = _gamma_outcome_yes(pos.condition_id, http_get)
    if yes_price is not None and _is_extreme(yes_price):
        pos.current_price = yes_price
        stats.resolved += 1
        return

    # PRIORITY 2: CLOB book — mid / one-sided ask / one-sided bid.
    book = _fetch_book(pos.token_id, http_get)
    if book is None:
        # Gamma normal range döndürdü ama CLOB hata verdi — mevcut fiyatı koru.
        logger.warning(
            "REST refresh stale: %s — Gamma yes=%s, CLOB book unavailable",
            pos.slug[:35] if pos.slug else pos.condition_id[:16],
            f"{yes_price:.3f}" if yes_price is not None else "n/a",
        )
        stats.stale += 1
        return

    bid, ask = book
    # bid_price HER ZAMAN güncellenir (defansif: 0.0 → 0.0 ama tutarlı).
    if bid > 0:
        pos.bid_price = bid
    if bid > 0 and ask > 0:
        pos.current_price = (bid + ask) / 2.0
        stats.refreshed += 1
        return
    if ask > 0:
        # Cautious upper-bound: tek taraflı ask. SL/scale-out optimist yorum
        # yapmaz, fiyat ask'a yapıştığı için drift sınırlı.
        pos.current_price = ask
        stats.refreshed += 1
        return
    if bid > 0:
        pos.current_price = bid  # Cautious lower-bound.
        stats.refreshed += 1
        return

    # Book tamamen boş, Gamma extreme değil → stale say. PRIORITY 1 zaten
    # Gamma'yı denedi; tekrar denemeye gerek yok.
    logger.warning(
        "REST refresh stale: %s — empty book + Gamma not extreme (yes=%s)",
        pos.slug[:35] if pos.slug else pos.condition_id[:16],
        f"{yes_price:.3f}" if yes_price is not None else "n/a",
    )
    stats.stale += 1


def refresh_open_positions(
    portfolio: PortfolioManager,
    http_get: HttpGet | None = None,
) -> tuple[int, int]:
    """Tüm açık pozisyonlar için "her ne pahasına olursa olsun güncel fiyat"
    priority ladder'ı uygula. Detay için modül docstring'i.

    Returns:
        (refreshed_count, resolved_count) — geriye uyumlu API. `stale_count`
        log'a yazılır ama caller hesabına girmez (test/diag için stats yapısı
        kullanılır, ama public return iki sayı olarak kalır).
    """
    get = http_get or _default_http_get
    stats = RefreshStats()
    for pos in list(portfolio.positions.values()):
        _refresh_one_position(pos, get, stats)
    logger.info(
        "REST refresh: refreshed=%d resolved=%d stale=%d",
        stats.refreshed, stats.resolved, stats.stale,
    )
    return stats.refreshed, stats.resolved
