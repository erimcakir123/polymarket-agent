"""Three-way market display title enrichment (SPEC-015).

Soccer/rugby/AFL/handball 3-way event'lerinde home/away sub-market'inin Polymarket
question'ı tek takım taşır ("Will X win?") → dashboard kartı "X vs Y" başlığı için
rakip adını bilemez. Draw sub-market'inin question'ı iki takımı da içerir
("Will X vs Y end in a draw?"); bu modül aynı event'in draw question'ından
"X vs Y" başlığını türetip event'in üç sub-market'inin `match_title` alanına yazar.

Ham `question` alanı dokunulmaz — score matching / question_parser invariantları
korunur (PLAN-011).
"""
from __future__ import annotations

import re

from src.domain.matching.event_grouper import group_markets_by_event
from src.models.market import MarketData

_DRAW_TITLE_PATTERN = re.compile(
    r"^Will\s+(.+?)\s+vs\.?\s+(.+?)\s+end\s+in\s+a\s+draw\??$",
    re.IGNORECASE,
)


def extract_teams_from_draw(draw_question: str) -> tuple[str, str] | None:
    """Draw sub-market question'ından (home_name, away_name) çıkar.

    Örnek: "Will PFK Krylia Sovetov Samara vs Spartak Kostroma end in a draw?"
           → ("PFK Krylia Sovetov Samara", "Spartak Kostroma")

    Regex eşleşmezse None. Boş/None question → None.
    """
    if not draw_question:
        return None
    m = _DRAW_TITLE_PATTERN.match(draw_question.strip())
    if not m:
        return None
    home = m.group(1).strip()
    away = m.group(2).strip()
    if not home or not away:
        return None
    return home, away


def enrich_three_way_titles(markets: list[MarketData]) -> list[MarketData]:
    """3-way event'lerin home/away/draw market'lerine `match_title` ("X vs Y") yazar.

    - 2-way market'ler pass-through (model_copy yapılmaz).
    - 3-way grup ama draw question parse edilemezse o event dokunulmaz.
    - Mevcut match_title boş değilse dokunulmaz (re-enrichment idempotent).
    """
    groups = group_markets_by_event(markets)
    enriched_ids: dict[str, str] = {}  # condition_id → match_title

    for g in groups:
        if g.market_type != "THREE_WAY":
            continue
        home, draw, away = g.classify_outcomes()
        if draw is None:
            continue
        teams = extract_teams_from_draw(draw.question)
        if teams is None:
            continue
        title = f"{teams[0]} vs {teams[1]}"
        for m in (home, draw, away):
            if m is not None and not m.match_title:
                enriched_ids[m.condition_id] = title

    if not enriched_ids:
        return markets

    return [
        m.model_copy(update={"match_title": enriched_ids[m.condition_id]})
        if m.condition_id in enriched_ids
        else m
        for m in markets
    ]
