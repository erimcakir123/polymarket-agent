"""Gate helper functions — extracted from gate.py to comply with 400-line ARCH limit.

Pure functions; no I/O. Imported back into gate.py for use.
"""
from __future__ import annotations

import logging

from src.models.enums import Direction, EntryReason
from src.models.signal import Signal

logger = logging.getLogger(__name__)


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


def _evaluate_mlb(
    cid: str,
    market: object,
    mlb_edge_enricher: object | None,
    gate_cfg: object,
    bankroll: float,
) -> tuple[Signal | None, str | None]:
    """MLB evaluation logic extracted for ARCH line-limit compliance.

    Returns (signal, skip_reason). Exactly one will be non-None.
    Pure coordination; no I/O beyond delegating to enricher + filter chain.
    """
    from datetime import datetime  # stdlib — not I/O
    from types import SimpleNamespace

    from src.domain.sports.mlb_question_parser import parse_mlb_question
    from src.strategy.entry._mlb_edge import MLBEntryConfig, apply_mlb_entry_filters

    # 1. Parse question → intent
    intent = parse_mlb_question(
        getattr(market, "question", None),
        outcome=getattr(market, "outcome", None),
    )
    if intent is None:
        return None, "MLB_QUESTION_PARSE_FAIL"

    # 2. Enricher required
    if mlb_edge_enricher is None:
        return None, "MLB_ENRICHER_UNAVAILABLE"

    # 3. Enrich
    try:
        raw_iso = getattr(market, "match_start_iso", "") or ""
        game_time = datetime.fromisoformat(raw_iso.replace("Z", "+00:00"))
        enriched = mlb_edge_enricher.enrich(
            game_pk=int(getattr(market, "game_pk", 0) or 0),
            home_abbr=intent.team_a,
            away_abbr=intent.team_b,
            game_time=game_time,
            season=game_time.year,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MLB enrichment failed for %s: %s", cid, exc)
        return None, "MLB_ENRICHMENT_ERROR"

    if enriched is None:
        return None, "MLB_ENRICHMENT_NONE"

    # 4. Build MLBEntryConfig from gate config
    mlb_cfg = MLBEntryConfig(
        rain_skip_threshold=gate_cfg.mlb_rain_skip_threshold,
        rain_partial_threshold=gate_cfg.mlb_rain_partial_threshold,
        pre_game_window_min_hours=gate_cfg.mlb_pre_game_window_min_hours,
        pre_game_window_max_hours=gate_cfg.mlb_pre_game_window_max_hours,
        min_volume_usdc=gate_cfg.mlb_min_market_volume,
        min_liquidity_usdc=gate_cfg.mlb_min_liquidity,
        min_polymarket_price=gate_cfg.mlb_min_polymarket_price,
        max_polymarket_price=gate_cfg.mlb_max_polymarket_price,
        gap_threshold=gate_cfg.mlb_min_gap_threshold,
        position_cap_pct=gate_cfg.mlb_position_cap_pct,
        max_position_usdc=gate_cfg.mlb_max_position_usdc,
        forbid_runline_minus_15_favorite=gate_cfg.mlb_forbid_runline_minus_15_favorite,
    )

    # 5. Wrap market with intent for filter chain
    poly_price = getattr(market, "polymarket_price", None)
    if poly_price is None:
        poly_price = getattr(market, "yes_price", 0.0)
    vol = getattr(market, "volume_24h", 0.0)
    wrapped = SimpleNamespace(
        question=getattr(market, "question", ""),
        outcome=getattr(market, "outcome", ""),
        polymarket_price=poly_price,
        volume_24h=vol,
        liquidity=getattr(market, "liquidity", vol),
        intent=intent,
    )

    # 6. Filter chain
    decision = apply_mlb_entry_filters(wrapped, enriched, mlb_cfg, bankroll)
    if decision is None:
        return None, "MLB_GATE_REJECT"

    # 7. Adapt → Signal (anchor_probability = internal fair_price = P(YES))
    signal = Signal(
        condition_id=cid,
        direction=Direction.BUY_YES,
        anchor_probability=max(0.01, min(0.99, decision.fair_price)),
        market_price=poly_price,
        confidence="B",
        size_usdc=decision.size_usdc,
        entry_reason=EntryReason.NORMAL,
        bookmaker_prob=decision.fair_price,
        sport_tag=getattr(market, "sport_tag", "baseball_mlb"),
        event_id=getattr(market, "event_id", "") or "",
        sports_market_type="moneyline",
    )
    return signal, None
