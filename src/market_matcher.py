"""Market matcher — bridges Polymarket markets to ESPN/PandaScore scout entries.

Drop-in replacement for scout_scheduler.match_markets_batch().
Uses 3-layer matching: exact abbreviation -> normalized short name -> fuzzy.
AliasStore caches team abbreviation lookups to logs/alias_cache.json.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from rapidfuzz import fuzz

from src.team_matcher import _normalize, TEAM_ALIASES

logger = logging.getLogger(__name__)

ALIAS_CACHE_PATH = Path("logs/alias_cache.json")
CACHE_TTL_HOURS = 24

# ---------------------------------------------------------------------------
# Static abbreviation fallback (all keys lowercase)
# ---------------------------------------------------------------------------
STATIC_ABBREVS: dict[str, str] = {
    # NBA
    "lal": "los angeles lakers", "bos": "boston celtics", "gsw": "golden state warriors",
    "bkn": "brooklyn nets", "nyk": "new york knicks", "phi": "philadelphia 76ers",
    "mil": "milwaukee bucks", "mia": "miami heat", "chi": "chicago bulls",
    "phx": "phoenix suns", "dal": "dallas mavericks", "den": "denver nuggets",
    "min": "minnesota timberwolves", "okc": "oklahoma city thunder",
    "cle": "cleveland cavaliers", "lac": "la clippers", "hou": "houston rockets",
    "mem": "memphis grizzlies", "nop": "new orleans pelicans", "atl": "atlanta hawks",
    "ind": "indiana pacers", "orl": "orlando magic", "tor": "toronto raptors",
    "wsh": "washington wizards", "det": "detroit pistons", "cha": "charlotte hornets",
    "sac": "sacramento kings", "por": "portland trail blazers", "uta": "utah jazz",
    "sas": "san antonio spurs",
    # NFL
    "kc": "kansas city chiefs", "buf": "buffalo bills", "bal": "baltimore ravens",
    "sf": "san francisco 49ers", "gb": "green bay packers", "tb": "tampa bay buccaneers",
    "ne": "new england patriots", "sea": "seattle seahawks", "pit": "pittsburgh steelers",
    "cin": "cincinnati bengals", "jax": "jacksonville jaguars", "ten": "tennessee titans",
    "lar": "los angeles rams", "nyg": "new york giants", "nyj": "new york jets",
    "car": "carolina panthers", "no": "new orleans saints", "lv": "las vegas raiders",
    "ari": "arizona cardinals",
    # MLB
    "nyy": "new york yankees", "lad": "los angeles dodgers", "nym": "new york mets",
    "chc": "chicago cubs", "cws": "chicago white sox", "sd": "san diego padres",
    "tex": "texas rangers", "stl": "st. louis cardinals",
    # NHL
    "mtl": "montreal canadiens", "nyr": "new york rangers",
    "edm": "edmonton oilers", "cgy": "calgary flames", "van": "vancouver canucks",
    "col": "colorado avalanche",
    # Esports
    "fnc": "fnatic", "tl": "team liquid", "g2": "g2 esports", "c9": "cloud9",
    "t1": "t1", "geng": "gen.g", "drx": "drx", "sen": "sentinels",
    "100t": "100 thieves", "eg": "evil geniuses", "navi": "natus vincere",
    "faze": "faze clan", "vit": "team vitality", "spirit": "team spirit",
    "mouz": "mouz", "hero": "heroic", "loud": "loud", "furia": "furia",
    "mibr": "mibr", "blg": "bilibili gaming", "tes": "top esports",
    "jdg": "jd gaming", "weibo": "weibo gaming", "lng": "lng esports",
    "rng": "royal never give up", "edg": "edward gaming", "fpx": "funplus phoenix",
}


class AliasStore:
    """Team abbreviation -> canonical name lookup.

    Loads from logs/alias_cache.json on init (instant).
    Refreshes from APIs in background thread every 24h.
    Falls back to STATIC_ABBREVS if cache missing/corrupted.
    """

    def __init__(self, cache_path: Path = ALIAS_CACHE_PATH, auto_refresh: bool = True):
        self._cache_path = cache_path
        self._abbrevs: dict[str, str] = {}
        self._lock = threading.Lock()

        if not self._load_cache():
            self._abbrevs = dict(STATIC_ABBREVS)

        if auto_refresh:
            t = threading.Thread(target=self._background_refresh, daemon=True)
            t.start()

    def resolve(self, abbreviation: str) -> str:
        """Resolve abbreviation to canonical name. Returns input lowered if not found."""
        key = abbreviation.lower().strip()
        with self._lock:
            return self._abbrevs.get(key, key)

    def has(self, abbreviation: str) -> bool:
        key = abbreviation.lower().strip()
        with self._lock:
            return key in self._abbrevs

    def _load_cache(self) -> bool:
        """Load from JSON cache. Returns True if successful."""
        try:
            if not self._cache_path.exists():
                return False
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            abbrevs = data.get("abbrevs", {})
            if not abbrevs:
                return False
            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in abbrevs.items()}
            logger.info("AliasStore: loaded %d abbreviations from cache", len(self._abbrevs))
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("AliasStore: cache load failed (%s), using static fallback", e)
            return False

    def _save_cache(self):
        """Persist to JSON."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = {
                    "_meta": {"updated_at": datetime.now(timezone.utc).isoformat()},
                    "abbrevs": dict(self._abbrevs),
                }
            self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("AliasStore: cache save failed: %s", e)

    def _background_refresh(self):
        """Refresh from 3 APIs in background thread."""
        try:
            new_abbrevs = dict(STATIC_ABBREVS)
            self._fetch_polymarket_teams(new_abbrevs)
            self._fetch_espn_teams(new_abbrevs)
            self._fetch_pandascore_teams(new_abbrevs)
            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in new_abbrevs.items()}
            self._save_cache()
            logger.info("AliasStore: background refresh complete — %d abbreviations", len(self._abbrevs))
        except Exception as e:
            logger.warning("AliasStore: background refresh failed: %s", e)

    def _fetch_polymarket_teams(self, abbrevs: dict):
        """Fetch from Polymarket Gamma API /sports/teams."""
        try:
            resp = requests.get("https://gamma-api.polymarket.com/sports/teams", timeout=15)
            if resp.status_code != 200:
                return
            teams = resp.json()
            if isinstance(teams, list):
                for team in teams:
                    abbr = (team.get("abbreviation") or "").strip()
                    name = (team.get("name") or "").strip()
                    if abbr and name and len(abbr) >= 2:
                        abbrevs[abbr.lower()] = name.lower()
                    alias = (team.get("alias") or "").strip()
                    if alias and name:
                        abbrevs[alias.lower()] = name.lower()
        except Exception as e:
            logger.debug("Polymarket teams fetch failed: %s", e)

    def _fetch_espn_teams(self, abbrevs: dict):
        """Fetch from ESPN /teams endpoints."""
        from src.scout_scheduler import _SCOUT_LEAGUES
        for sport, league, _ in _SCOUT_LEAGUES:
            if sport in ("tennis", "golf", "mma"):
                continue
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for sport_data in data.get("sports", []):
                    for league_data in sport_data.get("leagues", []):
                        for team_entry in league_data.get("teams", []):
                            t = team_entry.get("team", {})
                            abbr = (t.get("abbreviation") or "").strip()
                            display = (t.get("displayName") or "").strip()
                            short = (t.get("shortDisplayName") or "").strip()
                            if abbr and display:
                                abbrevs[abbr.lower()] = display.lower()
                            if short and display:
                                abbrevs[short.lower()] = display.lower()
                time.sleep(0.3)
            except Exception:
                pass

    def _fetch_pandascore_teams(self, abbrevs: dict):
        """Fetch from PandaScore /teams endpoints."""
        api_key = os.getenv("PANDASCORE_API_KEY", "")
        if not api_key:
            return
        for game in ["csgo", "lol", "dota2", "valorant"]:
            try:
                resp = requests.get(
                    f"https://api.pandascore.co/{game}/teams",
                    params={"page[size]": 100, "page[number]": 1},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                for team in resp.json():
                    acronym = (team.get("acronym") or "").strip()
                    name = (team.get("name") or "").strip()
                    if acronym and name:
                        abbrevs[acronym.lower()] = name.lower()
                time.sleep(0.5)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Sport context detection
# ---------------------------------------------------------------------------

_SLUG_SPORT_HINTS = {
    "nba": "basketball", "wnba": "basketball", "cbb": "basketball",
    "nfl": "football", "cfb": "football",
    "mlb": "baseball", "nhl": "hockey",
    "soc": "soccer", "epl": "soccer", "ucl": "soccer",
    "ufc": "mma", "mma": "mma",
    "ten": "tennis", "atp": "tennis", "wta": "tennis",
    "gol": "golf", "pga": "golf",
    "cs": "esports", "csgo": "esports", "cs2": "esports",
    "val": "esports", "lol": "esports", "dota": "esports",
}

_TAG_SPORT_HINTS = {
    "nba": "basketball", "nfl": "football", "mlb": "baseball",
    "nhl": "hockey", "mls": "soccer", "epl": "soccer",
    "premier league": "soccer", "la liga": "soccer",
    "champions league": "soccer", "bundesliga": "soccer",
    "serie a": "soccer", "ligue 1": "soccer",
    "ufc": "mma",
    "counter-strike": "esports", "csgo": "esports", "cs2": "esports",
    "valorant": "esports", "league-of-legends": "esports",
    "lol": "esports", "dota-2": "esports", "dota2": "esports",
}


def _detect_sport_context(market) -> Optional[str]:
    """Detect sport from market slug prefix or sport_tag."""
    slug = (getattr(market, "slug", "") or "").lower()
    sport_tag = (getattr(market, "sport_tag", "") or "").lower()
    prefix = slug.split("-")[0] if slug else ""
    if prefix in _SLUG_SPORT_HINTS:
        return _SLUG_SPORT_HINTS[prefix]
    if sport_tag in _TAG_SPORT_HINTS:
        return _TAG_SPORT_HINTS[sport_tag]
    slug_parts = set(slug.split("-"))
    for key, sport in _SLUG_SPORT_HINTS.items():
        if key in slug_parts:
            return sport
    return None


def _entry_sport(entry: dict) -> str:
    if entry.get("is_esports"):
        return "esports"
    return entry.get("sport", "")


def _sports_compatible(market_sport: Optional[str], entry_sport: str) -> bool:
    """Prevent cross-sport matches. Unknown -> allow."""
    if market_sport is None:
        return True
    if market_sport == "esports" and entry_sport == "esports":
        return True
    if market_sport == "esports" or entry_sport == "esports":
        return market_sport == entry_sport
    if market_sport and entry_sport:
        return market_sport == entry_sport
    return True


def _extract_slug_tokens(slug: str) -> set[str]:
    """Extract tokens from slug. 'nba-lal-bos-2026-04-05' -> {'nba', 'lal', 'bos'}"""
    return {p for p in slug.lower().split("-") if len(p) >= 2 and not p.isdigit()}


# ---------------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------------

def match_batch(markets: list, scout_queue: dict, alias_store: AliasStore) -> list[dict]:
    """Match Polymarket markets to scout entries. Drop-in replacement.

    3-layer matching:
        Layer 1: Exact abbreviation in slug tokens (confidence 1.0)
        Layer 2: Normalized short name in question/slug (confidence 0.9)
        Layer 3: Fuzzy rapidfuzz token_sort_ratio >= 80 (confidence 0.7-0.9)

    Returns: [{"market": m, "scout_entry": entry_copy, "scout_key": key}]
    Same format as scout_scheduler.match_markets_batch().
    """
    matched = []
    used_keys: set[str] = set()

    for market in markets:
        question = (getattr(market, "question", "") or "").lower()
        slug = (getattr(market, "slug", "") or "").lower()
        slug_tokens = _extract_slug_tokens(slug)
        market_sport = _detect_sport_context(market)

        best_match = None
        best_confidence = 0.0
        best_key = ""
        candidates: list[tuple[str, dict, float]] = []

        for key, entry in scout_queue.items():
            if entry.get("entered") or key in used_keys:
                continue

            # Sport context filter
            if not _sports_compatible(market_sport, _entry_sport(entry)):
                continue

            abbrev_a = (entry.get("abbrev_a") or "").lower()
            abbrev_b = (entry.get("abbrev_b") or "").lower()
            team_a = entry.get("team_a", "")
            team_b = entry.get("team_b", "")
            short_a = (entry.get("short_a") or "").lower()
            short_b = (entry.get("short_b") or "").lower()

            confidence = 0.0

            # Layer 1: Exact abbreviation in slug tokens
            if abbrev_a and abbrev_b and abbrev_a in slug_tokens and abbrev_b in slug_tokens:
                confidence = 1.0

            # Layer 2: Normalized short name in question/slug
            if confidence < 0.9:
                if short_a and short_b:
                    if (short_a in question or short_a in slug) and \
                       (short_b in question or short_b in slug):
                        confidence = max(confidence, 0.9)

                if confidence < 0.9:
                    norm_a = _normalize(team_a)
                    norm_b = _normalize(team_b)
                    if norm_a and norm_b:
                        if (norm_a in question or norm_a in slug) and \
                           (norm_b in question or norm_b in slug):
                            confidence = max(confidence, 0.85)

            # Layer 3: Fuzzy (rapidfuzz) — only if names >= 4 chars
            if confidence < 0.7:
                norm_a = _normalize(team_a)
                norm_b = _normalize(team_b)
                if len(norm_a) >= 4 and len(norm_b) >= 4:
                    resolved_a = alias_store.resolve(abbrev_a) if abbrev_a else norm_a
                    resolved_b = alias_store.resolve(abbrev_b) if abbrev_b else norm_b

                    score_a = max(
                        fuzz.token_sort_ratio(norm_a, question),
                        fuzz.partial_ratio(norm_a, question),
                        fuzz.token_sort_ratio(resolved_a, question) if resolved_a != norm_a else 0,
                    )
                    score_b = max(
                        fuzz.token_sort_ratio(norm_b, question),
                        fuzz.partial_ratio(norm_b, question),
                        fuzz.token_sort_ratio(resolved_b, question) if resolved_b != norm_b else 0,
                    )

                    if score_a >= 60 and score_b >= 60:
                        fuzzy_conf = min(score_a, score_b) / 100.0
                        if fuzzy_conf >= 0.70:
                            confidence = max(confidence, fuzzy_conf)

            if confidence > 0.0:
                candidates.append((key, entry, confidence))
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = entry
                best_key = key

        # Doubleheader check — same team pair, 2+ entries -> pick earliest
        if len(candidates) > 1 and best_match:
            team_pair = frozenset([
                best_match.get("team_a", "").lower(),
                best_match.get("team_b", "").lower(),
            ])
            same_pair = [
                (k, e, c) for k, e, c in candidates
                if frozenset([e.get("team_a", "").lower(), e.get("team_b", "").lower()]) == team_pair
            ]
            if len(same_pair) > 1:
                same_pair.sort(key=lambda x: x[1].get("match_time", ""))
                best_key, best_match, best_confidence = same_pair[0]

        # Threshold check
        if best_match and best_confidence >= 0.6:
            entry_copy = dict(best_match)
            entry_copy["matched"] = True
            entry_copy["match_confidence"] = best_confidence
            matched.append({
                "market": market,
                "scout_entry": entry_copy,
                "scout_key": best_key,
            })
            used_keys.add(best_key)
            logger.debug(
                "Matched [%.2f]: %s -> %s vs %s",
                best_confidence, slug[:40],
                best_match.get("team_a", ""), best_match.get("team_b", ""),
            )

    if matched:
        logger.info("market_matcher: %d/%d markets matched", len(matched), len(markets))

    return matched
