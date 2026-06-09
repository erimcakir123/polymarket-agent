"""Odds API verisini Polymarket MarketData ile birleştir.

Akış: market → question_parser → sport_key_resolver → odds_client.get_odds →
find_best_event_match → weighted bookmaker probability → BookmakerProbability.

Sadece pure data birleştirme + API çağrısı (strategy katmanı). Iş mantığı YOK.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import BookmakerProbability, calculate_bookmaker_probability
from src.domain.matching.bookmaker_weights import get_bookmaker_weight, is_sharp
from src.domain.matching.market_line_parser import parse_total_line
from src.domain.matching.pair_matcher import (
    find_best_event_match,
    find_best_single_team_match,
    match_team,
)
from src.models.market import MarketData
from src.strategy.enrichment._spread_totals_parser import parse_bookmaker_totals
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

logger = logging.getLogger(__name__)

# Vig sanity bounds (inline — pre-SPEC-K state).
# Pre-normalize 1/odds toplamı (2-way h2h): tipik 1.02-1.08 → [0.85, 1.20] dışı outlier.
_VIG_2WAY_MIN = 0.85
_VIG_2WAY_MAX = 1.20


def _odds_query_params(markets: str = "h2h") -> dict:
    """24h içinde başlayan event'ler için market parametreleri (markets seçilebilir)."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return {
        "regions": "us,uk,eu",
        "markets": markets,
        "oddsFormat": "decimal",
        "commenceTimeFrom": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo": (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _is_totals_market(market: MarketData) -> bool:
    """Totals (over/under) market mi? sports_market_type öncelik, slug fallback."""
    declared = (market.sports_market_type or "").strip().lower()
    if declared in ("totals", "tennis_match_totals"):
        return True
    return "-total-" in (market.slug or "").lower()


def _parse_bookmaker_markets(
    markets: list,
    home_team: str,
    away_team: str,
) -> tuple[float, float] | None:
    """Bir bookmaker'ın h2h market'ından (home_prob, away_prob) çıkar.

    Vig normalize (olasılıkları 1.0'a topla).

    Vig sanity: 2-way tipik vig %2-8 → pre-normalize total beklenen [1.02, 1.08].
    [0.85, 1.20] dışında ise outlier (yanlış outcome, stale data, bug).
    """
    for market in markets:
        if market.get("key") != "h2h":
            continue
        home_odds = away_odds = None
        for outcome in market.get("outcomes", []):
            name = outcome.get("name", "")
            price = outcome.get("price", 0) or 0
            if name == home_team:
                home_odds = price
            elif name == away_team:
                away_odds = price

        if not (home_odds and away_odds and home_odds > 1 and away_odds > 1):
            continue

        hr, ar = 1.0 / home_odds, 1.0 / away_odds
        total = hr + ar
        # 2-way vig sanity: typical 1.02-1.08, outlier reddet.
        if not (_VIG_2WAY_MIN <= total <= _VIG_2WAY_MAX):
            return None
        return hr / total, ar / total

    return None


def enrich_market(market: MarketData, odds_client) -> EnrichResult:
    """MarketData + Odds API → EnrichResult (probability veya fail_reason).

    Her başarısız yol için EnrichFailReason döner. Caller fail_reason'a göre skip_detail yazar.
    """
    # 1. Sport key resolve
    sport_key = resolve_sport_key(market.question, market.slug, market.tags, odds_client)
    if not sport_key:
        logger.debug("No sport_key for %s", market.slug[:40])
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.SPORT_KEY_UNRESOLVED)

    # 2. Team extraction
    team_a_name, team_b_name = extract_teams(market.question)
    if not team_a_name:
        logger.debug("Cannot extract teams from: %s", market.question[:80])
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.TEAM_EXTRACT_FAILED)

    # 3. Fetch odds (totals market type → totals odds, aksi h2h)
    is_totals = _is_totals_market(market)
    events = odds_client.get_odds(
        sport_key, _odds_query_params("totals" if is_totals else "h2h"),
    )
    if not events:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_EVENTS)

    # 4. Match event
    if team_b_name:
        match_result = find_best_event_match(team_a_name, team_b_name, events)
        if not match_result:
            logger.debug("No event match for %s vs %s in %d events",
                         team_a_name, team_b_name, len(events))
            return EnrichResult(probability=None, fail_reason=EnrichFailReason.EVENT_NO_MATCH)
        best_event, _ = match_result
        home_is_a, _, _ = match_team(team_a_name, best_event.get("home_team", ""))
    else:
        single = find_best_single_team_match(team_a_name, events)
        if not single:
            return EnrichResult(probability=None, fail_reason=EnrichFailReason.EVENT_NO_MATCH)
        best_event, _, home_is_a = single
        team_b_name = best_event.get("away_team" if home_is_a else "home_team", "")

    home_team = best_event.get("home_team", "")
    away_team = best_event.get("away_team", "")

    # 5. Weighted bookmaker average (totals → Over olasılığı; aksi h2h)
    if is_totals:
        line_side = parse_total_line(market.question)
        if line_side is None:
            return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)
        target_line, _side = line_side
        prob = _weighted_totals_average(best_event.get("bookmakers", []), target_line)
    else:
        prob = _weighted_average(
            best_event.get("bookmakers", []),
            home_team, away_team, home_is_a,
        )
    if prob is None:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)
    return EnrichResult(probability=prob, fail_reason=None)


def _weighted_average(
    bookmakers: list,
    home_team: str,
    away_team: str,
    home_is_a: bool,
) -> BookmakerProbability | None:
    """Bookmaker başına ağırlık uygula, toplam probability (team_a perspektifinden).

    Drop counter: parse None döndüren bookmaker'ları say (vig outlier).
    En az 1 drop varsa INFO log — silent skip görünür olsun.
    """
    weighted_a = 0.0
    total_weight = 0.0
    bm_count = 0
    skipped_count = 0
    has_sharp_flag = False

    for bookmaker in bookmakers:
        bm_key = bookmaker.get("key", "")
        if bm_key == "polymarket":
            continue  # Circular data engelle
        parsed = _parse_bookmaker_markets(
            bookmaker.get("markets", []), home_team, away_team,
        )
        if parsed is None:
            skipped_count += 1
            continue
        home_prob, away_prob = parsed
        weight = get_bookmaker_weight(bm_key)
        prob_a = home_prob if home_is_a else away_prob
        weighted_a += prob_a * weight
        total_weight += weight
        bm_count += 1
        if is_sharp(bm_key):
            has_sharp_flag = True

    if skipped_count > 0:
        logger.info(
            "Bookmaker drop: %d/%d skipped (vig outlier)",
            skipped_count,
            len(bookmakers),
        )

    if total_weight <= 0 or bm_count == 0:
        return None

    avg_a = weighted_a / total_weight
    return calculate_bookmaker_probability(
        bookmaker_prob=avg_a,
        num_bookmakers=total_weight,
        has_sharp=has_sharp_flag,
    )


def _weighted_totals_average(
    bookmakers: list,
    target_line: float,
) -> BookmakerProbability | None:
    """Bookmaker 'totals' market'larından ağırlıklı Over olasılığı (P(YES)=Over).

    parse_bookmaker_totals her bookmaker için line eşleştirir (±0.5) + vig
    normalize eder. Line tutmayan/outlier bookmaker düşürülür (drop sayılır).
    """
    weighted_over = 0.0
    total_weight = 0.0
    bm_count = 0
    skipped_count = 0
    has_sharp_flag = False

    for bookmaker in bookmakers:
        bm_key = bookmaker.get("key", "")
        if bm_key == "polymarket":
            continue  # Circular data engelle
        totals_market = None
        for mk in bookmaker.get("markets", []):
            if mk.get("key") == "totals":
                totals_market = mk
                break
        if totals_market is None:
            skipped_count += 1
            continue
        parsed = parse_bookmaker_totals(totals_market, target_line)
        if parsed is None:
            skipped_count += 1
            continue
        _line, over_prob, _under_prob = parsed
        weight = get_bookmaker_weight(bm_key)
        weighted_over += over_prob * weight
        total_weight += weight
        bm_count += 1
        if is_sharp(bm_key):
            has_sharp_flag = True

    if skipped_count > 0:
        logger.info(
            "Totals bookmaker drop: %d/%d (line mismatch / vig outlier)",
            skipped_count, len(bookmakers),
        )

    if total_weight <= 0 or bm_count == 0:
        return None

    avg_over = weighted_over / total_weight
    return calculate_bookmaker_probability(
        bookmaker_prob=avg_over,
        num_bookmakers=total_weight,
        has_sharp=has_sharp_flag,
    )
