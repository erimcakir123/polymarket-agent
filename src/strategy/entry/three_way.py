"""3-way entry strategy — Soccer/Rugby/AFL/Handball (SPEC-015, SPEC-017).

Bookmaker'ın 3 outcome arasında en yüksek olasılığa sahip outcome'u (favori) seçer.
Filter:
  - Absolute threshold: favorite_prob >= favorite_threshold (default 0.40)
  - Relative margin: favorite - second_highest >= favorite_margin (default 0.07)
  - Price cap: favorite market yes_price <= max_entry_price (pahalı outlier)

Edge hesabı YOK (SPEC-017). Direction: BUY_YES on favorite outcome's own market.
Tie-break: eşit olasılıklar → None (skip).
"""
from __future__ import annotations

import logging

from src.domain.analysis.probability import BookmakerProbability

logger = logging.getLogger(__name__)
from src.models.enums import Direction, EntryReason
from src.models.market import MarketData
from src.models.signal import Signal


def _select_favorite(probs: dict[str, BookmakerProbability]) -> tuple[str, float] | None:
    """En yüksek bookmaker_prob outcome'u. Eşitlik → None (tie-break)."""
    if not probs:
        return None
    sorted_outcomes = sorted(probs.items(), key=lambda kv: -kv[1].probability)
    top_outcome, top_prob_obj = sorted_outcomes[0]
    if len(sorted_outcomes) > 1:
        second_prob_obj = sorted_outcomes[1][1]
        if abs(top_prob_obj.probability - second_prob_obj.probability) < 1e-9:
            return None
    return top_outcome, top_prob_obj.probability


def _passes_favorite_filter(
    probs: dict[str, BookmakerProbability],
    favorite_outcome: str,
    threshold: float,
    margin: float,
) -> bool:
    """Absolute >= threshold AND margin to second highest >= margin."""
    fav_prob = probs[favorite_outcome].probability
    if fav_prob < threshold:
        return False
    others = [p.probability for k, p in probs.items() if k != favorite_outcome]
    second_highest = max(others) if others else 0.0
    return (fav_prob - second_highest) >= margin


def evaluate(
    home_market: MarketData | None,
    draw_market: MarketData | None,
    away_market: MarketData | None,
    probs: dict[str, BookmakerProbability],
    favorite_threshold: float = 0.40,
    favorite_margin: float = 0.07,
    max_entry_price: float = 0.85,
) -> Signal | None:
    """3-way entry kararı. None → koşul sağlanmadı."""
    if any(p.confidence == "C" for p in probs.values()):
        logger.info("[three-way] SKIP reason=c_conf_in_probs")
        return None

    selection = _select_favorite(probs)
    if selection is None:
        logger.info(
            "[three-way] SKIP reason=tie_break probs=%s",
            {k: round(v.probability, 3) for k, v in probs.items()},
        )
        return None
    fav_outcome, fav_prob = selection

    if not _passes_favorite_filter(probs, fav_outcome, favorite_threshold, favorite_margin):
        others = [p.probability for k, p in probs.items() if k != fav_outcome]
        second = max(others) if others else 0.0
        margin = fav_prob - second
        reason = "below_threshold" if fav_prob < favorite_threshold else "margin_too_low"
        logger.info(
            "[three-way] SKIP reason=%s fav=%s prob=%.3f threshold=%.3f margin=%.3f min_margin=%.3f",
            reason, fav_outcome, fav_prob, favorite_threshold, margin, favorite_margin,
        )
        return None

    fav_market_map: dict[str, MarketData | None] = {
        "home": home_market,
        "draw": draw_market,
        "away": away_market,
    }
    fav_market = fav_market_map.get(fav_outcome)
    if fav_market is None:
        logger.info("[three-way] SKIP reason=missing_market fav=%s", fav_outcome)
        return None

    market_yes = fav_market.yes_price
    if market_yes > max_entry_price:
        logger.info(
            "[three-way] SKIP reason=price_out_of_range fav=%s yes=%.3f max=%.2f",
            fav_outcome, market_yes, max_entry_price,
        )
        return None

    fav_prob_obj = probs[fav_outcome]
    logger.info(
        "[three-way] ENTER event_id=%s fav=%s probs=%s fav_prob=%.3f yes=%.3f margin=%.3f confidence=%s",
        fav_market.event_id or "",
        fav_outcome,
        {k: round(v.probability, 3) for k, v in probs.items()},
        fav_prob,
        market_yes,
        fav_prob - max(p.probability for k, p in probs.items() if k != fav_outcome),
        fav_prob_obj.confidence,
    )
    return Signal(
        condition_id=fav_market.condition_id,
        direction=Direction.BUY_YES,
        anchor_probability=fav_prob,
        market_price=market_yes,
        confidence=fav_prob_obj.confidence,
        size_usdc=0.0,
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=fav_prob,
        num_bookmakers=fav_prob_obj.num_bookmakers,
        has_sharp=fav_prob_obj.has_sharp,
        sport_tag=fav_market.sport_tag,
        event_id=fav_market.event_id or "",
    )
