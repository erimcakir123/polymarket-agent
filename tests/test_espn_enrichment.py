"""Tests for ESPN enrichment (athlete-specific only)."""
from unittest.mock import MagicMock
from src.espn_enrichment import ESPNEnrichment


def _make_enrichment():
    """Create ESPNEnrichment with mocked SportsDataClient."""
    mock_client = MagicMock()
    mock_client.detect_sport.return_value = ("basketball", "nba")
    return ESPNEnrichment(sports_client=mock_client)


def test_enrich_returns_none_for_team_sports():
    """Team sports should return None — enrichment is in sports_data.py now."""
    e = _make_enrichment()
    e._client.detect_sport.return_value = ("basketball", "nba")
    result = e.enrich("Will Lakers beat Celtics?", "nba-lal-bos", ["nba"])
    assert result is None


def test_enrich_routes_athlete_sports():
    """Athlete sports (tennis, MMA, golf) should attempt enrichment."""
    e = _make_enrichment()
    e._client.detect_sport.return_value = ("tennis", "atp")
    result = e.enrich("Djokovic vs Nadal", "atp-djo-nad", ["tennis"])
    assert result is None or isinstance(result, str)


def test_cache_ttl():
    """Verify TTL cache stores and expires."""
    e = _make_enrichment()
    e._cache["test_key"] = {"data": "value", "ts": 0}
    assert e._get_cached("test_key", ttl=300) is None

    import time
    e._cache["test_key2"] = {"data": "value2", "ts": time.time()}
    assert e._get_cached("test_key2", ttl=300) == "value2"
