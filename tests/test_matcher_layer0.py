"""Tests for Polymarket /teams-based matcher Layer 0."""
from __future__ import annotations


class TestPolymarketTeamsCache:
    def test_resolve_known_abbreviation(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        cache = PolymarketTeamsCache()
        cache._abbr_to_name = {
            "nj": "Devils",
            "mon": "Canadiens",
            "bos": "Bruins",
            "pain": "paiN",
        }

        assert cache.resolve("nj") == "Devils"
        assert cache.resolve("mon") == "Canadiens"
        assert cache.resolve("pain") == "paiN"

    def test_resolve_unknown_returns_none(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        cache = PolymarketTeamsCache()
        cache._abbr_to_name = {"nj": "Devils"}

        assert cache.resolve("xyz") is None
        assert cache.resolve("") is None

    def test_resolve_case_insensitive(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        cache = PolymarketTeamsCache()
        cache._abbr_to_name = {"nj": "Devils"}

        assert cache.resolve("NJ") == "Devils"
        assert cache.resolve("Nj") == "Devils"

    def test_load_from_api_response(self):
        from src.matching.polymarket_teams import PolymarketTeamsCache

        fake_response = [
            {"id": 100630, "name": "Devils", "abbreviation": "nj", "alias": "Devils", "league": "nhl"},
            {"id": 100628, "name": "Canadiens", "abbreviation": "mon", "alias": "Canadiens", "league": "nhl"},
            {"id": 177234, "name": "paiN", "abbreviation": "pain", "alias": "paiN", "league": "csgo"},
        ]
        cache = PolymarketTeamsCache()
        cache._ingest_teams(fake_response)

        assert cache.resolve("nj") == "Devils"
        assert cache.resolve("mon") == "Canadiens"
        assert cache.resolve("pain") == "paiN"
        assert len(cache._abbr_to_name) == 3
