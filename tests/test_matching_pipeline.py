"""Integration tests for the full matching pipeline."""
import pytest
from dataclasses import dataclass, field
from typing import List

import src.matching as matching_module
from src.matching import match_markets


@dataclass
class FakeMarket:
    condition_id: str = "cond_123"
    question: str = ""
    slug: str = ""
    sport_tag: str = ""
    tags: List[str] = field(default_factory=list)


@pytest.fixture(autouse=True)
def reset_resolver():
    matching_module._resolver = None
    yield
    matching_module._resolver = None


class TestMatchMarkets:
    def test_nba_abbreviation_match(self, tmp_path):
        market = FakeMarket(
            slug="nba-lal-bos-2026-04-05",
            question="Will the Los Angeles Lakers beat the Boston Celtics?",
        )
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS",
                "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 1
        assert results[0]["scout_key"] == "k1"

    def test_esports_match(self, tmp_path):
        market = FakeMarket(
            slug="cs2-hero-nip-2026-04-03",
            question="Counter-Strike: Heroic vs NIP",
        )
        queue = {
            "k1": {
                "team_a": "Heroic", "team_b": "NIP",
                "abbrev_a": "HERO", "abbrev_b": "NIP",
                "short_a": "", "short_b": "",
                "match_time": "2026-04-03T12:00:00+00:00",
                "sport": "", "league": "",
                "is_esports": True, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 1

    def test_no_cross_sport(self, tmp_path):
        market = FakeMarket(slug="nba-phi-mia-2026-04-05", question="76ers vs Heat")
        queue = {
            "k1": {
                "team_a": "Philadelphia Eagles", "team_b": "Miami Dolphins",
                "abbrev_a": "PHI", "abbrev_b": "MIA",
                "short_a": "Eagles", "short_b": "Dolphins",
                "match_time": "2026-04-05T20:00:00+00:00",
                "sport": "football", "league": "nfl",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 0

    def test_skips_entered(self, tmp_path):
        market = FakeMarket(slug="nba-lal-bos-2026-04-05", question="Lakers vs Celtics")
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS",
                "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": True,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 0

    def test_empty_abbrevs_still_matches_by_name(self, tmp_path):
        """Even without abbreviations, full names in question should match."""
        market = FakeMarket(
            slug="some-unknown-slug",
            question="Will the Los Angeles Lakers beat the Boston Celtics?",
        )
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "", "abbrev_b": "",
                "short_a": "", "short_b": "",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        assert len(results) == 1

    def test_return_format(self, tmp_path):
        market = FakeMarket(slug="nba-lal-bos-2026-04-05", question="Lakers vs Celtics")
        queue = {
            "k1": {
                "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS",
                "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba",
                "is_esports": False, "entered": False,
            }
        }
        results = match_markets([market], queue, cache_dir=tmp_path)
        r = results[0]
        assert "market" in r and "scout_entry" in r and "scout_key" in r
        assert r["scout_entry"]["matched"] is True
        assert "match_confidence" in r["scout_entry"]
