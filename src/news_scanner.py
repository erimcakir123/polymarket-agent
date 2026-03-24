"""Multi-source news scanner with article content extraction.

Fallback chain: Tavily → NewsAPI → GNews → RSS (unlimited).
Tavily is an LLM-optimized search API (1000 credits/month free).
Full article content extracted via trafilatura for deeper AI analysis.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

BREAKING_PATTERNS = re.compile(r"\b(BREAKING|URGENT|JUST IN|FLASH)\b", re.IGNORECASE)

RSS_FEEDS = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZ4ZERBU0FtVnVHZ0pWVXlnQVAB",
    "https://feeds.reuters.com/reuters/politicsNews",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
]

# Topic templates for grouping related markets
TOPIC_GROUPS: Dict[str, List[str]] = {
    "us_politics": ["trump", "biden", "congress", "senate", "house", "republican", "democrat", "election", "president"],
    "geopolitics": ["ukraine", "russia", "china", "taiwan", "nato", "war", "sanctions", "iran", "israel", "gaza"],
    "economics": ["fed", "interest rate", "inflation", "gdp", "recession", "tariff", "trade war", "stock market", "s&p"],
    "crypto": ["bitcoin", "ethereum", "crypto", "sec crypto", "etf"],
    "tech": ["ai regulation", "openai", "google ai", "meta ai", "tiktok ban", "antitrust"],
}


def _cache_key(query: str) -> str:
    """Stable cache key from query string."""
    return hashlib.md5(query.encode()).hexdigest()


class NewsScanner:
    """Multi-source news fetcher with intelligent caching and content extraction."""

    def __init__(
        self,
        newsapi_key: Optional[str] = None,
        gnews_key: Optional[str] = None,
        tavily_key: Optional[str] = None,
        rss_feeds: Optional[List[str]] = None,
        cache_ttl: float = 2700,  # 45 min
    ) -> None:
        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY", "")
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY", "")
        self.gnews_key = gnews_key or os.getenv("GNEWS_KEY", "")
        self.rss_feeds = rss_feeds or RSS_FEEDS

        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[float, List[dict]]] = {}
        self._daily_usage: Dict[str, int] = {"newsapi": 0, "gnews": 0, "tavily": 0}
        self._monthly_tavily: int = 0
        self._tavily_month: str = ""
        self._usage_reset_day: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_news(self, query: str, max_results: int = 5) -> List[dict]:
        """Search for news articles using the fallback chain.

        Returns list of dicts with keys:
            title, link, published, summary, source, content (extracted), is_breaking
        """
        self._maybe_reset_daily_usage()

        # Check cache
        key = _cache_key(query)
        if key in self._cache:
            ts, cached = self._cache[key]
            if (time.time() - ts) < self.cache_ttl:
                logger.debug("Cache hit for query: %s", query)
                return cached

        # Fallback chain: Tavily → NewsAPI → GNews → RSS
        articles: List[dict] = []

        if not articles and self.tavily_key and self._monthly_tavily < 950:
            articles = self._fetch_tavily(query, max_results)

        if not articles and self.newsapi_key and self._daily_usage["newsapi"] < 95:
            articles = self._fetch_newsapi(query, max_results)

        if not articles and self.gnews_key and self._daily_usage["gnews"] < 95:
            articles = self._fetch_gnews(query, max_results)

        if not articles:
            articles = self._fetch_rss(query, max_results)

        # Extract full content for top articles
        for article in articles[:3]:
            if article.get("link") and not article.get("content"):
                article["content"] = self._extract_content(article["link"])

        # Mark breaking news
        for article in articles:
            article["is_breaking"] = bool(BREAKING_PATTERNS.search(article.get("title", "")))

        # Cache results
        self._cache[key] = (time.time(), articles)
        return articles

    def search_for_markets(
        self,
        market_keywords: Dict[str, List[str]],
        max_results_per_topic: int = 5,
    ) -> Dict[str, List[dict]]:
        """Group markets by topic, search once per topic, distribute results.

        market_keywords: {condition_id: [keyword1, keyword2, ...]}
        Returns: {condition_id: [articles]}
        """
        # Group markets into topics to reduce API calls
        topic_markets = self._group_markets_by_topic(market_keywords)

        # Search once per topic
        topic_results: Dict[str, List[dict]] = {}
        for topic_query, _market_ids in topic_markets.items():
            topic_results[topic_query] = self.search_news(topic_query, max_results_per_topic)

        # Distribute results back to individual markets
        results: Dict[str, List[dict]] = {}
        for topic_query, market_ids in topic_markets.items():
            articles = topic_results.get(topic_query, [])
            for cid in market_ids:
                keywords = market_keywords[cid]
                # Filter articles relevant to this specific market
                relevant = []
                for a in articles:
                    text = (a.get("title", "") + " " + a.get("summary", "")).lower()
                    if any(kw.lower() in text for kw in keywords):
                        relevant.append(a)
                results[cid] = relevant if relevant else articles[:2]

        return results

    def build_news_context(self, articles: List[dict], max_articles: int = 5) -> str:
        """Build a text context string for AI analysis from articles."""
        if not articles:
            return ""
        lines = []
        for a in articles[:max_articles]:
            line = f"- **{a['title']}**"
            if a.get("content"):
                # First 300 chars of extracted content
                snippet = a["content"][:300].replace("\n", " ").strip()
                line += f"\n  {snippet}"
            elif a.get("summary"):
                line += f"\n  {a['summary'][:200]}"
            if a.get("is_breaking"):
                line = "🔴 BREAKING " + line
            lines.append(line)
        return "\n".join(lines)

    def invalidate_cache(self, query: str) -> None:
        """Force cache invalidation for a query (e.g., on price movement)."""
        key = _cache_key(query)
        self._cache.pop(key, None)

    # ------------------------------------------------------------------
    # Tier 0: Tavily (LLM-optimized search, 1000 credits/month free)
    # ------------------------------------------------------------------

    def _fetch_tavily(self, query: str, max_results: int) -> List[dict]:
        """Fetch from Tavily Search API (1000 credits/month free)."""
        self._maybe_reset_tavily_monthly()
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",  # 1 credit per basic search
                    "include_answer": False,
                },
                timeout=15,
            )

            if resp.status_code == 429:
                logger.warning("Tavily rate limited, falling back")
                return []
            if resp.status_code == 401:
                logger.warning("Tavily API key invalid — disabling")
                self.tavily_key = ""
                return []
            resp.raise_for_status()

            self._monthly_tavily += 1  # Count only successful API calls
            data = resp.json()
            articles = []
            for item in data.get("results", [])[:max_results]:
                articles.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "published": "",
                    "summary": (item.get("content") or "")[:200],
                    "source": f"tavily:{item.get('url', '').split('/')[2] if '/' in item.get('url', '') else 'unknown'}",
                    "content": (item.get("content") or "")[:1500],
                })
            logger.info("Tavily returned %d articles for '%s' (monthly usage: %d/1000)",
                        len(articles), query, self._monthly_tavily)
            return articles

        except Exception as e:
            logger.warning("Tavily error: %s", e)
            return []

    def _maybe_reset_tavily_monthly(self) -> None:
        """Reset Tavily monthly counter on month change."""
        month = time.strftime("%Y-%m")
        if self._tavily_month != month:
            self._monthly_tavily = 0
            self._tavily_month = month

    # ------------------------------------------------------------------
    # Tier 1: NewsAPI
    # ------------------------------------------------------------------

    def _fetch_newsapi(self, query: str, max_results: int) -> List[dict]:
        """Fetch from NewsAPI.org (100 req/day free)."""
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "sortBy": "publishedAt",
                    "pageSize": max_results,
                    "language": "en",
                },
                headers={"X-Api-Key": self.newsapi_key},
                timeout=10,
            )
            self._daily_usage["newsapi"] += 1

            if resp.status_code == 429:
                logger.warning("NewsAPI rate limited, falling back")
                return []
            resp.raise_for_status()

            data = resp.json()
            articles = []
            for item in data.get("articles", [])[:max_results]:
                articles.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "published": item.get("publishedAt", ""),
                    "summary": (item.get("description") or "")[:200],
                    "source": f"newsapi:{item.get('source', {}).get('name', 'unknown')}",
                    "content": "",
                })
            logger.info("NewsAPI returned %d articles for '%s' (usage: %d/100)",
                        len(articles), query, self._daily_usage["newsapi"])
            return articles

        except Exception as e:
            logger.warning("NewsAPI error: %s", e)
            return []

    # ------------------------------------------------------------------
    # Tier 2: GNews
    # ------------------------------------------------------------------

    def _fetch_gnews(self, query: str, max_results: int) -> List[dict]:
        """Fetch from GNews.io (100 req/day free)."""
        try:
            resp = requests.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q": query,
                    "max": max_results,
                    "lang": "en",
                    "token": self.gnews_key,
                },
                timeout=10,
            )
            self._daily_usage["gnews"] += 1

            if resp.status_code == 429:
                logger.warning("GNews rate limited, falling back")
                return []
            resp.raise_for_status()

            data = resp.json()
            articles = []
            for item in data.get("articles", [])[:max_results]:
                articles.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "published": item.get("publishedAt", ""),
                    "summary": (item.get("description") or "")[:200],
                    "source": f"gnews:{item.get('source', {}).get('name', 'unknown')}",
                    "content": (item.get("content") or "")[:500],
                })
            logger.info("GNews returned %d articles for '%s' (usage: %d/100)",
                        len(articles), query, self._daily_usage["gnews"])
            return articles

        except Exception as e:
            logger.warning("GNews error: %s", e)
            return []

    # ------------------------------------------------------------------
    # Tier 3: RSS (unlimited)
    # ------------------------------------------------------------------

    def _fetch_rss(self, query: str, max_results: int) -> List[dict]:
        """Fetch from RSS feeds and filter by query keywords."""
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed, skipping RSS")
            return []

        query_words = query.lower().split()
        articles: List[dict] = []

        for url in self.rss_feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")[:200]
                    text = (title + " " + summary).lower()

                    if any(w in text for w in query_words):
                        articles.append({
                            "title": title,
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "summary": summary,
                            "source": f"rss:{url.split('/')[2]}",
                            "content": "",
                        })
            except Exception as e:
                logger.warning("RSS feed error %s: %s", url, e)

        logger.info("RSS returned %d articles for '%s'", len(articles[:max_results]), query)
        return articles[:max_results]

    # ------------------------------------------------------------------
    # Content extraction
    # ------------------------------------------------------------------

    def _extract_content(self, url: str) -> str:
        """Extract article content from URL using trafilatura."""
        try:
            import trafilatura
        except ImportError:
            logger.debug("trafilatura not installed, skipping content extraction")
            return ""

        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return ""
            text = trafilatura.extract(downloaded) or ""
            # Limit to first 1500 chars for AI context efficiency
            return text[:1500]
        except Exception as e:
            logger.debug("Content extraction failed for %s: %s", url, e)
            return ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _group_markets_by_topic(
        self, market_keywords: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Group markets into topic queries to reduce API calls.

        Example: 20 markets → 5-15 unique topic queries.
        """
        topic_map: Dict[str, List[str]] = {}

        for cid, keywords in market_keywords.items():
            # Try to match to a known topic group
            matched = False
            for _topic_name, topic_keywords in TOPIC_GROUPS.items():
                if any(kw.lower() in topic_keywords for kw in keywords):
                    # Use the first 2-3 market keywords as query
                    query = " ".join(keywords[:3])
                    topic_map.setdefault(query, []).append(cid)
                    matched = True
                    break

            if not matched:
                # Use market's own keywords as a standalone query
                query = " ".join(keywords[:3])
                topic_map.setdefault(query, []).append(cid)

        return topic_map

    def _maybe_reset_daily_usage(self) -> None:
        """Reset daily usage counters at midnight."""
        today = time.strftime("%Y-%m-%d")
        if self._usage_reset_day != today:
            self._daily_usage = {"newsapi": 0, "gnews": 0, "tavily": 0}
            self._usage_reset_day = today

