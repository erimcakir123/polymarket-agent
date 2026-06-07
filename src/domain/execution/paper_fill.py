"""Paper fill walker — pure domain function, no I/O.

Walks orderbook levels under slippage tolerance, returns FillResult.
Caller (paper_executor) handles I/O (fetching the book, persisting state).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FillStatus(str, Enum):
    FILLED = "filled"
    PARTIAL_FILL = "partial_fill"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FillResult:
    status: FillStatus
    filled_shares: float
    filled_size_usdc: float
    weighted_avg_price: float
    reason: str


def _level_price_size(level: dict) -> tuple[float, float]:
    try:
        return float(level.get("price", 0)), float(level.get("size", 0))
    except (TypeError, ValueError):
        return 0.0, 0.0


def walk_buy(
    asks: list[dict],
    target_price: float,
    target_size_usdc: float,
    max_slippage_pct: float,
    min_fill_ratio: float,
) -> FillResult:
    """Walk asks ascending, accumulate fill while price <= target * (1 + slippage).

    REJECTED if filled_usdc < target * min_fill_ratio.
    """
    if not asks or target_size_usdc <= 0:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "empty_book")

    max_acceptable = target_price * (1.0 + max_slippage_pct)
    filled_shares = 0.0
    filled_usdc = 0.0

    # Polymarket asks DESC-sorted; best ask = asks[-1]. Walk ascending price.
    for level in reversed(asks):
        price, size = _level_price_size(level)
        if price <= 0 or size <= 0:
            continue
        if price > max_acceptable:
            break
        level_usdc_available = price * size
        remaining_usdc = target_size_usdc - filled_usdc
        if remaining_usdc <= 0:
            break
        take_usdc = min(level_usdc_available, remaining_usdc)
        take_shares = take_usdc / price
        filled_shares += take_shares
        filled_usdc += take_usdc
        if filled_usdc >= target_size_usdc:
            break

    if filled_usdc < target_size_usdc * min_fill_ratio:
        return FillResult(
            FillStatus.REJECTED, 0.0, 0.0, 0.0,
            f"below_min_fill_or_slippage (filled=${filled_usdc:.2f}/${target_size_usdc:.2f})",
        )

    wap = filled_usdc / filled_shares if filled_shares > 0 else 0.0
    return FillResult(FillStatus.FILLED, filled_shares, filled_usdc, wap, "")


def walk_sell(
    bids: list[dict],
    target_price: float,
    shares: float,
    max_slippage_pct: float,
    market: bool = False,
) -> FillResult:
    """Walk bids descending, accumulate fill while price >= target * (1 - slippage).

    market=True → kayma tabanı yok (gerçek piyasa emri): tüm gerçek bid
    derinliği yürünür. Yalnız her seviyedeki gerçek `size` kadar doldurulur
    (hayalet icat yok). Returns FILLED / PARTIAL_FILL / REJECTED.
    Zero shares input → FILLED with 0 (degenerate).
    """
    if shares <= 0:
        return FillResult(FillStatus.FILLED, 0.0, 0.0, 0.0, "")
    if not bids:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "empty_book")

    min_acceptable = 0.0 if market else target_price * (1.0 - max_slippage_pct)
    filled_shares = 0.0
    filled_usdc = 0.0

    # Polymarket bids ASC-sorted; best bid = bids[-1]. Walk descending price.
    for level in reversed(bids):
        price, size = _level_price_size(level)
        if price <= 0 or size <= 0:
            continue
        if price < min_acceptable:
            break
        remaining_shares = shares - filled_shares
        if remaining_shares <= 0:
            break
        take_shares = min(size, remaining_shares)
        filled_shares += take_shares
        filled_usdc += take_shares * price
        if filled_shares >= shares:
            break

    if filled_shares <= 0:
        return FillResult(FillStatus.REJECTED, 0.0, 0.0, 0.0, "no_bids_above_slippage")
    wap = filled_usdc / filled_shares
    status = FillStatus.FILLED if abs(filled_shares - shares) < 1e-9 else FillStatus.PARTIAL_FILL
    return FillResult(status, filled_shares, filled_usdc, wap, "" if status == FillStatus.FILLED else "partial")
