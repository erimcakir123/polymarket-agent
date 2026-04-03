# src/matching/__init__.py
"""Matching pipeline — bridges Polymarket markets to scout entries.

Public API:
    match_markets(markets, scout_queue, cache_dir=None) -> list[dict]

Replaces: src/market_matcher.py (match_batch + AliasStore)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.matching.sport_classifier import classify_sport, classify_entry, sports_compatible
from src.matching.slug_parser import parse_slug, extract_slug_tokens
from src.matching.team_resolver import TeamResolver, normalize
from src.matching.pair_matcher import match_team, match_pair

logger = logging.getLogger(__name__)

# Module-level singleton (created on first call)
_resolver: Optional[TeamResolver] = None


def _get_resolver(cache_dir: Optional[Path] = None) -> TeamResolver:
    global _resolver
    if _resolver is None:
        cache_path = (cache_dir / "team_resolver_cache.json") if cache_dir else None
        _resolver = TeamResolver(cache_path=cache_path, auto_refresh=cache_dir is None)
    return _resolver


def match_markets(
    markets: list,
    scout_queue: dict,
    cache_dir: Optional[Path] = None,
) -> list[dict]:
    """Match Polymarket markets to scout entries.

    Returns list of dicts: {"market": m, "scout_entry": entry_copy, "scout_key": key}
    Same format as old market_matcher.match_batch().
    """
    resolver = _get_resolver(cache_dir)
    matched = []
    used_keys: set[str] = set()

    for market in markets:
        slug = (getattr(market, "slug", "") or "").lower()
        question = (getattr(market, "question", "") or "").lower()
        market_sport = classify_sport(market)
        slug_parts = parse_slug(slug)
        slug_tokens = extract_slug_tokens(slug)

        # Resolve slug abbreviations to names
        resolved_names: list[str] = []
        for token in slug_parts.team_tokens:
            name = resolver.resolve(token)
            if name:
                resolved_names.append(name)

        best_match = None
        best_confidence = 0.0
        best_key = ""
        candidates: list[tuple[str, dict, float]] = []

        for key, entry in scout_queue.items():
            if entry.get("entered") or key in used_keys:
                continue

            entry_sport = classify_entry(entry)
            if not sports_compatible(market_sport, entry_sport):
                continue

            entry_a = entry.get("team_a", "")
            entry_b = entry.get("team_b", "")
            if not entry_a or not entry_b:
                continue

            abbrev_a = (entry.get("abbrev_a") or "").lower()
            abbrev_b = (entry.get("abbrev_b") or "").lower()
            short_a = (entry.get("short_a") or "").lower()
            short_b = (entry.get("short_b") or "").lower()

            confidence = 0.0

            # Layer 1: Abbreviation in slug tokens (both must match)
            if abbrev_a and abbrev_b:
                if abbrev_a in slug_tokens and abbrev_b in slug_tokens:
                    confidence = 1.0

            # Layer 2: Resolved slug names match entry names
            if confidence < 0.9 and len(resolved_names) >= 2:
                is_match, conf = match_pair(
                    (resolved_names[0], resolved_names[1]),
                    (entry_a, entry_b),
                )
                if is_match:
                    confidence = max(confidence, conf)

            # Layer 3: Short names in question/slug
            if confidence < 0.9:
                if short_a and short_b:
                    if ((short_a in question or short_a in slug) and
                            (short_b in question or short_b in slug)):
                        confidence = max(confidence, 0.90)

            # Layer 4: Full name in question
            if confidence < 0.85:
                norm_a = normalize(entry_a)
                norm_b = normalize(entry_b)
                if norm_a and norm_b:
                    if ((norm_a in question or norm_a in slug) and
                            (norm_b in question or norm_b in slug)):
                        confidence = max(confidence, 0.85)

            # Layer 5: Fuzzy on question text
            if confidence < 0.80:
                norm_a = normalize(entry_a)
                norm_b = normalize(entry_b)
                if len(norm_a) >= 4 and len(norm_b) >= 4:
                    from rapidfuzz import fuzz
                    score_a = max(
                        fuzz.token_sort_ratio(norm_a, question),
                        fuzz.partial_ratio(norm_a, question),
                    )
                    score_b = max(
                        fuzz.token_sort_ratio(norm_b, question),
                        fuzz.partial_ratio(norm_b, question),
                    )
                    if score_a >= 65 and score_b >= 65:
                        fuzzy_conf = min(score_a, score_b) / 100.0
                        if fuzzy_conf >= 0.80:
                            confidence = max(confidence, fuzzy_conf)

            if confidence > 0.0:
                candidates.append((key, entry, confidence))
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = entry
                best_key = key

        # Doubleheader: same team pair, pick earliest
        if len(candidates) > 1 and best_match:
            team_pair = frozenset([
                best_match.get("team_a", "").lower(),
                best_match.get("team_b", "").lower(),
            ])
            same_pair = [
                (k, e, c) for k, e, c in candidates
                if frozenset([e.get("team_a", "").lower(),
                              e.get("team_b", "").lower()]) == team_pair
            ]
            if len(same_pair) > 1:
                same_pair.sort(key=lambda x: x[1].get("match_time", ""))
                best_key, best_match, best_confidence = same_pair[0]

        # Threshold
        if best_match and best_confidence >= 0.60:
            entry_copy = dict(best_match)
            entry_copy["matched"] = True
            entry_copy["match_confidence"] = best_confidence
            matched.append({
                "market": market,
                "scout_entry": entry_copy,
                "scout_key": best_key,
            })
            used_keys.add(best_key)
            logger.debug("Matched [%.2f]: %s -> %s vs %s",
                         best_confidence, slug[:40],
                         best_match.get("team_a", ""),
                         best_match.get("team_b", ""))

    if matched:
        logger.info("matching: %d/%d markets matched", len(matched), len(markets))

    return matched
