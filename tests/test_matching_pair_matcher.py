"""Tests for team pair matching."""
from src.matching.pair_matcher import match_team, match_pair


class TestMatchTeam:
    def test_exact_same(self):
        ok, conf, method = match_team("fnatic", "fnatic")
        assert ok and conf == 1.0

    def test_alias_match(self):
        ok, conf, method = match_team("lakers", "los angeles lakers")
        assert ok and conf == 1.0 and method == "exact_alias"

    def test_token_substring(self):
        ok, conf, method = match_team("lakers", "LA Lakers Basketball")
        assert ok and conf >= 0.85

    def test_fuzzy_high(self):
        ok, conf, method = match_team("manchester united", "man united fc")
        assert ok and conf >= 0.80

    def test_no_match(self):
        ok, conf, method = match_team("fnatic", "team liquid")
        assert not ok

    def test_normalized_suffix_strip(self):
        ok, conf, _ = match_team("team liquid", "liquid")
        assert ok


class TestMatchPair:
    def test_normal_order(self):
        ok, conf = match_pair(
            ("los angeles lakers", "boston celtics"),
            ("Los Angeles Lakers", "Boston Celtics"),
        )
        assert ok and conf >= 0.85

    def test_swapped_order(self):
        ok, conf = match_pair(
            ("boston celtics", "los angeles lakers"),
            ("Los Angeles Lakers", "Boston Celtics"),
        )
        assert ok and conf >= 0.85

    def test_no_match(self):
        ok, conf = match_pair(
            ("fnatic", "team liquid"),
            ("g2 esports", "natus vincere"),
        )
        assert not ok

    def test_partial_match_fails(self):
        """Only one team matching is not enough."""
        ok, conf = match_pair(
            ("fnatic", "team liquid"),
            ("fnatic", "natus vincere"),
        )
        assert not ok
