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
from src.domain.matching.odds_sport_keys import is_soccer_key
from src.domain.matching.pair_matcher import (
    find_best_event_match,
    find_best_single_team_match,
    match_team,
)
from src.models.market import MarketData
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

logger = logging.getLogger(__name__)


def _odds_query_params() -> dict:
    """24h içinde başlayan event'ler için h2h market parametreleri."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return {
        "regions": "us,uk,eu",
        "markets": "h2h",
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
                continue
            hr, ar, dr = 1.0 / home_odds, 1.0 / away_odds, 1.0 / draw_odds
            total = hr + ar + dr
            return hr / total, ar / total, dr / total

        hr, ar = 1.0 / home_odds, 1.0 / away_odds
        total = hr + ar
        return hr / total, ar / total, None

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

    # 5. Weighted bookmaker average
    prob = _weighted_average(
        best_event.get("bookmakers", []),
        home_team, away_team, home_is_a, is_soccer,
    )
    if prob is None:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)
    return EnrichResult(probability=prob, fail_reason=None)


def _weighted_average(
    bookmakers: list,
    home_team: str,
    away_team: str,
    home_is_a: bool,
    is_soccer: bool,
) -> BookmakerProbability | None:
    """Bookmaker başına ağırlık uygula, toplam probability (team_a perspektifinden)."""
    weighted_a = 0.0
    total_weight = 0.0
    bm_count = 0
    has_sharp_flag = False

    for bookmaker in bookmakers:
        bm_key = bookmaker.get("key", "")
        if bm_key == "polymarket":
            continue  # Circular data engelle
        parsed = _parse_bookmaker_markets(
            bookmaker.get("markets", []), home_team, away_team, is_soccer,
        )
        if parsed is None:
            continue
        home_prob, away_prob, _ = parsed
        weight = get_bookmaker_weight(bm_key)
        prob_a = home_prob if home_is_a else away_prob
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
