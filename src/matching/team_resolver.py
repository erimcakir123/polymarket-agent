"""Resolve team abbreviations and aliases to canonical names.

Data sources (priority order):
1. Polymarket GET /teams — abbreviation + alias
2. ESPN /teams — abbreviation + shortDisplayName
3. PandaScore /teams — acronym
4. Static fallback — hardcoded common abbreviations/nicknames
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_STRIP_SUFFIXES = (" fc", " sc", " esports", " gaming", " clan", " team")


def normalize(name: str) -> str:
    """Lowercase, strip whitespace and common suffixes."""
    name = name.lower().strip()
    for suffix in _STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


# Combined static data from old STATIC_ABBREVS + TEAM_ALIASES
_STATIC_ABBREVS: dict[str, str] = {
    # NBA
    "lal": "los angeles lakers", "bos": "boston celtics",
    "gsw": "golden state warriors", "bkn": "brooklyn nets",
    "nyk": "new york knicks", "phi": "philadelphia 76ers",
    "mil": "milwaukee bucks", "mia": "miami heat",
    "chi": "chicago bulls", "phx": "phoenix suns",
    "dal": "dallas mavericks", "den": "denver nuggets",
    "min": "minnesota timberwolves", "okc": "oklahoma city thunder",
    "cle": "cleveland cavaliers", "lac": "la clippers",
    "hou": "houston rockets", "mem": "memphis grizzlies",
    "nop": "new orleans pelicans", "atl": "atlanta hawks",
    "ind": "indiana pacers", "orl": "orlando magic",
    "tor": "toronto raptors", "wsh": "washington wizards",
    "det": "detroit pistons", "cha": "charlotte hornets",
    "sac": "sacramento kings", "por": "portland trail blazers",
    "uta": "utah jazz", "sas": "san antonio spurs",
    # NFL
    "kc": "kansas city chiefs", "buf": "buffalo bills",
    "bal": "baltimore ravens", "sf": "san francisco 49ers",
    "gb": "green bay packers", "tb": "tampa bay buccaneers",
    "ne": "new england patriots", "sea": "seattle seahawks",
    "pit": "pittsburgh steelers", "cin": "cincinnati bengals",
    "jax": "jacksonville jaguars", "ten": "tennessee titans",
    "lar": "los angeles rams", "nyg": "new york giants",
    "nyj": "new york jets", "car": "carolina panthers",
    "no": "new orleans saints", "lv": "las vegas raiders",
    "ari": "arizona cardinals",
    # MLB
    "nyy": "new york yankees", "lad": "los angeles dodgers",
    "nym": "new york mets", "chc": "chicago cubs",
    "cws": "chicago white sox", "sd": "san diego padres",
    "tex": "texas rangers", "stl": "st. louis cardinals",
    # NHL
    "mtl": "montreal canadiens", "nyr": "new york rangers",
    "edm": "edmonton oilers", "cgy": "calgary flames",
    "van": "vancouver canucks", "col": "colorado avalanche",
    # Esports
    "fnc": "fnatic", "tl": "team liquid", "g2": "g2 esports",
    "c9": "cloud9", "t1": "t1", "geng": "gen.g", "drx": "drx",
    "sen": "sentinels", "100t": "100 thieves", "eg": "evil geniuses",
    "navi": "natus vincere", "faze": "faze clan", "vit": "team vitality",
    "spirit": "team spirit", "mouz": "mouz", "hero": "heroic",
    "loud": "loud", "furia": "furia", "mibr": "mibr",
    "blg": "bilibili gaming", "tes": "top esports", "jdg": "jd gaming",
    "weibo": "weibo gaming", "lng": "lng esports",
    "rng": "royal never give up", "edg": "edward gaming",
    "fpx": "funplus phoenix",
}

_STATIC_ALIASES: dict[str, str] = {
    # Nicknames -> canonical
    "lakers": "los angeles lakers", "celtics": "boston celtics",
    "warriors": "golden state warriors", "bucks": "milwaukee bucks",
    "sixers": "philadelphia 76ers", "76ers": "philadelphia 76ers",
    "knicks": "new york knicks", "nets": "brooklyn nets",
    "heat": "miami heat", "nuggets": "denver nuggets",
    "suns": "phoenix suns", "mavs": "dallas mavericks",
    "thunder": "oklahoma city thunder", "wolves": "minnesota timberwolves",
    "cavs": "cleveland cavaliers", "clips": "la clippers",
    "rockets": "houston rockets", "grizzlies": "memphis grizzlies",
    "pelicans": "new orleans pelicans", "hawks": "atlanta hawks",
    "bulls": "chicago bulls", "pacers": "indiana pacers",
    "magic": "orlando magic", "raptors": "toronto raptors",
    "hornets": "charlotte hornets", "kings": "sacramento kings",
    "blazers": "portland trail blazers", "jazz": "utah jazz",
    "spurs": "san antonio spurs",
    # Soccer
    "man utd": "manchester united", "man city": "manchester city",
    "liverpool": "liverpool fc", "chelsea": "chelsea fc",
    "arsenal": "arsenal fc", "tottenham": "tottenham hotspur",
    "barca": "fc barcelona", "bayern": "bayern munich",
    "psg": "paris saint-germain", "juve": "juventus",
    "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
    # Esports
    "na'vi": "natus vincere", "liquid": "team liquid",
    "vitality": "team vitality", "mousesports": "mouz",
    "complexity": "complexity gaming", "cloud9": "cloud9",
    # NHL
    "leafs": "toronto maple leafs", "habs": "montreal canadiens",
    "bruins": "boston bruins", "rangers": "new york rangers",
    "pens": "pittsburgh penguins", "caps": "washington capitals",
    "oilers": "edmonton oilers", "flames": "calgary flames",
    "avs": "colorado avalanche",
    # NFL
    "chiefs": "kansas city chiefs", "eagles": "philadelphia eagles",
    "niners": "san francisco 49ers", "cowboys": "dallas cowboys",
    "bills": "buffalo bills", "ravens": "baltimore ravens",
    "steelers": "pittsburgh steelers", "packers": "green bay packers",
    # MLB
    "yankees": "new york yankees", "dodgers": "los angeles dodgers",
    "red sox": "boston red sox", "mets": "new york mets",
    "astros": "houston astros", "braves": "atlanta braves",
    "cubs": "chicago cubs", "phillies": "philadelphia phillies",
    # Tennis
    "djokovic": "novak djokovic", "sinner": "jannik sinner",
    "alcaraz": "carlos alcaraz", "medvedev": "daniil medvedev",
}


class TeamResolver:
    """Resolve abbreviations/aliases to canonical team names.

    Single source of truth replacing old AliasStore + TEAM_ALIASES.
    """

    def __init__(self, cache_path: Path | None = None, auto_refresh: bool = True):
        self._cache_path = cache_path or Path("logs/team_resolver_cache.json")
        self._abbrevs: dict[str, str] = {}   # abbreviation -> canonical
        self._aliases: dict[str, str] = {}    # alias/nickname -> canonical
        self._lock = threading.Lock()

        # Load from cache or static
        if not self._load_cache():
            self._abbrevs = dict(_STATIC_ABBREVS)
            self._aliases = dict(_STATIC_ALIASES)

        if auto_refresh:
            t = threading.Thread(target=self._background_refresh, daemon=True)
            t.start()

    def resolve(self, token: str) -> Optional[str]:
        """Resolve a token (abbreviation, alias, or name) to canonical name.

        Returns canonical lowercase name, or None if unknown.
        """
        key = token.lower().strip()
        with self._lock:
            # 1. Direct abbreviation
            if key in self._abbrevs:
                return self._abbrevs[key]
            # 2. Alias/nickname
            if key in self._aliases:
                return self._aliases[key]
        return None

    def _load_cache(self) -> bool:
        try:
            if not self._cache_path.exists():
                return False
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            abbrevs = data.get("abbrevs", {})
            aliases = data.get("aliases", {})
            if not abbrevs:
                return False
            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in abbrevs.items()}
                self._aliases = {k.lower(): v.lower() for k, v in aliases.items()}
            logger.info("TeamResolver: loaded %d abbrevs + %d aliases from cache",
                        len(self._abbrevs), len(self._aliases))
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("TeamResolver: cache load failed: %s", e)
            return False

    def _save_cache(self):
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = {"abbrevs": dict(self._abbrevs), "aliases": dict(self._aliases)}
            self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("TeamResolver: cache save failed: %s", e)

    def _background_refresh(self):
        """Refresh from APIs in background thread."""
        try:
            new_abbrevs: dict[str, str] = {}
            new_aliases: dict[str, str] = {}

            self._fetch_polymarket_teams(new_abbrevs, new_aliases)
            self._fetch_espn_teams(new_abbrevs)
            self._fetch_pandascore_teams(new_abbrevs)

            # Static codes LAST so they override API data for major leagues
            new_abbrevs.update(_STATIC_ABBREVS)
            new_aliases.update(_STATIC_ALIASES)

            with self._lock:
                self._abbrevs = {k.lower(): v.lower() for k, v in new_abbrevs.items()}
                self._aliases = {k.lower(): v.lower() for k, v in new_aliases.items()}
            self._save_cache()
            logger.info("TeamResolver: refresh complete — %d abbrevs, %d aliases",
                        len(self._abbrevs), len(self._aliases))
        except Exception as e:
            logger.warning("TeamResolver: refresh failed: %s", e)

    def _fetch_polymarket_teams(self, abbrevs: dict, aliases: dict):
        """Polymarket GET /teams — GOLD STANDARD for abbreviations.

        API max limit is 500 per page, so we paginate until exhausted.
        """
        try:
            total = 0
            offset = 0
            while True:
                resp = requests.get(
                    "https://gamma-api.polymarket.com/teams",
                    params={"limit": 500, "offset": offset},
                    timeout=15,
                )
                if resp.status_code != 200:
                    break
                teams = resp.json()
                if not isinstance(teams, list) or not teams:
                    break
                for team in teams:
                    abbr = (team.get("abbreviation") or "").strip()
                    name = (team.get("name") or "").strip()
                    alias = (team.get("alias") or "").strip()
                    if abbr and name and len(abbr) >= 2:
                        abbrevs[abbr.lower()] = name.lower()
                    if alias and name:
                        aliases[alias.lower()] = name.lower()
                total += len(teams)
                if len(teams) < 500:
                    break
                offset += 500
                time.sleep(0.2)
            logger.info("TeamResolver: Polymarket — %d teams fetched", total)
        except Exception as e:
            logger.debug("TeamResolver: Polymarket fetch failed: %s", e)

    def _fetch_espn_teams(self, abbrevs: dict):
        """ESPN /teams — abbreviation + shortDisplayName."""
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
        """PandaScore /teams — acronym."""
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
