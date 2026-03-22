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
