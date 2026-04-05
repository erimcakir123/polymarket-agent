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


class TestLayer0Matching:
    """Layer 0: slug abbreviation → /teams name → scout entry team_a/team_b."""

    def _make_market(self, slug="nhl-nj-mon-2026-04-05", question="Devils vs. Canadiens"):
        from src.models import MarketData
        return MarketData(
            condition_id="0x123", question=question,
            yes_price=0.5, no_price=0.5,
            yes_token_id="1", no_token_id="2",
            slug=slug, sport_tag="nhl",
        )

    def test_layer0_matches_nhl_by_abbreviation(self):
        from src.matching import match_markets
        from src.matching.polymarket_teams import PolymarketTeamsCache
        import src.matching as matcher_mod

        fake_cache = PolymarketTeamsCache()
        fake_cache._abbr_to_name = {"nj": "Devils", "mon": "Canadiens"}
        matcher_mod._teams_cache = fake_cache

        market = self._make_market()
        scout_queue = {
            "hockey_nhl_NJD_MTL_20260405": {
                "team_a": "New Jersey Devils",
                "team_b": "Montreal Canadiens",
                "sport": "hockey",
                "match_time": "2026-04-05T23:00:00Z",
            }
        }

        result = match_markets([market], scout_queue)
        assert len(result) == 1
        assert result[0]["market"].slug == "nhl-nj-mon-2026-04-05"
        assert result[0]["scout_entry"]["team_a"] == "New Jersey Devils"

    def test_layer0_matches_esports_csgo(self):
        from src.matching import match_markets
        from src.matching.polymarket_teams import PolymarketTeamsCache
        import src.matching as matcher_mod

        fake_cache = PolymarketTeamsCache()
        fake_cache._abbr_to_name = {"pain": "paiN", "gl1": "GamerLegion"}
        matcher_mod._teams_cache = fake_cache

        market = self._make_market(
            slug="cs2-pain-gl1-2026-04-06",
            question="Counter-Strike: paiN vs GamerLegion (BO3)",
        )
        scout_queue = {
            "csgo_paiN_GamerLegion_20260406": {
                "team_a": "paiN",
                "team_b": "GamerLegion",
                "sport": "",
                "match_time": "2026-04-06T15:00:00Z",
            }
        }

        result = match_markets([market], scout_queue)
        assert len(result) == 1

    def test_layer0_falls_through_to_fuzzy(self):
        """If Layer 0 can't resolve, old fuzzy layers should still match."""
        from src.matching import match_markets
        from src.matching.polymarket_teams import PolymarketTeamsCache
        import src.matching as matcher_mod

        fake_cache = PolymarketTeamsCache()
        fake_cache._abbr_to_name = {}
        matcher_mod._teams_cache = fake_cache

        market = self._make_market(
            slug="nhl-nj-mon-2026-04-05",
            question="New Jersey Devils vs Montreal Canadiens",
        )
        scout_queue = {
            "hockey_nhl_NJD_MTL_20260405": {
                "team_a": "New Jersey Devils",
                "team_b": "Montreal Canadiens",
                "abbrev_a": "", "abbrev_b": "",
                "short_a": "devils", "short_b": "canadiens",
                "sport": "hockey",
                "match_time": "2026-04-05T23:00:00Z",
            }
        }

        result = match_markets([market], scout_queue)
        assert len(result) == 1
