"""Tests for market_matcher.py — AliasStore + match_batch."""
import json
from pathlib import Path
from dataclasses import dataclass

from src.market_matcher import (
    AliasStore, match_batch, STATIC_ABBREVS,
    _extract_slug_tokens, _detect_sport_context, _sports_compatible,
)


@dataclass
class FakeMarket:
    condition_id: str = "cond_123"
    question: str = ""
    slug: str = ""
    sport_tag: str = ""


class TestAliasStore:
    def test_static_fallback_has_entries(self):
        assert len(STATIC_ABBREVS) > 0
        assert "fnc" in STATIC_ABBREVS

    def test_load_from_cache_file(self, tmp_path):
        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps({
            "_meta": {"updated_at": "2026-04-03T00:00:00Z"},
            "abbrevs": {"lal": "los angeles lakers", "bos": "boston celtics"},
        }))
        store = AliasStore(cache_path=cache, auto_refresh=False)
        assert store.resolve("LAL") == "los angeles lakers"
        assert store.resolve("BOS") == "boston celtics"

    def test_fallback_when_no_cache(self, tmp_path):
        store = AliasStore(cache_path=tmp_path / "nope.json", auto_refresh=False)
        assert store._abbrevs  # static fallback

    def test_resolve_case_insensitive(self, tmp_path):
        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps({
            "_meta": {"updated_at": "2026-04-03T00:00:00Z"},
            "abbrevs": {"fnc": "fnatic"},
        }))
        store = AliasStore(cache_path=cache, auto_refresh=False)
        assert store.resolve("FNC") == "fnatic"
        assert store.resolve("fnc") == "fnatic"

    def test_unknown_returns_input_lowered(self, tmp_path):
        store = AliasStore(cache_path=tmp_path / "nope.json", auto_refresh=False)
        assert store.resolve("ZZZZZ") == "zzzzz"

    def test_corrupted_cache(self, tmp_path):
        cache = tmp_path / "cache.json"
        cache.write_text("{broken!!!")
        store = AliasStore(cache_path=cache, auto_refresh=False)
        assert store._abbrevs  # static fallback loaded


class TestHelpers:
    def test_extract_slug_tokens(self):
        assert _extract_slug_tokens("nba-lal-bos-2026-04-05") == {"nba", "lal", "bos"}
        assert _extract_slug_tokens("val-fnc-tl-2026-04-01") == {"val", "fnc", "tl"}

    def test_detect_sport_context(self):
        m1 = FakeMarket(slug="nba-lal-bos-2026-04-05")
        assert _detect_sport_context(m1) == "basketball"
        m2 = FakeMarket(slug="val-fnc-tl-2026-04-05")
        assert _detect_sport_context(m2) == "esports"

    def test_sports_compatible(self):
        assert _sports_compatible("basketball", "basketball") is True
        assert _sports_compatible("basketball", "football") is False
        assert _sports_compatible("esports", "esports") is True
        assert _sports_compatible("esports", "basketball") is False
        assert _sports_compatible(None, "basketball") is True  # unknown allows


class TestMatchBatch:
    def _store(self, tmp_path):
        return AliasStore(cache_path=tmp_path / "nope.json", auto_refresh=False)

    def test_exact_abbreviation_match(self, tmp_path):
        store = self._store(tmp_path)
        market = FakeMarket(slug="nba-lal-bos-2026-04-05", question="Lakers vs Celtics", sport_tag="NBA")
        entries = {
            "k1": {
                "scout_key": "k1", "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS", "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba", "is_esports": False,
            }
        }
        results = match_batch([market], entries, store)
        assert len(results) == 1
        assert results[0]["scout_key"] == "k1"

    def test_esports_acronym_match(self, tmp_path):
        store = self._store(tmp_path)
        market = FakeMarket(slug="val-fnc-tl-2026-04-05", question="Fnatic vs Team Liquid")
        entries = {
            "k1": {
                "scout_key": "k1", "team_a": "Fnatic", "team_b": "Team Liquid",
                "abbrev_a": "FNC", "abbrev_b": "TL", "match_time": "2026-04-05T18:00:00+00:00",
                "sport": "", "league": "", "is_esports": True,
            }
        }
        results = match_batch([market], entries, store)
        assert len(results) == 1

    def test_no_cross_sport_match(self, tmp_path):
        store = self._store(tmp_path)
        market = FakeMarket(slug="nba-phi-mia-2026-04-05", question="76ers vs Heat", sport_tag="NBA")
        entries = {
            "k1": {
                "scout_key": "k1", "team_a": "Philadelphia Eagles", "team_b": "Dallas Cowboys",
                "abbrev_a": "PHI", "abbrev_b": "DAL", "match_time": "2026-04-05T20:00:00+00:00",
                "sport": "football", "league": "nfl", "is_esports": False,
            }
        }
        results = match_batch([market], entries, store)
        assert len(results) == 0

    def test_short_name_match(self, tmp_path):
        store = self._store(tmp_path)
        market = FakeMarket(slug="will-lakers-beat-celtics", question="Will the Lakers beat the Celtics?")
        entries = {
            "k1": {
                "scout_key": "k1", "team_a": "Los Angeles Lakers", "team_b": "Boston Celtics",
                "abbrev_a": "LAL", "abbrev_b": "BOS", "short_a": "Lakers", "short_b": "Celtics",
                "match_time": "2026-04-05T00:00:00+00:00",
                "sport": "basketball", "league": "nba", "is_esports": False,
            }
        }
        results = match_batch([market], entries, store)
        assert len(results) == 1

    def test_doubleheader_picks_earliest(self, tmp_path):
        store = self._store(tmp_path)
        market = FakeMarket(slug="mlb-nyy-bos-2026-04-05", question="Yankees vs Red Sox", sport_tag="MLB")
        entries = {
            "game1": {
                "scout_key": "game1", "team_a": "New York Yankees", "team_b": "Boston Red Sox",
                "abbrev_a": "NYY", "abbrev_b": "BOS",
                "match_time": "2026-04-05T17:00:00+00:00",
                "sport": "baseball", "league": "mlb", "is_esports": False,
            },
            "game2": {
                "scout_key": "game2", "team_a": "New York Yankees", "team_b": "Boston Red Sox",
                "abbrev_a": "NYY", "abbrev_b": "BOS",
                "match_time": "2026-04-05T22:00:00+00:00",
                "sport": "baseball", "league": "mlb", "is_esports": False,
            },
        }
        results = match_batch([market], entries, store)
        assert len(results) == 1
        assert results[0]["scout_key"] == "game1"

    def test_return_format(self, tmp_path):
        store = self._store(tmp_path)
        market = FakeMarket(slug="val-fnc-tl-2026-04-05", question="Fnatic vs Team Liquid")
        entries = {
            "k1": {
                "scout_key": "k1", "team_a": "Fnatic", "team_b": "Team Liquid",
                "abbrev_a": "FNC", "abbrev_b": "TL",
                "match_time": "2026-04-05T18:00:00+00:00",
                "is_esports": True, "sport": "", "league": "",
            }
        }
        results = match_batch([market], entries, store)
        r = results[0]
        assert "market" in r and "scout_entry" in r and "scout_key" in r
        assert r["market"] is market
        assert r["scout_entry"]["team_a"] == "Fnatic"
        assert r["scout_key"] == "k1"
