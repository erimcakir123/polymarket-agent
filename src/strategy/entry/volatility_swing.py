"""Volatility swing — düşük fiyatlı underdog scalp (TDD §9 `volatility_swing`).

Mantık: maç başlamadan önceki saatlerde fiyatı düşük (~10-50¢) underdog'lar
maçın ilk dakikalarında volatil sıçramalar yapar. Bot bunu yakalar:
  - Kısa SL (%20)
  - Sıkı TP (%60)
  - Pozisyon kendi market'inde işaretlenir (volatility_swing=True)
  - Stop-loss, scale-out, A-conf gibi kurallar bypass — kendi exit kuralı

Eşikler:
  - market_price ∈ [min_token_price, max_token_price] (default 0.10-0.50)
  - max_hours_to_start (24h)
  - max_concurrent (5 pozisyon)

Bu strateji **edge bağımsız** — bookmaker probability'sine bakmaz, sadece
market price + zamanlama. Underdog'un patlama olasılığını sayısal değil,
volatilite gözlemiyle istismar eder.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


def evaluate(
    market: MarketData,
    bm_prob_for_logging=None,
    min_token_price: float = 0.10,
    max_token_price: float = 0.50,
    max_hours_to_start: float = 24.0,
) -> Signal | None:
    """Volatility swing kararı. None: koşullar uymuyor.

    bm_prob_for_logging: opsiyonel, sadece TradeRecord metadata için.
    """
    # 1. Fiyat aralığı (underdog seviyesi)
    if not (min_token_price <= market.yes_price <= max_token_price):
        # YES taraftan değil — NO tarafı kontrol et (NO ucuzsa BUY_NO yap)
        if not (min_token_price <= market.no_price <= max_token_price):
            return None
        direction = Direction.BUY_NO
        market_price = market.no_price
    else:
        direction = Direction.BUY_YES
        market_price = market.yes_price

    # 2. Zaman penceresi: maç başlamamış AND ≤ max_hours_to_start
    if not _pre_match_within_window(market, max_hours_to_start):
        return None

    # Anchor probability — bookmaker varsa kullan, yoksa market price
    has_bm = bm_prob_for_logging is not None
    anchor = bm_prob_for_logging.probability if has_bm else market.yes_price
    bm_prob = bm_prob_for_logging.bookmaker_prob if has_bm else 0.0
    confidence = bm_prob_for_logging.confidence if has_bm else "B"
    num_bookmakers = bm_prob_for_logging.num_bookmakers if has_bm else 0.0
    has_sharp = bm_prob_for_logging.has_sharp if has_bm else False

    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=max(0.01, min(0.99, anchor)),
        market_price=market_price,
        edge=0.0,  # VS edge bağımsız — patlama beklentisi
        confidence=confidence,
        size_usdc=0.0,  # Gate sizing
        entry_reason=EntryReason.VOLATILITY_SWING,
        bookmaker_prob=bm_prob,
        num_bookmakers=num_bookmakers,
        has_sharp=has_sharp,
        sport_tag=market.sport_tag,
        event_id=market.event_id or "",
    )


def _pre_match_within_window(market: MarketData, max_hours: float) -> bool:
    """match_start gelecekte ve ≤ max_hours içinde mi?"""
    if not market.match_start_iso:
        return False
    try:
        start = datetime.fromisoformat(market.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    delta = (start - datetime.now(timezone.utc)).total_seconds() / 3600.0
    return 0 < delta <= max_hours
