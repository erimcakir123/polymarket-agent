"""Tests for Polymarket NHL question parser."""
from __future__ import annotations

import pytest
from src.domain.sports.nhl_question_parser import (
    parse_nhl_question,
    is_nhl_question,
)


class TestBasicVsPattern:
    def test_mascot_vs_mascot(self):
        assert parse_nhl_question("Bruins vs. Sabres") == ("BOS", "BUF")

    def test_no_period_after_vs(self):
        assert parse_nhl_question("Bruins vs Sabres") == ("BOS", "BUF")

    def test_full_name_vs(self):
        assert parse_nhl_question("Boston Bruins vs. Buffalo Sabres") == ("BOS", "BUF")

    def test_oilers_vs_ducks(self):
        assert parse_nhl_question("Oilers vs. Ducks") == ("EDM", "ANA")

    def test_maple_leafs_vs_canadiens(self):
        assert parse_nhl_question("Maple Leafs vs. Canadiens") == ("TOR", "MTL")

    def test_blue_jackets_vs_predators(self):
        assert parse_nhl_question("Blue Jackets vs. Predators") == ("CBJ", "NSH")


class TestPrefixPattern:
    def test_nhl_prefix(self):
        assert parse_nhl_question("NHL: Lightning vs. Canadiens") == ("TB", "MTL")

    def test_nhl_playoffs_prefix(self):
        assert parse_nhl_question("NHL Playoffs: Oilers vs. Ducks") == ("EDM", "ANA")

    def test_nhl_playoff_singular(self):
        assert parse_nhl_question("NHL Playoff: Bruins vs. Panthers") == ("BOS", "FLA")


class TestQuestionFormPattern:
    def test_will_x_win_against_y(self):
        assert parse_nhl_question("Will the Bruins win against the Sabres?") == ("BOS", "BUF")

    def test_will_x_beat_y(self):
        assert parse_nhl_question("Will the Oilers beat the Ducks?") == ("EDM", "ANA")

    def test_will_without_the(self):
        assert parse_nhl_question("Will Bruins win against Sabres?") == ("BOS", "BUF")

    def test_no_question_mark(self):
        assert parse_nhl_question("Will the Bruins win against the Sabres") == ("BOS", "BUF")


class TestUtahMammothEdgeCase:
    def test_mammoth_vs_kraken(self):
        assert parse_nhl_question("Mammoth vs. Kraken") == ("UTA", "SEA")

    def test_utah_mammoth_full(self):
        assert parse_nhl_question("Utah Mammoth vs. Seattle Kraken") == ("UTA", "SEA")

    def test_legacy_utah_hockey_club(self):
        assert parse_nhl_question("Utah Hockey Club vs. Seattle Kraken") == ("UTA", "SEA")


class TestMultiWordTeams:
    def test_red_wings_vs_blackhawks(self):
        assert parse_nhl_question("Red Wings vs. Blackhawks") == ("DET", "CHI")

    def test_golden_knights_vs_kings(self):
        assert parse_nhl_question("Golden Knights vs. Kings") == ("VGK", "LA")

    def test_st_louis_blues_vs_dallas_stars(self):
        assert parse_nhl_question("St. Louis Blues vs. Dallas Stars") == ("STL", "DAL")


class TestEdgeCases:
    def test_unknown_team_returns_none(self):
        assert parse_nhl_question("Galatasaray vs. Fenerbahce") is None

    def test_one_known_one_unknown_returns_none(self):
        assert parse_nhl_question("Bruins vs. Galatasaray") is None

    def test_same_team_twice_returns_none(self):
        assert parse_nhl_question("Bruins vs. Bruins") is None

    def test_empty_string(self):
        assert parse_nhl_question("") is None

    def test_none_safe(self):
        assert parse_nhl_question(None) is None

    def test_whitespace_only(self):
        assert parse_nhl_question("   ") is None

    def test_not_a_match_question(self):
        assert parse_nhl_question("What is hockey?") is None

    def test_no_vs_separator(self):
        assert parse_nhl_question("Bruins beat Sabres yesterday") is None


class TestIsNHLQuestion:
    def test_yes_for_valid_nhl(self):
        assert is_nhl_question("Bruins vs. Sabres") is True

    def test_no_for_unknown_teams(self):
        assert is_nhl_question("Lakers vs. Warriors") is False

    def test_no_for_empty(self):
        assert is_nhl_question("") is False

    def test_no_for_none(self):
        assert is_nhl_question(None) is False


class TestCaseSensitivity:
    def test_lowercase(self):
        assert parse_nhl_question("bruins vs. sabres") == ("BOS", "BUF")

    def test_uppercase(self):
        assert parse_nhl_question("BRUINS VS. SABRES") == ("BOS", "BUF")

    def test_mixed_case(self):
        assert parse_nhl_question("BrUiNs Vs. SaBrEs") == ("BOS", "BUF")


class TestPunctuationVariation:
    def test_extra_whitespace(self):
        assert parse_nhl_question("  Bruins   vs.   Sabres  ") == ("BOS", "BUF")

    def test_no_period_in_vs(self):
        assert parse_nhl_question("Bruins vs Sabres") == ("BOS", "BUF")
