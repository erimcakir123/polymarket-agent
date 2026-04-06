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
from src.matching.polymarket_teams import PolymarketTeamsCache

logger = logging.getLogger(__name__)

# Module-level singletons (created on first call)
_resolver: Optional[TeamResolver] = None
_teams_cache: Optional[PolymarketTeamsCache] = None


def _get_resolver(cache_dir: Optional[Path] = None) -> TeamResolver:
    global _resolver
    if _resolver is None:
        cache_path = (cache_dir / "team_resolver_cache.json") if cache_dir else None
        _resolver = TeamResolver(cache_path=cache_path, auto_refresh=cache_dir is None)
    return _resolver


def _get_teams_cache() -> PolymarketTeamsCache:
    global _teams_cache
    if _teams_cache is None:
        _teams_cache = PolymarketTeamsCache()
    return _teams_cache


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
    # Refresh Polymarket teams cache daily (free API, no auth needed)
    _get_teams_cache().refresh_if_stale()
    matched = []
    used_keys: set[str] = set()

    # Diagnostics: track WHY markets fail to match, so we can improve the matcher.
    # Buckets: no_scout_entries_for_sport, sport_incompatible_only, below_threshold,
    #          no_candidates (sport compatible but nothing resembling match).
    _diag: dict[str, int] = {
        "matched": 0,
        "below_threshold": 0,
        "no_candidates": 0,
        "no_teams_in_slug": 0,
    }
    _unmatched_samples: list[str] = []  # Up to 10 slugs with best_confidence < 0.60

    for market in markets:
        slug = (getattr(market, "slug", "") or "").lower()
        question = (getattr(market, "question", "") or "").lower()
        market_sport = classify_sport(market)
        slug_parts = parse_slug(slug)
        slug_tokens = extract_slug_tokens(slug)

        # ── Layer 0: Polymarket /teams abbreviation lookup (deterministic) ──
        # Resolve slug tokens via Polymarket's own /teams endpoint scoped by
        # league to prevent cross-league collisions (e.g. "atl" = Hawks in NBA
        # vs Atletico in soccer). Uses sport from slug parser or market.sport_tag.
        teams = _get_teams_cache()
        layer0_matched = False
        # Determine league for scoped resolution: slug parser sport or market sport_tag
        _league = slug_parts.sport or (getattr(market, "sport_tag", "") or "").split("-")[0]
        if len(slug_parts.team_tokens) >= 2:
            t0_name = teams.resolve(slug_parts.team_tokens[0], _league)
            t1_name = teams.resolve(slug_parts.team_tokens[1], _league)
            if t0_name and t1_name:
                t0_low = normalize(t0_name)
                t1_low = normalize(t1_name)
                for key, entry in scout_queue.items():
                    if entry.get("entered") or key in used_keys:
                        continue
                    ea = normalize(entry.get("team_a") or "")
                    eb = normalize(entry.get("team_b") or "")
                    if not ea or not eb:
                        continue
                    # Bidirectional containment: "/teams" may return longer
                    # names ("Udinese Calcio") while scout has shorter ("Udinese"),
                    # or vice versa. Check both directions for each team.
                    t0_hit = (t0_low in ea or ea in t0_low or
                              t0_low in eb or eb in t0_low)
                    t1_hit = (t1_low in ea or ea in t1_low or
                              t1_low in eb or eb in t1_low)
                    if t0_hit and t1_hit:
                        entry_copy = dict(entry)
                        entry_copy["matched"] = True
                        entry_copy["match_confidence"] = 1.0
                        matched.append({
                            "market": market,
                            "scout_entry": entry_copy,
                            "scout_key": key,
                        })
                        used_keys.add(key)
                        _diag["matched"] += 1
                        logger.debug("L0 matched [1.00]: %s -> %s vs %s (via /teams)",
                                     slug[:40], t0_name, t1_name)
                        layer0_matched = True
                        break
        if layer0_matched:
            continue  # Skip fuzzy layers for this market

        # Resolve slug abbreviations to names (fuzzy fallback layers)
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
            _diag["matched"] += 1
            logger.debug("Matched [%.2f]: %s -> %s vs %s",
                         best_confidence, slug[:40],
                         best_match.get("team_a", ""),
                         best_match.get("team_b", ""))
        else:
            # Classify failure for diagnostics
            if not slug_parts.team_tokens:
                _diag["no_teams_in_slug"] += 1
            elif best_confidence > 0.0:
                _diag["below_threshold"] += 1
                if len(_unmatched_samples) < 10 and best_match:
                    _unmatched_samples.append(
                        f"[{best_confidence:.2f}] {slug[:50]} -> closest: "
                        f"{best_match.get('team_a', '')} vs {best_match.get('team_b', '')}"
                    )
            else:
                _diag["no_candidates"] += 1
                if len(_unmatched_samples) < 10:
                    _unmatched_samples.append(f"[0.00] {slug[:50]} (no scout candidate)")

    if matched:
        logger.info("matching: %d/%d markets matched", len(matched), len(markets))
    # Full diagnostics breakdown so we can see WHERE matches are lost.
    _total_unmatched = len(markets) - _diag["matched"]
    if _total_unmatched > 0:
        logger.info(
            "matcher diag: below_thresh=%d | no_candidates=%d | no_teams_in_slug=%d",
            _diag["below_threshold"], _diag["no_candidates"], _diag["no_teams_in_slug"],
        )
        for sample in _unmatched_samples[:5]:
            logger.info("  unmatched sample: %s", sample)

    return matched
