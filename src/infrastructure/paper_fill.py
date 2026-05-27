"""Order book walker — PAPER mode için gerçekçi fill simülasyonu.

Polymarket CLOB book formatı (NON-STANDARD sort):
  asks: list of {price, size} DESC by price (best ask = -1)
  bids: list of {price, size} DESC by price (best bid = 0... wait)
  Aslında deneme: API bids ASC döner ama best="closer to mid" testte
  iki yönü de tutmamız lazım. Bu modülde defansif: hem ASC hem DESC için
  walk doğru çalışsın diye **sort'u biz yapıyoruz**.

ARCH_GUARD Kural 3 — executor.py 400 satır altı tutmak için ayrı modül.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FillResult:
    """Bir order book walk'ının sonucu."""
    status: Literal["FILLED", "PARTIAL_FILL", "REJECTED"]
    filled_shares: float
    avg_price: float
    reason: str = ""


def _parse_levels(raw_levels: list, side: Literal["ask", "bid"]) -> list[tuple[float, float]]:
    """Book level'larını (price, size) tuple listesine çevir + side için doğru sırala.

    Walk için: ask side ASCENDING (en ucuzdan başla), bid side DESCENDING (en pahalıdan).
    """
    out: list[tuple[float, float]] = []
    for lv in raw_levels or []:
        try:
            p = float(lv.get("price", 0))
            s = float(lv.get("size", 0))
            if p > 0 and s > 0:
                out.append((p, s))
        except (TypeError, ValueError, AttributeError):
            continue
    out.sort(key=lambda x: x[0], reverse=(side == "bid"))
    return out


def walk_book_buy(
    asks: list,
    target_price: float,
    size_usdc: float,
    max_slippage_pct: float,
    min_fill_ratio: float,
) -> FillResult:
    """BUY: ask side'da target_price'tan +%slip'e kadar yürü, share doldur.

    Args:
        asks: book["asks"] raw
        target_price: bot'un girmek istediği fiyat
        size_usdc: harcamak istediği USDC
        max_slippage_pct: max kabul edilebilir fiyat yukarı sapması (örn. 0.02 = %2)
        min_fill_ratio: en az bu oran dolarsa kabul (örn. 0.95)

    Returns:
        FILLED: tam istediği shares dolduruldu
        PARTIAL_FILL: kısmen dolduruldu ama min_fill_ratio üstünde
        REJECTED: dolma min_fill_ratio altında veya hiç doldurulamadı
    """
    if target_price <= 0 or size_usdc <= 0:
        return FillResult("REJECTED", 0, 0, reason="invalid input")

    max_acceptable_price = target_price * (1 + max_slippage_pct)
    shares_wanted = size_usdc / target_price

    levels = _parse_levels(asks, "ask")
    filled = 0.0
    cost = 0.0
    for price, available in levels:
        if price > max_acceptable_price:
            break
        take = min(available, shares_wanted - filled)
        if take <= 0:
            break
        cost += take * price
        filled += take
        if filled >= shares_wanted:
            break

    if filled <= 0:
        return FillResult("REJECTED", 0, 0, reason="no asks within slippage")

    avg = cost / filled
    if filled < shares_wanted * min_fill_ratio:
        return FillResult("REJECTED", round(filled, 4), round(avg, 4),
                          reason=f"insufficient_depth (filled {filled:.2f}/{shares_wanted:.2f})")
    if filled < shares_wanted:
        return FillResult("PARTIAL_FILL", round(filled, 4), round(avg, 4))
    return FillResult("FILLED", round(filled, 4), round(avg, 4))


def walk_book_sell(
    bids: list,
    target_price: float,
    shares: float,
    max_slippage_pct: float,
) -> FillResult:
    """SELL: bid side'da target_price'tan -%slip'e kadar yürü, share sat.

    Args:
        bids: book["bids"] raw
        target_price: bot'un satmak istediği fiyat (genelde current_price)
        shares: satılacak pay sayısı
        max_slippage_pct: max kabul edilebilir fiyat aşağı sapması (örn. 0.05 = %5)

    Returns:
        FILLED: tüm shares satıldı
        PARTIAL_FILL: kısmen satıldı (kalan pozisyonda)
        REJECTED: 0 dolma (no buyers at acceptable price)
    """
    if target_price <= 0 or shares <= 0:
        return FillResult("REJECTED", 0, 0, reason="invalid input")

    min_acceptable_price = target_price * (1 - max_slippage_pct)

    levels = _parse_levels(bids, "bid")
    filled = 0.0
    revenue = 0.0
    for price, available in levels:
        if price < min_acceptable_price:
            break
        take = min(available, shares - filled)
        if take <= 0:
            break
        revenue += take * price
        filled += take
        if filled >= shares:
            break

    if filled <= 0:
        return FillResult("REJECTED", 0, 0, reason="no bids within slippage")
    avg = revenue / filled
    if filled < shares:
        return FillResult("PARTIAL_FILL", round(filled, 4), round(avg, 4))
    return FillResult("FILLED", round(filled, 4), round(avg, 4))
