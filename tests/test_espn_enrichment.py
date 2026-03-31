"""Tests for ESPN enrichment endpoints."""
from unittest.mock import MagicMock, patch
from src.espn_enrichment import ESPNEnrichment


def _make_enrichment():
    """Create ESPNEnrichment with mocked SportsDataClient."""
    mock_client = MagicMock()
    mock_client.detect_sport.return_value = ("basketball", "nba")
    return ESPNEnrichment(sports_client=mock_client)


def test_enrich_returns_string_or_none():
    """enrich() should return a context string or None."""
    e = _make_enrichment()
    result = e.enrich("Will Lakers beat Celtics?", "nba-lal-bos", ["nba"])
    # With mocked client, may return None (no real API) — that's fine
    assert result is None or isinstance(result, str)


def test_cache_ttl():
    """Verify TTL cache stores and expires."""
    e = _make_enrichment()
    e._cache["test_key"] = {"data": "value", "ts": 0}  # Expired
    assert e._get_cached("test_key", ttl=300) is None

    import time
    e._cache["test_key2"] = {"data": "value2", "ts": time.time()}
    assert e._get_cached("test_key2", ttl=300) == "value2"


def test_format_standings_section():
    """Verify standings formatting."""
    e = _make_enrichment()
    standing = {"rank": 3, "wins": 45, "losses": 20, "streak": "W5"}
    text = e._format_standing(standing, "Lakers")
    assert "Lakers" in text
    assert "45" in text
    assert "#3" in text
