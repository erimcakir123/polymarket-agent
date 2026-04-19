"""Early entry — maç başlamadan ≥6 saat önce yüksek edge fırsatı (TDD §9 `early`).

Bookmaker line'ları Polymarket'ten önce hareket eder; bot bu pencereyi yakalar.
Sıkı eşikler: yüksek min_edge (%10), favorite filter (≥0.52 our side), B+ confidence,
ve max entry price (≤0.70 — kısa shot için yer bırak).

Time window:
  match_start ∈ [now + min_hours_to_start, now + max_hours_to_start]
  (default: 6h-24h = 6 ila 24 saat arası; amaç fırsatı oturmadan yakalamak)
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.domain.analysis.edge import calculate_edge
from src.domain.analysis.probability import BookmakerProbability
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


def evaluate(
    market: MarketData,
    bm_prob: BookmakerProbability,
    min_edge: float = 0.10,
    min_favorite_probability: float = 0.52,
    min_confidence: str = "B",
    max_entry_price: float = 0.70,
    min_hours_to_start: float = 6.0,
    max_hours_to_start: float = 24.0,
    confidence_multipliers: dict[str, float] | None = None,
) -> Signal | None:
    """Early entry kararı. None döner: koşullar uymuyor."""
    # 1. Confidence eşiği (default B+; v2'de B veya A kabul)
    if not _confidence_meets(bm_prob.confidence, min_confidence):
        return None

    # 2. Market entry price eşiği
    if market.yes_price > max_entry_price:
        return None

    # 3. Time window — match_start gerekli
    if not _within_time_window(market, min_hours_to_start, max_hours_to_start):
        return None

    # 4. Edge hesabı (yüksek eşik 0.10)
    direction, edge = calculate_edge(
        anchor_prob=bm_prob.probability,
        market_yes_price=market.yes_price,
        min_edge=min_edge,
        confidence=bm_prob.confidence,
        confidence_multipliers=confidence_multipliers,
    )
    if direction == Direction.SKIP:
        return None

    # 5. Favorite filter (SPEC-013) — our side bookmaker prob >= threshold
    our_side_prob = bm_prob.probability if direction == Direction.BUY_YES else (1.0 - bm_prob.probability)
    if our_side_prob < min_favorite_probability:
        return None

    return Signal(
        condition_id=market.condition_id,
        direction=direction,
        anchor_probability=bm_prob.probability,
        market_price=market.yes_price,
        edge=edge,
        confidence=bm_prob.confidence,
        size_usdc=0.0,
        entry_reason=EntryReason.EARLY,
        bookmaker_prob=bm_prob.bookmaker_prob,
        num_bookmakers=bm_prob.num_bookmakers,
        has_sharp=bm_prob.has_sharp,
        sport_tag=market.sport_tag,
        event_id=market.event_id or "",
    )


def _confidence_meets(actual: str, minimum: str) -> bool:
    """A > B > C sıralaması (ordinal). minimum'u karşılıyor mu?"""
    order = {"C": 0, "B": 1, "A": 2}
    return order.get(actual, -1) >= order.get(minimum, 0)


def _within_time_window(market: MarketData, min_h: float, max_h: float) -> bool:
    """match_start gelecekte ve [min_h, max_h] aralığında mı?"""
    if not market.match_start_iso:
        return False
    try:
        start = datetime.fromisoformat(market.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    hours = (start - datetime.now(timezone.utc)).total_seconds() / 3600.0
    return min_h <= hours <= max_h
