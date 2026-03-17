"""RSS headline fetcher and breaking news detection."""
from __future__ import annotations
import logging
import re
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZ4ZERBU0FtVnVHZ0pWVXlnQVAB",
    "https://feeds.reuters.com/reuters/politicsNews",
]

BREAKING_PATTERNS = re.compile(r"\b(BREAKING|URGENT|JUST IN|FLASH)\b", re.IGNORECASE)


class NewsScanner:
    def __init__(self, feeds: Optional[List[str]] = None) -> None:
        self.feeds = feeds or RSS_FEEDS
        self._cache: List[dict] = []
        self._last_fetch: float = 0
        self._cache_ttl: float = 1800  # 30 min

    def fetch_headlines(self, max_per_feed: int = 10) -> List[dict]:
        now = time.time()
        if self._cache and (now - self._last_fetch) < self._cache_ttl:
            return self._cache

        headlines: List[dict] = []
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed, skipping RSS")
            return []

        for url in self.feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_feed]:
                    headlines.append({
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": entry.get("summary", "")[:200],
                    })
            except Exception as e:
                logger.warning("Failed to fetch feed %s: %s", url, e)

        self._cache = headlines
        self._last_fetch = now
        return headlines

    def match_headlines(
        self,
        headlines: List[dict],
        market_keywords: Dict[str, List[str]],
    ) -> Dict[str, List[dict]]:
        matches: Dict[str, List[dict]] = {}
        for cid, keywords in market_keywords.items():
            for h in headlines:
                title_lower = h["title"].lower()
                if any(kw.lower() in title_lower for kw in keywords):
                    entry = {**h, "is_breaking": bool(BREAKING_PATTERNS.search(h["title"]))}
                    matches.setdefault(cid, []).append(entry)
        return matches

    def build_news_context(self, headlines: List[dict], max_headlines: int = 5) -> str:
        if not headlines:
            return ""
        lines = [f"- {h['title']}" for h in headlines[:max_headlines]]
        return "\n".join(lines)
