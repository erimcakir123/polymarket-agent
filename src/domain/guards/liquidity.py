"""Likidite kontrolleri (TDD §6.17) — pure, orderbook dict dışarıdan verilir.

ARCH Kural 1 uyumu: domain HTTP çağırmaz; orchestration CLOB'dan kitap çekip
bu domain fonksiyonlarına parametre olarak geçer.

Polymarket non-standard sort:
  asks → DESC (last = lowest = best ask)
  bids → ASC  (last = highest = best bid)
"""
from __future__ import annotations


def _best_ask(book: dict) -> float | None:
    asks = book.get("asks", [])
    if not asks:
        return None
    try:
        return float(asks[-1].get("price", 0)) or None
    except (TypeError, ValueError, KeyError):
        return None


def _best_bid(book: dict) -> float | None:
    bids = book.get("bids", [])
    if not bids:
        return None
    try:
        return float(bids[-1].get("price", 0)) or None
    except (TypeError, ValueError, KeyError):
        return None


def check_entry(
    book: dict,
    size_usdc: float,
    min_depth_usdc: float = 100.0,
    halve_threshold: float = 0.20,
) -> dict:
    """Entry likidite kontrolü. Returns: {ok, recommended_size, depth, reason}.

    - Ask derinliği < min_depth → reject
    - Emrimiz > halve_threshold × derinlik → size / 2 (slippage azalt)
    """
    if size_usdc <= 0:
        return {"ok": True, "recommended_size": size_usdc, "reason": "Nothing to buy"}

    asks = book.get("asks", [])
    if not asks:
        return {"ok": False, "recommended_size": 0.0, "reason": "No asks — market dead"}

    total_depth = 0.0
    for ask in asks:
        try:
            price = float(ask["price"])
            sz = float(ask["size"])
            total_depth += price * sz
        except (TypeError, ValueError, KeyError):
            continue

    if total_depth < max(min_depth_usdc, 1.0):
        return {
            "ok": False, "recommended_size": 0.0, "depth": total_depth,
            "reason": f"Ask depth ${total_depth:.0f} < ${min_depth_usdc:.0f}",
        }

    recommended = size_usdc
    impact_ratio = size_usdc / total_depth
    if impact_ratio > halve_threshold:
        recommended = size_usdc / 2

    return {
        "ok": True, "recommended_size": recommended,
        "depth": total_depth, "impact_ratio": impact_ratio,
    }


def check_exit(
    book: dict,
    shares_to_sell: float,
    min_fill_ratio: float = 0.80,
    floor_pct_of_best_bid: float = 0.95,
) -> dict:
    """Exit likidite kontrolü. Returns: {fillable, strategy, recommended_price, ...}.

    Strategy:
      - Tam dolum (>= 1.0) → market
      - Kısmi (>= min_fill_ratio) → limit
      - Yetersiz → split (parçalara böl, cycle'lara yay)
    """
    if shares_to_sell <= 0:
        return {"fillable": True, "strategy": "market", "reason": "Nothing to sell"}

    bids = book.get("bids", [])
    if not bids:
        return {"fillable": False, "strategy": "skip", "reason": "No bids"}

    best_bid = _best_bid(book)
    if best_bid is None or best_bid <= 0:
        return {"fillable": False, "strategy": "skip", "reason": "No valid best bid"}

    floor = best_bid * floor_pct_of_best_bid
    available = 0.0
    # Bids ASC-sorted → en yüksekten aşağı iter için reversed
    for bid in reversed(bids):
        try:
            price = float(bid["price"])
            sz = float(bid["size"])
        except (TypeError, ValueError, KeyError):
            continue
        if price < floor:
            break
        available += sz

    fill_ratio = available / shares_to_sell
    if fill_ratio >= 1.0:
        return {"fillable": True, "strategy": "market",
                "recommended_price": best_bid, "available_depth": available}
    if fill_ratio >= min_fill_ratio:
        return {"fillable": True, "strategy": "limit",
                "recommended_price": best_bid, "available_depth": available}
    return {"fillable": False, "strategy": "split",
            "recommended_price": best_bid, "available_depth": available,
            "partially_fillable": True,
            "note": f"Only {fill_ratio:.0%} fillable — split across cycles"}
