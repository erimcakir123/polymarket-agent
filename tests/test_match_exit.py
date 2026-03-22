"""Tests for match-aware exit system."""
import pytest


class TestParseMatchScore:
    def test_bo3_ahead(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("2-1|Bo3", number_of_games=3, direction="BUY_YES")
        assert result["available"] is True
        assert result["our_maps"] == 2
        assert result["opp_maps"] == 1
        assert result["map_diff"] == 1
        assert result["is_already_won"] is True  # 2 wins needed in BO3, we have 2

    def test_bo3_behind(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("0-2|Bo3", number_of_games=3, direction="BUY_YES")
        assert result["our_maps"] == 0
        assert result["opp_maps"] == 2
        assert result["map_diff"] == -2
        assert result["is_already_lost"] is True

    def test_bo5_mid_match(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("1-2|Bo5", number_of_games=5, direction="BUY_YES")
        assert result["our_maps"] == 1
        assert result["opp_maps"] == 2
        assert result["map_diff"] == -1
        assert result["is_already_lost"] is False  # Need 3 to win BO5
        assert result["is_already_won"] is False

    def test_buy_no_reverses_sides(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("2-1|Bo3", number_of_games=3, direction="BUY_NO")
        assert result["our_maps"] == 1  # reversed
        assert result["opp_maps"] == 2  # reversed
        assert result["map_diff"] == -1

    def test_simple_score_no_format(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("1-0", number_of_games=3, direction="BUY_YES")
        assert result["our_maps"] == 1
        assert result["opp_maps"] == 0
        assert result["map_diff"] == 1

    def test_empty_score(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("", number_of_games=3, direction="BUY_YES")
        assert result["available"] is False

    def test_none_score(self):
        from src.match_exit import parse_match_score
        result = parse_match_score(None, number_of_games=3, direction="BUY_YES")
        assert result["available"] is False

    def test_unparseable_score(self):
        from src.match_exit import parse_match_score
        result = parse_match_score("Live", number_of_games=3, direction="BUY_YES")
        assert result["available"] is False


class TestGameDuration:
    def test_cs2_bo3(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("cs2-nrg-furia-2026-03-22", 3) == 130

    def test_cs2_bo1(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("cs2-nrg-furia-2026-03-22", 1) == 40

    def test_valorant_bo5(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("val-lse-s8ul-2026-03-22", 5) == 220

    def test_dota2_bo3(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("dota2-tundra-bb4-2026-03-22", 3) == 130

    def test_lol_bo3(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("lol-g2-blg-2026-03-22", 3) == 100

    def test_football(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("epl-ast-wes-2026-03-22-total-2pt5", 0) == 95

    def test_nba(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("nba-por-den-2026-03-22-total-241pt5", 0) == 150

    def test_mlb(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("mlb-atl-min-2026-03-22", 0) == 180

    def test_nhl(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("nhl-car-pit-2026-03-22", 0) == 150

    def test_college_basketball(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("cbb-ucla-uconn-2026-03-22", 0) == 120

    def test_unknown_fallback(self):
        from src.match_exit import get_game_duration
        assert get_game_duration("some-unknown-market", 0) == 90

    def test_generic_esports_bo3(self):
        from src.match_exit import get_game_duration
        # Unknown esports game but has BO format → generic esports
        assert get_game_duration("hok-team1-team2-2026", 3) == 120
