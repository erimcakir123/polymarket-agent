"""Odds API verisini Polymarket MarketData ile birleştir.

Akış: market → question_parser → sport_key_resolver → odds_client.get_odds →
find_best_event_match → weighted bookmaker probability → BookmakerProbability.

SPEC-K: spreads/totals market'leri için ek branch — moneyline davranışı korunur.

Sadece pure data birleştirme + API çağrısı (strategy katmanı). Iş mantığı YOK.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import BookmakerProbability, calculate_bookmaker_probability
from src.domain.matching.bookmaker_weights import get_bookmaker_weight, is_sharp
from src.domain.matching.market_line_parser import (
    parse_home_away_side,
    parse_spread_line,
    parse_total_line,
)
from src.domain.matching.odds_sport_keys import is_soccer_key
from src.domain.matching.pair_matcher import (
    find_best_event_match,
    find_best_single_team_match,
    match_team,
)
from src.models.enums import SportsMarketType, TotalSide
from src.models.market import MarketData
from src.strategy.enrichment._spread_totals_parser import (
    parse_bookmaker_spread,
    parse_bookmaker_totals,
)
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

logger = logging.getLogger(__name__)

# SPEC-K default — config'den override edilir (settings.OddsApiConfig).
_DEFAULT_LINE_TOLERANCE = 0.5


def _odds_query_params() -> dict:
    """24h içinde başlayan event'ler için h2h+spreads+totals market parametreleri.

    SPEC-K: spreads ve totals tek API çağrısında geliyor (Odds API destekler).
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return {
        "regions": "us,uk,eu",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",
        "commenceTimeFrom": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo": (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _parse_bookmaker_markets(
    markets: list,
    home_team: str,
    away_team: str,
    is_soccer: bool,
) -> tuple[float, float, float | None] | None:
    """Bir bookmaker'ın h2h market'ından (home_prob, away_prob, draw_prob) çıkar.

    Vig normalize (olasılıkları 1.0'a topla). Soccer için 3-way outcome gerekli;
    yoksa bu bookmaker atlanır (draw mass home/away'e absorbe olur → bias).

    Vig sanity:
    - 3-way (soccer) tipik vig %5-10 → pre-normalize total beklenen [1.05, 1.10].
      [0.85, 1.30] dışında ise outlier (yanlış outcome, stale data, bug).
    - 2-way tipik vig %2-8 → pre-normalize total beklenen [1.02, 1.08].
      [0.85, 1.20] dışında ise outlier.
    """
    for market in markets:
        if market.get("key") != "h2h":
            continue
        home_odds = away_odds = draw_odds = None
        for outcome in market.get("outcomes", []):
            name = outcome.get("name", "")
            price = outcome.get("price", 0) or 0
            if name == home_team:
                home_odds = price
            elif name == away_team:
                away_odds = price
            elif name.lower() == "draw":
                draw_odds = price

        if not (home_odds and away_odds and home_odds > 1 and away_odds > 1):
            continue

        if is_soccer:
            if not (draw_odds and draw_odds > 1):
                # Soccer 3-way zorunlu; draw outcome eksik → bookmaker atla.
                return None
            hr, ar, dr = 1.0 / home_odds, 1.0 / away_odds, 1.0 / draw_odds
            total = hr + ar + dr
            # 3-way vig sanity: typical 1.05-1.10, outlier reddet.
            if not (0.85 <= total <= 1.30):
                return None
            return hr / total, ar / total, dr / total

        hr, ar = 1.0 / home_odds, 1.0 / away_odds
        total = hr + ar
        # 2-way vig sanity: typical 1.02-1.08, outlier reddet.
        if not (0.85 <= total <= 1.20):
            return None
        return hr / total, ar / total, None

    return None


def enrich_market(
    market: MarketData,
    odds_client,
    line_tolerance: float = _DEFAULT_LINE_TOLERANCE,
) -> EnrichResult:
    """MarketData + Odds API → EnrichResult (probability veya fail_reason).

    SPEC-K: market.sports_market_type'a göre 3 branch — moneyline / spreads / totals.
    line_tolerance spread/totals line eşleşmesi için (config'den geçirilir).

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

    # 3. Fetch odds
    events = odds_client.get_odds(sport_key, _odds_query_params())
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
    is_soccer = is_soccer_key(sport_key)
    bookmakers = best_event.get("bookmakers", [])

    # 5. Branch by market type — SPEC-K
    market_type = market.sports_market_type or SportsMarketType.MONEYLINE.value

    if market_type == SportsMarketType.SPREADS.value:
        return _enrich_spread(
            bookmakers, home_team, away_team, home_is_a,
            market.question, market.slug, line_tolerance,
        )
    if market_type == SportsMarketType.TOTALS.value:
        return _enrich_totals(bookmakers, market.question, line_tolerance)

    # Moneyline (default + boş string + "moneyline")
    prob = _weighted_average(
        bookmakers, home_team, away_team, home_is_a, is_soccer,
    )
    if prob is None:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)
    return EnrichResult(probability=prob, fail_reason=None)


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


def _weighted_average(
    bookmakers: list,
    home_team: str,
    away_team: str,
    home_is_a: bool,
    is_soccer: bool,
) -> BookmakerProbability | None:
    """Bookmaker başına ağırlık uygula, toplam probability (team_a perspektifinden).

    Drop counter: parse None döndüren bookmaker'ları say (no_draw veya vig outlier).
    En az 1 drop varsa INFO log — futbol açılınca silent skip görünür olsun.
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
            bookmaker.get("markets", []), home_team, away_team, is_soccer,
        )
        if parsed is None:
            skipped_count += 1
            continue
        home_prob, away_prob, _ = parsed
        weight = get_bookmaker_weight(bm_key)
        prob_a = home_prob if home_is_a else away_prob
        weighted_a += prob_a * weight
        total_weight += weight
        bm_count += 1
        if is_sharp(bm_key):
            has_sharp_flag = True

    if skipped_count > 0:
        logger.info(
            "Bookmaker drop: %d/%d skipped (no_draw or vig outlier) — sport=%s",
            skipped_count,
            len(bookmakers),
            "soccer" if is_soccer else "h2h",
        )

    if total_weight <= 0 or bm_count == 0:
        return None

    avg_a = weighted_a / total_weight
    return calculate_bookmaker_probability(
        bookmaker_prob=avg_a,
        num_bookmakers=total_weight,
        has_sharp=has_sharp_flag,
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
