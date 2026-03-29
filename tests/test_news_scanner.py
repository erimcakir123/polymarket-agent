import pytest
from unittest.mock import patch, MagicMock


def test_search_for_markets_matches():
    """search_for_markets groups by topic, searches, and distributes results."""
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    # Pre-fill cache so no real API calls happen
    from src.news_scanner import _cache_key
    import time
    articles = [
        {"title": "Trump announces new trade policy", "published": "2026-03-17",
         "summary": "trump election news", "link": "", "source": "test", "content": "", "is_breaking": False},
        {"title": "Weather forecast for tomorrow", "published": "2026-03-17",
         "summary": "weather", "link": "", "source": "test", "content": "", "is_breaking": False},
    ]
    # Cache the topic query that "trump" maps to
    topic_query = "us politics election 2026"
    scanner._cache[_cache_key(topic_query)] = (time.time(), articles)

    market_keywords = {"0xabc": ["trump", "election", "republican"]}
    matches = scanner.search_for_markets(market_keywords)
    assert "0xabc" in matches
    assert len(matches["0xabc"]) >= 1
    assert any("Trump" in a["title"] for a in matches["0xabc"])


def test_no_match_returns_fallback():
    """When no keyword matches, search_for_markets returns top articles as fallback."""
    from src.news_scanner import NewsScanner, _cache_key
    import time
    scanner = NewsScanner()
    articles = [{"title": "Cat video goes viral", "published": "2026-03-17",
                 "summary": "cats", "link": "", "source": "test", "content": "", "is_breaking": False}]
    # Cache the topic query for this keyword set
    topic_query = "us politics election 2026"
    scanner._cache[_cache_key(topic_query)] = (time.time(), articles)

    market_keywords = {"0xabc": ["trump", "election"]}
    matches = scanner.search_for_markets(market_keywords)
    # Falls back to top 2 articles when no keyword match
    assert "0xabc" in matches


def test_breaking_news_detection():
    from src.news_scanner import NewsScanner, BREAKING_PATTERNS
    # Test that BREAKING pattern is detected in article titles
    title = "BREAKING: Major political event unfolds"
    assert BREAKING_PATTERNS.search(title) is not None
    # Non-breaking
    assert BREAKING_PATTERNS.search("Normal headline here") is None
