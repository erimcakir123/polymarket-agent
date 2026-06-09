"""Wikipedia'dan tenis turnuvası zemini çözer (ücretsiz API, anahtarsız)."""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

_API = "https://en.wikipedia.org/w/api.php"
_TIMEOUT = 10
_SURFACE_RE = re.compile(r"\|\s*surface\s*=\s*(.+)", re.IGNORECASE)
_SURFACES = ("Clay", "Grass", "Hard", "Carpet")


class WikipediaSurfaceClient:
    """resolve_surface(name) -> 'Clay'|'Grass'|'Hard' | None. I/O burada (infra)."""

    def __init__(
        self,
        http_get: Callable[..., Any] | None = None,
        timeout: int = _TIMEOUT,
    ) -> None:
        self._http = http_get or httpx.get
        self._timeout = timeout

    def resolve_surface(self, tournament_name: str) -> str | None:
        title = self._search(tournament_name)
        if not title:
            return None
        wikitext = self._fetch_section0(title)
        if not wikitext:
            return None
        return self._parse_surface(wikitext)

    def _search(self, name: str) -> str | None:
        data = self._get(
            {
                "action": "query",
                "list": "search",
                "format": "json",
                "srsearch": f"{name} tennis tournament",
                "srlimit": "1",
            }
        )
        hits = (((data or {}).get("query") or {}).get("search") or [])
        return hits[0]["title"] if hits else None

    def _fetch_section0(self, title: str) -> str | None:
        data = self._get(
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "rvsection": "0",
                "format": "json",
                "titles": title,
            }
        )
        for p in (((data or {}).get("query") or {}).get("pages") or {}).values():
            revs = p.get("revisions") or []
            if revs:
                return revs[0].get("slots", {}).get("main", {}).get("*")
        return None

    def _parse_surface(self, wikitext: str) -> str | None:
        m = _SURFACE_RE.search(wikitext)
        if not m:
            return None
        line = m.group(1).lower()
        for s in _SURFACES:
            if s.lower() in line:
                return "Hard" if s == "Carpet" else s
        return None

    def _get(self, params: dict) -> dict | None:
        try:
            resp = self._http(_API, params=params, timeout=self._timeout)
            if getattr(resp, "status_code", 0) >= 400:
                logger.warning("Wikipedia returned %s", resp.status_code)
                return None
            return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as e:
            logger.warning("Wikipedia fetch failed: %s", e)
            return None
        except Exception as e:
            logger.warning("Wikipedia unexpected error: %s", e)
            return None
