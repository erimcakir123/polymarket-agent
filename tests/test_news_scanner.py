import pytest


def test_match_headlines_to_markets():
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    headlines = [
        {"title": "Trump announces new trade policy", "published": "2026-03-17"},
        {"title": "Weather forecast for tomorrow", "published": "2026-03-17"},
    ]
    market_keywords = {"0xabc": ["trump", "election", "republican"]}
    matches = scanner.match_headlines(headlines, market_keywords)
    assert "0xabc" in matches
    assert len(matches["0xabc"]) == 1
    assert "Trump" in matches["0xabc"][0]["title"]


def test_no_match_returns_empty():
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    headlines = [{"title": "Cat video goes viral", "published": "2026-03-17"}]
    market_keywords = {"0xabc": ["trump", "election"]}
    matches = scanner.match_headlines(headlines, market_keywords)
    assert len(matches.get("0xabc", [])) == 0


def test_breaking_news_detection():
    from src.news_scanner import NewsScanner
    scanner = NewsScanner()
    headlines = [
        {"title": "BREAKING: Major political event unfolds", "published": "2026-03-17"},
    ]
    market_keywords = {"0xabc": ["political", "event"]}
    matches = scanner.match_headlines(headlines, market_keywords)
    assert matches["0xabc"][0].get("is_breaking", False)
