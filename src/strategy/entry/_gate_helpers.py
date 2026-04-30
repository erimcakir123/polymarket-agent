"""Gate helper functions — extracted from gate.py to comply with 400-line ARCH limit.

Pure functions; no I/O. Imported back into gate.py for use.
"""
from __future__ import annotations

from src.models.enums import Direction


def _classify_confidence(has_sharp: bool, bm_weight: float) -> str:
    """Bookmaker kalitesine göre A/B/C tier."""
    if bm_weight < 5.0:
        return "C"
    return "A" if has_sharp else "B"


def _gap_multiplier(gap: float, cfg: object) -> float:
    """Gap büyüklüğüne göre stake çarpanı."""
    if gap >= cfg.gap_extreme_zone:
        return cfg.extreme_gap_multiplier
    if gap >= cfg.gap_high_zone:
        return cfg.high_gap_multiplier
    return 1.0


def _passes_filters(
    gap: float,
    polymarket_price: float,
    bookmaker_prob: float,
    volume: float,
    cfg: object,
    market_type: str = "moneyline",
    spread_line: float | None = None,
    total_line: float | None = None,
    gap_threshold_adj: float = 0.0,
    sport_tag: str = "",
) -> str | None:
    """Tüm filtrelerden geç. None = geçti, string = skip sebebi."""
    effective_gap_threshold = max(0.0, cfg.min_gap_threshold + gap_threshold_adj)
    if market_type == "spreads" and spread_line is not None and spread_line >= cfg.spread_large_threshold:
        effective_gap_threshold += cfg.spread_gap_bonus

    if gap < effective_gap_threshold:
        return "GAP_TOO_LOW"

    sport_low = (sport_tag or "").lower()
    is_nhl_puck_line = (
        market_type == "spreads"
        and sport_low in ("nhl", "ahl", "icehockey_nhl")
    )
    is_nhl_totals = (
        market_type == "totals"
        and sport_low in ("nhl", "ahl", "icehockey_nhl")
    )

    if market_type == "spreads":
        if is_nhl_puck_line:
            if polymarket_price < cfg.nhl_puck_line_min_price or polymarket_price > cfg.nhl_puck_line_max_price:
                return "PRICE_OUT_OF_RANGE"
            if volume < cfg.nhl_puck_line_min_volume:
                return "VOLUME_TOO_LOW"
        else:
            if polymarket_price < cfg.spread_min_price or polymarket_price > cfg.spread_max_price:
                return "PRICE_OUT_OF_RANGE"
    elif market_type == "totals":
        if is_nhl_totals:
            if polymarket_price < cfg.nhl_totals_min_price or polymarket_price > cfg.nhl_totals_max_price:
                return "PRICE_OUT_OF_RANGE"
            if total_line is not None and total_line < cfg.nhl_totals_min_target_total:
                return "TOTAL_TOO_LOW"
            if volume < cfg.nhl_totals_min_volume:
                return "VOLUME_TOO_LOW"
        else:
            if polymarket_price < cfg.totals_min_price or polymarket_price > cfg.totals_max_price:
                return "PRICE_OUT_OF_RANGE"
            if total_line is not None and total_line < cfg.totals_min_target_total:
                return "TOTAL_TOO_LOW"
    else:  # moneyline
        if polymarket_price < cfg.min_polymarket_price or polymarket_price > cfg.max_entry_price:
            return "PRICE_OUT_OF_RANGE"

    if bookmaker_prob < cfg.min_favorite_probability:
        return "BOOKMAKER_PROB_TOO_LOW"
    # NHL puck line / totals volume already checked above; skip generic for those paths.
    if not (is_nhl_puck_line or is_nhl_totals):
        if volume < cfg.min_market_volume:
            return "VOLUME_TOO_LOW"
    return None


def _compute_stake(
    bankroll: float,
    confidence: str,
    gap: float,
    win_prob: float,
    cfg: object,
) -> float:
    """stake = bankroll × confidence_pct × gap_mult × win_prob, hard cap."""
    base_pct = cfg.confidence_a_pct if confidence == "A" else cfg.confidence_b_pct
    mult = _gap_multiplier(gap, cfg)
    raw = bankroll * base_pct * mult * win_prob
    cap = bankroll * cfg.max_bet_pct
    return min(raw, cap, cfg.max_single_bet_usdc)


def _check_event_guard(
    event_id: str | None,
    market_type: str,
    direction: Direction,
    positions: dict,
    max_per_event: int = 3,
) -> str | None:
    """Event-level pozisyon guard. None = geçti.

    Block: aynı market_type + aynı event (line varyantları, Over+Under).
    Block: ML + Spread aynı yön (yüksek korelasyon).
    Allow: ML + Spread (zit yön) + Totals → full slate (üç farklı edge).
    Cap: max 3 pozisyon/event (worst case bankroll %18.75 risk; daily
    circuit_breaker %8 tetiklenirse bot ertesi gün durur).
    """
    if not event_id:
        return None
    same_event = [p for p in positions.values() if p.event_id == event_id]
    if len(same_event) >= max_per_event:
        return "EVENT_GUARD_MAX_POSITIONS"
    norm_type = market_type or "moneyline"
    for pos in same_event:
        pos_type = pos.sports_market_type or "moneyline"
        if pos_type == norm_type:
            return "EVENT_GUARD_SAME_MARKET_TYPE"
        ml_spread = frozenset({"moneyline", "spreads"})
        if frozenset({pos_type, norm_type}) == ml_spread and pos.direction == direction:
            return "EVENT_GUARD_ML_SPREAD_CORRELATED"
    return None
