"""PLAN-012: SoccerLeagueCache — disk persist + TTL + learned map tests."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.infrastructure.persistence.soccer_league_cache import SoccerLeagueCache


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "soccer_league_cache.json"


class TestLeagueListCache:
    def test_empty_cache_returns_empty_list(self, cache_path: Path):
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        assert cache.get_leagues() == []

    def test_set_and_get_leagues(self, cache_path: Path):
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        cache.set_leagues(["arg.1", "rus.1", "uefa.champions"])
        assert cache.get_leagues() == ["arg.1", "rus.1", "uefa.champions"]

    def test_leagues_expire_after_ttl(self, cache_path: Path):
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=1)
        cache.set_leagues(["arg.1"])
        # manipulate timestamp to simulate expiration
        cache._league_list_ts = time.time() - (2 * 3600)
        assert cache.get_leagues() == []  # expired → empty

    def test_leagues_persist_to_disk(self, cache_path: Path):
        cache1 = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        cache1.set_leagues(["arg.1", "rus.1"])
        # New instance → load from disk
        cache2 = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        assert cache2.get_leagues() == ["arg.1", "rus.1"]


class TestLearnedMap:
    def test_no_learned_entry_returns_none(self, cache_path: Path):
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        assert cache.get_learned("rus", "Krylia Sovetov Samara") is None

    def test_set_and_get_learned(self, cache_path: Path):
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        cache.set_learned("rus", "Krylia Sovetov Samara", "rus.1")
        assert cache.get_learned("rus", "Krylia Sovetov Samara") == "rus.1"

    def test_learned_persists_to_disk(self, cache_path: Path):
        cache1 = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        cache1.set_learned("arg", "CA Platense", "arg.1")
        cache2 = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        assert cache2.get_learned("arg", "CA Platense") == "arg.1"

    def test_learned_team_key_normalised(self, cache_path: Path):
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        cache.set_learned("arg", "CA Platense", "arg.1")
        # Different case / whitespace → same key
        assert cache.get_learned("ARG", "ca platense") == "arg.1"
        assert cache.get_learned("arg", "  CA Platense  ") == "arg.1"


class TestCorruption:
    def test_corrupt_disk_file_returns_empty_state(self, cache_path: Path):
        cache_path.write_text("{not valid json", encoding="utf-8")
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        assert cache.get_leagues() == []
        assert cache.get_learned("rus", "x") is None

    def test_missing_file_returns_empty_state(self, cache_path: Path):
        assert not cache_path.exists()
        cache = SoccerLeagueCache(cache_path=cache_path, ttl_hours=24)
        assert cache.get_leagues() == []
