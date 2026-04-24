"""Polymarket MarketData → The Odds API sport_key çözümleyici.

Öncelik: static mapping (slug/tag) → tennis dinamik → event discovery fallback.
odds_client DI ile — HTTP çağrıları dışarıdan verilir.
"""
from __future__ import annotations

import logging

from src.domain.matching.odds_sport_keys import resolve_odds_key
from src.strategy.enrichment.question_parser import extract_teams

logger = logging.getLogger(__name__)

_GENERIC_TENNIS_WORDS: frozenset[str] = frozenset({
    "open", "grand", "prix", "cup", "championship", "masters", "series",
})

# SPEC-003: Polymarket sponsor-named tournaments → Odds API city-based keys.
# Odds API guide (2026-04-04): tennis keys are strictly city/location-based
# (e.g., tennis_atp_munich, tennis_wta_stuttgart_open). Polymarket question
# text sometimes uses sponsor names (BMW Open, Porsche Tennis Grand Prix).
# This alias table augments the combined string with the city token so the
# existing score-based match in _match_tennis_key picks the right key.
_TENNIS_SPONSOR_ALIASES: dict[str, str] = {
    "bmw open": "munich",
    "porsche tennis grand prix": "stuttgart",
}


def resolve_sport_key(
    question: str,
    slug: str,
    tags: list[str],
    odds_client,
) -> str | None:
    """Market için The Odds API sport_key bul. None → bulunamadı.

    odds_client: OddsAPIClient benzeri. `get_sports(include_inactive=False)` ve
    `get_events(sport_key)` metodları kullanılır.
    """
    # 1. Static mapping — pazarların ~95%'ini kapsar
    # Generic tennis keys (tennis_atp/tennis_wta) burada short-circuit yapma:
    # önce dinamik turnuva resolution dene; bulamazsa generic key'e düş.
    _GENERIC_TENNIS: frozenset[str] = frozenset({"tennis_atp", "tennis_wta"})
    static = resolve_odds_key(slug, tags)
    if static and static not in _GENERIC_TENNIS:
        return static

    # 2. Tennis: dinamik turnuva key matching
    # Slug prefix otoritesi question text'ten önce — slug 'wta-...' ise WTA zorla
    # (aksi halde WTA market'in ATP branch'ine kaçması bug'ı).
    slug_lower = (slug or "").lower()
    prefix = slug_lower.split("-")[0] if slug_lower else ""
    q_lower = (question or "").lower()

    if prefix == "wta":
        return _match_tennis_key("wta", q_lower, slug_lower, odds_client) or static
    if prefix == "atp":
        return _match_tennis_key("atp", q_lower, slug_lower, odds_client) or static
    # Slug bilgi vermiyor — question text'ten kestir
    if "wta" in q_lower or "women" in q_lower:
        return _match_tennis_key("wta", q_lower, slug_lower, odds_client) or static
    if "atp" in q_lower or "tennis" in q_lower:
        return _match_tennis_key("atp", q_lower, slug_lower, odds_client) or static

    # 3. Dinamik discovery — takım adlarıyla tüm sport'ların event'lerini ara
    team_a, team_b = extract_teams(question)
    if team_a or team_b:
        return _discover_by_events(team_a or "", team_b or "", odds_client)

    return static


def _match_tennis_key(gender: str, q_lower: str, slug_lower: str, odds_client) -> str | None:
    """Aktif tennis key'leri arasından en iyi turnuva eşleşmesini bul."""
    sports = odds_client.get_sports(include_inactive=False) or []
    prefix = f"tennis_{gender}"
    keys = [s["key"] for s in sports
            if isinstance(s, dict) and s.get("key", "").startswith(prefix) and s.get("active")]
    if not keys:
        return None
    if len(keys) == 1:
        return keys[0]

    combined = f"{q_lower} {slug_lower}"

    # SPEC-003: sponsor→city augmentation — conservative (append, don't replace)
    for sponsor, city in _TENNIS_SPONSOR_ALIASES.items():
        if sponsor in combined:
            combined = f"{combined} {city}"

    # Her key için spesifik kelime eşleşmesi sayısını hesapla
    best_key: str | None = None
    best_score = 0
    for key in keys:
        parts = key.split("_")[2:]  # 'tennis_atp_miami_open' → ['miami', 'open']
        specific = [p for p in parts if len(p) > 2 and p not in _GENERIC_TENNIS_WORDS]
        score = sum(1 for p in specific if p in combined)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key:
        return best_key

    # Turnuva adı tamamen geçiyorsa
    for key in keys:
        tourney = " ".join(key.split("_")[2:])
        if tourney and tourney in combined:
            return key

    return None


def _discover_by_events(team_a: str, team_b: str, odds_client) -> str | None:
    """Aktif sport'ların event listesinde takım adı eşleşmesi ara."""
    sports = odds_client.get_sports(include_inactive=False) or []
    active_keys = [s["key"] for s in sports
                   if isinstance(s, dict) and s.get("key") and s.get("active")]

    a_lower = team_a.lower()
    b_lower = team_b.lower()

    best_key: str | None = None
    best_count = 0

    for sk in active_keys:
        events = odds_client.get_events(sk) or []
        if not isinstance(events, list):
            continue
        for event in events:
            home = (event.get("home_team") or "").lower()
            away = (event.get("away_team") or "").lower()
            if not home or not away:
                continue

            a_match = a_lower and (a_lower in home or home in a_lower
                                    or a_lower in away or away in a_lower)
            b_match = b_lower and (b_lower in home or home in b_lower
                                    or b_lower in away or away in b_lower)
            count = int(bool(a_match)) + int(bool(b_match))
            if count == 2:
                return sk
            if count == 1 and count > best_count:
                best_count = count
                best_key = sk

    return best_key
