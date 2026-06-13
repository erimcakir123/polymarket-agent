"""Polymarket çözülmüş marketlerinden taze tenis sonucu hasadı (Orchestration).

Katmanları koordine eder: gamma (infra) + extract_teams/_resolve (strategy) +
winner_loser_from_resolution (domain) + surface_map (infra). Saf değil — I/O
gamma çağrısı yapar; ama gamma DI ile verilir (test fake).
"""
from __future__ import annotations

import logging
from typing import Callable

from src.domain.pricing.tennis.harvested_result import (
    HarvestedResult,
    winner_loser_from_resolution,
)
from src.strategy.enrichment.question_parser import extract_teams
from src.strategy.enrichment.tennis_dispatch import _extract_location, _match_surface

logger = logging.getLogger(__name__)


def harvest_results(
    seen_markets: list[dict],
    gamma_client,
    resolve_name: Callable[[str], str | None],
    surface_map: dict[str, str],
    already_keys: set[str],
    today_yyyymmdd: str,
    max_fetches: int = 400,
) -> list[HarvestedResult]:
    """Görülen tenis marketlerinden çözülenlerin sonucunu topla.

    resolve_name: Polymarket adı → Sackmann adı (çözülemez → None).
    today_yyyymmdd: sonuç tarihi (çözüm günü; sıralama + dedupe için).
    max_fetches: gamma çağrı tavanı (rate-limit nezaketi).
    """
    out: list[HarvestedResult] = []
    fetches = 0
    for m in seen_markets:
        if fetches >= max_fetches:
            logger.info("Harvest fetch tavanı (%d) — kalan atlandı", max_fetches)
            break
        question = m.get("question") or ""
        a_raw, b_raw = extract_teams(question)
        if not a_raw or not b_raw:
            continue
        win_a, win_b = resolve_name(a_raw), resolve_name(b_raw)
        if not win_a or not win_b:
            continue
        market = gamma_client.fetch_closed_market_by_condition(m.get("condition_id"))
        fetches += 1
        pair = winner_loser_from_resolution(market or {}, win_a, win_b)
        if pair is None:
            continue
        winner, loser = pair
        key = f"{today_yyyymmdd}|{winner}|{loser}"
        if key in already_keys:
            continue
        loc = _extract_location(question)
        surface = (_match_surface(loc, surface_map) if loc else None) or "Unknown"
        already_keys.add(key)
        out.append(HarvestedResult(winner=winner, loser=loser, surface=surface, date=today_yyyymmdd))
    return out
