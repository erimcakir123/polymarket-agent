"""Polymarket /teams cache — resolves slug abbreviations to team names.

Polymarket's GET /teams endpoint returns all registered teams (sports + esports)
with {id, name, abbreviation, alias, league}. The `abbreviation` field matches
the slug tokens used in market slugs (e.g. "nj" in "nhl-nj-mon-2026-04-05").

Usage:
    cache = PolymarketTeamsCache()
    cache.refresh_if_stale()  # fetches from API if >24h old
    name = cache.resolve("nj")  # → "Devils"

The cache persists to disk (logs/polymarket_teams_cache.json) so there's no
cold-start API call on bot restart. Refresh happens at most once per 24 hours.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GAMMA_TEAMS_URL = "https://gamma-api.polymarket.com/teams"
CACHE_FILE = Path("logs/polymarket_teams_cache.json")
REFRESH_INTERVAL = 24 * 3600  # 24 hours


class PolymarketTeamsCache:
    """Abbreviation → team name resolver backed by Polymarket /teams API."""

    def __init__(self) -> None:
        self._abbr_to_name: dict[str, str] = {}
        self._last_refresh: float = 0.0
        self._load_disk_cache()

    def resolve(self, abbreviation: str) -> Optional[str]:
        """Return team name for a slug abbreviation, or None if unknown."""
        if not abbreviation:
            return None
        return self._abbr_to_name.get(abbreviation.lower())

    def refresh_if_stale(self) -> None:
        """Fetch fresh teams from API if cache is older than REFRESH_INTERVAL."""
        if time.time() - self._last_refresh < REFRESH_INTERVAL:
            return
        self._fetch_all_teams()

    def _ingest_teams(self, teams: list[dict]) -> None:
        """Load a list of team dicts into the lookup table."""
        for team in teams:
            abbr = (team.get("abbreviation") or "").lower().strip()
            name = team.get("name") or team.get("alias") or ""
            if abbr and name:
                self._abbr_to_name[abbr] = name

    def _fetch_all_teams(self) -> None:
        """Paginate through /teams endpoint and ingest all teams."""
        all_teams: list[dict] = []
        offset = 0
        page_size = 500

        while True:
            try:
                resp = requests.get(
                    GAMMA_TEAMS_URL,
                    params={"limit": page_size, "offset": offset},
                    timeout=15,
                )
                resp.raise_for_status()
                page = resp.json()
            except Exception as exc:
                logger.warning("Polymarket /teams fetch failed (offset=%d): %s", offset, exc)
                break

            if not page:
                break
            all_teams.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        if all_teams:
            self._abbr_to_name.clear()
            self._ingest_teams(all_teams)
            self._last_refresh = time.time()
            self._save_disk_cache(all_teams)
            logger.info("Polymarket teams cache refreshed: %d teams, %d abbreviations",
                        len(all_teams), len(self._abbr_to_name))

    def _load_disk_cache(self) -> None:
        """Load previously saved cache from disk (survives bot restarts)."""
        try:
            if not CACHE_FILE.exists():
                return
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            teams = raw.get("teams", [])
            ts = raw.get("timestamp", 0)
            if teams:
                self._ingest_teams(teams)
                self._last_refresh = ts
                logger.info("Polymarket teams loaded from disk: %d abbreviations",
                            len(self._abbr_to_name))
        except Exception as exc:
            logger.debug("Could not load teams cache: %s", exc)

    def _save_disk_cache(self, teams: list[dict]) -> None:
        """Persist teams to disk for cold-start on next boot."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "teams": teams,
                "timestamp": time.time(),
                "count": len(teams),
            }), encoding="utf-8")
            tmp.replace(CACHE_FILE)
        except Exception as exc:
            logger.debug("Could not save teams cache: %s", exc)
