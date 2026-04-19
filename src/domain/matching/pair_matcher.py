"""Team pair matching — 4-layer confidence (pure, rapidfuzz ile).

L1: Exact canonical / alias (1.0)
L2: Token overlap (0.85-0.90)
L3: Fuzzy SequenceMatcher + rapidfuzz token_sort / partial

Date-aware matching: MLB/KBO seri maçlarında aynı takımlar arka arkaya
günlerde oynar. find_best_event_match expected_start verildiğinde
commence_time en yakın event'i tercih eder.
"""
from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher

from rapidfuzz import fuzz

from src.domain.matching.team_resolver import canonicalize, normalize

_NOISE: frozenset[str] = frozenset({"team", "the", "of", "de", "fc", "sc", "city", "united"})


def match_team(query: str, candidate: str) -> tuple[bool, float, str]:
    """İki takım adını karşılaştır. (is_match, confidence, method)."""
    q = normalize(query)
    c = normalize(candidate)
    if not q or not c:
        return False, 0.0, "empty"

    # L1: Exact canonical
    if canonicalize(query) == canonicalize(candidate):
        return True, 1.0, "exact_alias"

    # L2: Token overlap
    q_tokens = set(q.split())
    c_tokens = set(c.split())

    if len(q_tokens) == 1:
        q_word = next(iter(q_tokens))
        if q_word not in _NOISE and (q_word in c_tokens or any(q_word in ct for ct in c_tokens)):
            return True, 0.90, "token_substring"

    if len(q_tokens) > 1 and len(c_tokens) > 1:
        overlap = q_tokens & c_tokens
        meaningful = overlap - _NOISE
        if meaningful and len(overlap) / min(len(q_tokens), len(c_tokens)) >= 0.5:
            return True, 0.85, "token_overlap"

    # L3a: Fuzzy SequenceMatcher
    score = SequenceMatcher(None, q, c).ratio()
    if score >= 0.80:
        return True, score, "fuzzy"

    # L3b: rapidfuzz token_sort (uzun isimler)
    if len(q) >= 4 and len(c) >= 4:
        rf_score = fuzz.token_sort_ratio(q, c) / 100.0
        if rf_score >= 0.85:
            return True, rf_score, "fuzzy_token_sort"

    # L3c: rapidfuzz partial_ratio + token overlap guard
    if len(q) >= 4 and len(c) >= 4:
        partial = fuzz.partial_ratio(q, c) / 100.0
        overlap = q_tokens & c_tokens
        if partial >= 0.80 and overlap:
            return True, partial, "fuzzy_partial"

    return False, max(score, 0.0), "no_match"


def match_pair(
    market_names: tuple[str, str],
    entry_names: tuple[str, str],
) -> tuple[bool, float]:
    """İki takım çiftini karşılaştır. Normal ve ters sıra dener, ikisi de eşleşmeli."""
    # Normal order
    ma, ca, _ = match_team(market_names[0], entry_names[0])
    mb, cb, _ = match_team(market_names[1], entry_names[1])
    if ma and mb:
        return True, min(ca, cb)

    # Swapped
    ma2, ca2, _ = match_team(market_names[0], entry_names[1])
    mb2, cb2, _ = match_team(market_names[1], entry_names[0])
    if ma2 and mb2:
        return True, min(ca2, cb2)

    return False, 0.0


def _parse_iso(iso: str) -> datetime | None:
    """ISO 8601 string → datetime (UTC). Parse edilemezse None."""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def find_best_event_match(
    team_a: str,
    team_b: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
    expected_start: str = "",
) -> tuple[dict, float] | None:
    """Bir takım çifti için en iyi event'i bul (Odds API match'ing için).

    expected_start verildiğinde: aynı takım çifti birden fazla event'te
    eşleşirse (MLB/KBO seri maçları), commence_time beklenen tarihe en
    yakın olan seçilir. Verilmezse eski davranış (ilk en yüksek conf).
    """
    candidates: list[tuple[dict, float]] = []

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue
        is_match, conf = match_pair((team_a, team_b), (home, away))
        if is_match and conf >= min_confidence:
            candidates.append((event, conf))

    if not candidates:
        return None

    # Tek eşleşme → doğrudan döndür
    if len(candidates) == 1:
        return candidates[0]

    # Birden fazla eşleşme: expected_start varsa commence_time yakınlığına göre seç
    expected_dt = _parse_iso(expected_start)
    if expected_dt:
        def _time_distance(candidate: tuple[dict, float]) -> float:
            ct = _parse_iso(candidate[0].get("commence_time", ""))
            if ct is None:
                return float("inf")
            return abs((ct - expected_dt).total_seconds())

        candidates.sort(key=_time_distance)
        return candidates[0]

    # expected_start yoksa en yüksek confidence'ı döndür
    candidates.sort(key=lambda c: c[1], reverse=True)
    return candidates[0]


def find_best_single_team_match(
    team: str,
    events: list[dict],
    home_key: str = "home_team",
    away_key: str = "away_team",
    min_confidence: float = 0.80,
) -> tuple[dict, float, bool] | None:
    """Tek takım adı için en iyi event. (event, confidence, team_is_home) veya None."""
    best_event: dict | None = None
    best_conf = 0.0
    best_is_home = True

    for event in events:
        home = event.get(home_key, "")
        away = event.get(away_key, "")
        if not home or not away:
            continue

        is_match_h, conf_h, _ = match_team(team, home)
        if is_match_h and conf_h > best_conf:
            best_conf = conf_h
            best_event = event
            best_is_home = True

        is_match_a, conf_a, _ = match_team(team, away)
        if is_match_a and conf_a > best_conf:
            best_conf = conf_a
            best_event = event
            best_is_home = False

    if best_event and best_conf >= min_confidence:
        return best_event, best_conf, best_is_home
    return None
