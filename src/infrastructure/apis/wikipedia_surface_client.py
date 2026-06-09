"""Wikipedia'dan tenis turnuvası zemini çözer (ücretsiz API, anahtarsız)."""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

_API = "https://en.wikipedia.org/w/api.php"
_TIMEOUT = 10
_HEADERS = {"User-Agent": "PolymarketAgent/2.0 (tennis surface lookup; erimcakir93@gmail.com)"}
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
        for title in self._search_titles(tournament_name):
            wikitext = self._fetch_section0(title)
            if wikitext:
                surf = self._parse_surface(wikitext)
                if surf:
                    return surf
        return None

    def _search_titles(self, name: str) -> list[str]:
        data = self._get(
            {
                "action": "query",
                "list": "search",
                "format": "json",
                "srsearch": f"{name} tennis tournament",
                "srlimit": "5",
            }
        )
        hits = (((data or {}).get("query") or {}).get("search") or [])
        name_tokens = set(re.sub(r"[^a-z0-9 ]", " ", name.lower()).split())
        titles = []
        for h in hits:
            title = h.get("title", "")
            ttoks = set(re.sub(r"[^a-z0-9 ]", " ", title.lower()).split())
            if name_tokens & ttoks:  # paylaşılan kelime şart (Lyon→'ATP Lyon Open' ✓, 'Open Sud de France' ✗)
                titles.append(title)
        return titles

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
        # Find which surface name appears first in the line (earliest position = current surface).
        first_pos: int | None = None
        first_surface: str | None = None
        for s in _SURFACES:
            pos = line.find(s.lower())
            if pos != -1 and (first_pos is None or pos < first_pos):
                first_pos = pos
                first_surface = s
        if first_surface is None:
            return None
        return "Hard" if first_surface == "Carpet" else first_surface

    def _get(self, params: dict) -> dict | None:
        try:
            resp = self._http(_API, params=params, headers=_HEADERS, timeout=self._timeout)
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
