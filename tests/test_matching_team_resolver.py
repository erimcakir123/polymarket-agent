"""Tests for team name resolution from abbreviations/aliases."""
import json
from src.matching.team_resolver import TeamResolver


class TestTeamResolver:
    def _resolver(self, tmp_path):
        return TeamResolver(cache_path=tmp_path / "resolver_cache.json", auto_refresh=False)

    def test_static_nba(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("lal") == "los angeles lakers"
        assert r.resolve("bos") == "boston celtics"

    def test_static_esports(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("fnc") == "fnatic"
        assert r.resolve("navi") == "natus vincere"
        assert r.resolve("g2") == "g2 esports"

    def test_case_insensitive(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("LAL") == "los angeles lakers"
        assert r.resolve("FNC") == "fnatic"

    def test_unknown_returns_none(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("zzzzz") is None

    def test_alias_nicknames(self, tmp_path):
        r = self._resolver(tmp_path)
        assert r.resolve("lakers") == "los angeles lakers"
        assert r.resolve("celtics") == "boston celtics"
        assert r.resolve("spirit") == "team spirit"

    def test_load_from_cache(self, tmp_path):
        cache = tmp_path / "resolver_cache.json"
        cache.write_text(json.dumps({
            "abbrevs": {"xyz": "xyz gaming"},
            "aliases": {"xyz team": "xyz gaming"},
        }))
        r = TeamResolver(cache_path=cache, auto_refresh=False)
        assert r.resolve("xyz") == "xyz gaming"

    def test_normalize(self, tmp_path):
        from src.matching.team_resolver import normalize
        assert normalize("Team Liquid FC") == "team liquid"
        assert normalize("  Fnatic Esports  ") == "fnatic"
        assert normalize("G2 Gaming") == "g2"
