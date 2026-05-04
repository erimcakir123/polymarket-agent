"""Tests for NHL team alias resolution."""
from __future__ import annotations

import pytest
from src.domain.sports.nhl_team_aliases import (
    resolve_nhl_team,
    get_team_info,
    NHL_TEAMS,
)


class TestRoster:
    def test_thirty_two_teams(self):
        assert len(NHL_TEAMS) == 32

    def test_utah_is_mammoth_not_hockey_club(self):
        assert NHL_TEAMS["UTA"]["mascot"] == "Mammoth"
        assert NHL_TEAMS["UTA"]["name"] == "Utah Mammoth"

    def test_utah_former_name_registered(self):
        assert "Utah Hockey Club" in NHL_TEAMS["UTA"]["former_names"]

    def test_all_teams_have_name_and_mascot(self):
        for abbr, info in NHL_TEAMS.items():
            assert "name" in info, f"{abbr} missing name"
            assert "mascot" in info, f"{abbr} missing mascot"


class TestResolveByAbbr:
    def test_canonical_abbr_bos(self):
        assert resolve_nhl_team("BOS") == "BOS"

    def test_canonical_abbr_edm(self):
        assert resolve_nhl_team("EDM") == "EDM"

    def test_lowercase_abbr(self):
        assert resolve_nhl_team("bos") == "BOS"

    def test_mixed_case_abbr(self):
        assert resolve_nhl_team("Bos") == "BOS"

    def test_alt_abbr_lak_to_la(self):
        assert resolve_nhl_team("LAK") == "LA"

    def test_alt_abbr_njd_to_nj(self):
        assert resolve_nhl_team("NJD") == "NJ"

    def test_alt_abbr_sjs_to_sj(self):
        assert resolve_nhl_team("SJS") == "SJ"

    def test_alt_abbr_tbl_to_tb(self):
        assert resolve_nhl_team("TBL") == "TB"

    def test_canonical_la(self):
        assert resolve_nhl_team("LA") == "LA"

    def test_canonical_nj(self):
        assert resolve_nhl_team("NJ") == "NJ"


class TestResolveByMascot:
    def test_bruins(self):
        assert resolve_nhl_team("Bruins") == "BOS"

    def test_oilers(self):
        assert resolve_nhl_team("Oilers") == "EDM"

    def test_maple_leafs(self):
        assert resolve_nhl_team("Maple Leafs") == "TOR"

    def test_lightning(self):
        assert resolve_nhl_team("Lightning") == "TB"

    def test_blue_jackets(self):
        assert resolve_nhl_team("Blue Jackets") == "CBJ"

    def test_golden_knights(self):
        assert resolve_nhl_team("Golden Knights") == "VGK"

    def test_kraken(self):
        assert resolve_nhl_team("Kraken") == "SEA"

    def test_mammoth(self):
        assert resolve_nhl_team("Mammoth") == "UTA"

    def test_wild(self):
        assert resolve_nhl_team("Wild") == "MIN"

    def test_avalanche(self):
        assert resolve_nhl_team("Avalanche") == "COL"


class TestResolveByFullName:
    def test_boston_bruins(self):
        assert resolve_nhl_team("Boston Bruins") == "BOS"

    def test_st_louis_blues(self):
        assert resolve_nhl_team("St. Louis Blues") == "STL"

    def test_utah_mammoth(self):
        assert resolve_nhl_team("Utah Mammoth") == "UTA"

    def test_utah_hockey_club_former_name(self):
        assert resolve_nhl_team("Utah Hockey Club") == "UTA"

    def test_los_angeles_kings(self):
        assert resolve_nhl_team("Los Angeles Kings") == "LA"

    def test_new_jersey_devils(self):
        assert resolve_nhl_team("New Jersey Devils") == "NJ"

    def test_tampa_bay_lightning(self):
        assert resolve_nhl_team("Tampa Bay Lightning") == "TB"

    def test_vegas_golden_knights(self):
        assert resolve_nhl_team("Vegas Golden Knights") == "VGK"

    def test_montreal_canadiens(self):
        assert resolve_nhl_team("Montreal Canadiens") == "MTL"

    def test_columbus_blue_jackets(self):
        assert resolve_nhl_team("Columbus Blue Jackets") == "CBJ"


class TestEdgeCases:
    def test_none_returns_none(self):
        assert resolve_nhl_team(None) is None

    def test_empty_string_returns_none(self):
        assert resolve_nhl_team("") is None

    def test_unknown_team_returns_none(self):
        assert resolve_nhl_team("Houston Aeros") is None

    def test_whitespace_stripped(self):
        assert resolve_nhl_team("  BOS  ") == "BOS"

    def test_get_team_info_valid(self):
        info = get_team_info("BOS")
        assert info is not None
        assert info["name"] == "Boston Bruins"
        assert info["mascot"] == "Bruins"

    def test_get_team_info_unknown_returns_none(self):
        assert get_team_info("XYZ") is None

    def test_get_team_info_none_safe(self):
        assert get_team_info(None) is None

    def test_get_team_info_lowercase(self):
        assert get_team_info("bos") is not None
