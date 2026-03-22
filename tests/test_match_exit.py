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


class TestEntryPriceMultiplier:
    def test_heavy_underdog(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.15) == 1.50

    def test_underdog(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.25) == 1.25

    def test_coin_flip(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.45) == 1.00

    def test_favorite(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.60) == 0.85

    def test_heavy_favorite(self):
        from src.match_exit import get_entry_price_multiplier
        assert get_entry_price_multiplier(0.80) == 0.70


class TestGraduatedMaxLoss:
    def test_early_match_coin_flip(self):
        from src.match_exit import get_graduated_max_loss
        # 30% progress, 45¢ entry, no score
        loss = get_graduated_max_loss(0.30, 0.45, {"available": False})
        assert loss == pytest.approx(0.40, abs=0.01)  # -40% × 1.0 × 1.0

    def test_mid_match_favorite(self):
        from src.match_exit import get_graduated_max_loss
        # 50% progress, 65¢ entry, no score
        loss = get_graduated_max_loss(0.50, 0.65, {"available": False})
        assert loss == pytest.approx(0.255, abs=0.01)  # -30% × 0.85

    def test_late_match_underdog_ahead(self):
        from src.match_exit import get_graduated_max_loss
        # 75% progress, 25¢ entry, score ahead
        score = {"available": True, "map_diff": 1, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(0.75, 0.25, score)
        # -20% × 1.25 × 1.25 = -31.25%
        assert loss == pytest.approx(0.3125, abs=0.01)

    def test_final_phase_favorite_behind(self):
        from src.match_exit import get_graduated_max_loss
        # 90% progress, 70¢ entry, score behind
        score = {"available": True, "map_diff": -1, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(0.90, 0.70, score)
        # -15% × 0.70 × 0.75 = -7.875%
        assert loss == pytest.approx(0.07875, abs=0.01)

    def test_overtime(self):
        from src.match_exit import get_graduated_max_loss
        loss = get_graduated_max_loss(1.10, 0.50, {"available": False})
        assert loss == pytest.approx(0.05, abs=0.01)  # -5% × 1.0

    def test_pre_match(self):
        from src.match_exit import get_graduated_max_loss
        loss = get_graduated_max_loss(-0.5, 0.50, {"available": False})
        assert loss == pytest.approx(0.40, abs=0.01)  # Pre-match default

    def test_clamp_max(self):
        from src.match_exit import get_graduated_max_loss
        # Heavy underdog early: -40% × 1.50 × 1.25 (ahead) = -75% → clamped to -70%
        score = {"available": True, "map_diff": 1, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(0.30, 0.10, score)
        assert loss <= 0.70

    def test_clamp_min(self):
        from src.match_exit import get_graduated_max_loss
        # Overtime heavy favorite behind: -5% × 0.70 × 0.75 = -2.625% → clamped to -5%
        score = {"available": True, "map_diff": -2, "is_already_lost": False, "is_already_won": False}
        loss = get_graduated_max_loss(1.10, 0.80, score)
        assert loss >= 0.05
