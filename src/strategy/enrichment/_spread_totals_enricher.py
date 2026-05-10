"""SPEC-K: Spread/Totals branch enricher — odds_enricher'dan ayrılmış sibling.

Spread/totals market'leri için EnrichResult üretir.
Pure orchestration of bookmaker-level parser + weighted average. I/O yok.
"""
from __future__ import annotations

import logging

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import (
    BookmakerProbability,
    calculate_bookmaker_probability,
)
from src.domain.matching.bookmaker_weights import get_bookmaker_weight, is_sharp
from src.domain.matching.market_line_parser import (
    parse_home_away_side,
    parse_spread_line,
    parse_total_line,
)
from src.models.enums import TotalSide
from src.strategy.enrichment._spread_totals_parser import (
    parse_bookmaker_spread,
    parse_bookmaker_totals,
)

logger = logging.getLogger(__name__)


def _enrich_spread(
    bookmakers: list,
    home_team: str,
    away_team: str,
    home_is_a: bool,
    question: str,
    slug: str,
    line_tolerance: float,
) -> EnrichResult:
    """SPEC-K: spread market enrichment.

    Polymarket question'dan target_line, slug'dan home/away side parse.
    Side="home" → YES = home cover; side="away" → YES = away cover.
    team_a perspektifine çevir (home_is_a kullanarak).
    """
    target_line = parse_spread_line(question)
    side = parse_home_away_side(slug)
    if target_line is None or side is None:
        return EnrichResult(
            probability=None, fail_reason=EnrichFailReason.BOOKMAKER_NO_SPREAD,
        )

    prob = _weighted_average_spread(
        bookmakers, home_team, away_team, home_is_a,
        target_line, side, line_tolerance,
    )
    if prob is None:
        return EnrichResult(
            probability=None, fail_reason=EnrichFailReason.BOOKMAKER_NO_SPREAD,
        )
    return EnrichResult(
        probability=prob, fail_reason=None, spread_line=target_line,
    )


def _enrich_totals(
    bookmakers: list,
    question: str,
    line_tolerance: float,
) -> EnrichResult:
    """SPEC-K: totals market enrichment. Polymarket YES = OVER konvansiyonu."""
    parsed = parse_total_line(question)
    if parsed is None:
        return EnrichResult(
            probability=None, fail_reason=EnrichFailReason.BOOKMAKER_NO_TOTALS,
        )
    target_line, side = parsed  # side = "over" by Polymarket convention

    prob = _weighted_average_totals(bookmakers, target_line, line_tolerance, side)
    if prob is None:
        return EnrichResult(
            probability=None, fail_reason=EnrichFailReason.BOOKMAKER_NO_TOTALS,
        )
    return EnrichResult(
        probability=prob, fail_reason=None,
        total_line=target_line, total_side=TotalSide(side),
    )


def _weighted_average_spread(
    bookmakers: list,
    home_team: str,
    away_team: str,
    home_is_a: bool,
    target_line: float,
    side: str,
    line_tolerance: float,
) -> BookmakerProbability | None:
    """Spread için weighted bookmaker average (perspective: team_a's YES side).

    side="home" → Polymarket YES = home cover; "away" → YES = away cover.
    team_a yes_prob: side=home ise home_prob; side=away ise away_prob.
    Sonra home_is_a False ise zaten team_a = away → mantık düz.
    """
    yes_is_home = (side == "home")
    weighted_a = 0.0
    total_weight = 0.0
    bm_count = 0
    has_sharp_flag = False

    for bookmaker in bookmakers:
        bm_key = bookmaker.get("key", "")
        if bm_key == "polymarket":
            continue

        spread_market = None
        for m in bookmaker.get("markets", []):
            if m.get("key") == "spreads":
                spread_market = m
                break
        if spread_market is None:
            continue

        parsed = parse_bookmaker_spread(
            spread_market, home_team, away_team, target_line, line_tolerance,
        )
        if parsed is None:
            continue
        _, home_prob, away_prob = parsed

        # YES tarafının olasılığı (Polymarket konvansiyonu)
        yes_prob = home_prob if yes_is_home else away_prob
        # team_a perspektifi: home_is_a=True → team_a = home; YES home ise prob_a = yes_prob
        # home_is_a=False → team_a = away; YES home ise prob_a = 1 - yes_prob
        prob_a = yes_prob if (home_is_a == yes_is_home) else (1.0 - yes_prob)

        weight = get_bookmaker_weight(bm_key)
        weighted_a += prob_a * weight
        total_weight += weight
        bm_count += 1
        if is_sharp(bm_key):
            has_sharp_flag = True

    if total_weight <= 0 or bm_count == 0:
        return None
    avg_a = weighted_a / total_weight
    return calculate_bookmaker_probability(
        bookmaker_prob=avg_a,
        num_bookmakers=total_weight,
        has_sharp=has_sharp_flag,
    )


def _weighted_average_totals(
    bookmakers: list,
    target_line: float,
    line_tolerance: float,
    side: str,
) -> BookmakerProbability | None:
    """Totals için weighted bookmaker average.

    Polymarket YES = OVER, market_line_parser her zaman side="over" döner.
    Yine de side parametresi ileride UNDER market'i çıkarsa diye taşınır.
    """
    use_over = (side == "over")
    weighted_a = 0.0
    total_weight = 0.0
    bm_count = 0
    has_sharp_flag = False

    for bookmaker in bookmakers:
        bm_key = bookmaker.get("key", "")
        if bm_key == "polymarket":
            continue

        totals_market = None
        for m in bookmaker.get("markets", []):
            if m.get("key") == "totals":
                totals_market = m
                break
        if totals_market is None:
            continue

        parsed = parse_bookmaker_totals(totals_market, target_line, line_tolerance)
        if parsed is None:
            continue
        _, over_prob, under_prob = parsed
        prob_a = over_prob if use_over else under_prob

        weight = get_bookmaker_weight(bm_key)
        weighted_a += prob_a * weight
        total_weight += weight
        bm_count += 1
        if is_sharp(bm_key):
            has_sharp_flag = True

    if total_weight <= 0 or bm_count == 0:
        return None
    avg_a = weighted_a / total_weight
    return calculate_bookmaker_probability(
        bookmaker_prob=avg_a,
        num_bookmakers=total_weight,
        has_sharp=has_sharp_flag,
    )
