# tests/test_correlation.py
import pytest


class TestMatchKeyExtraction:
    def test_cs2_map_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-map-1") == "cs2-faze-vs-navi"

    def test_no_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("lol-t1-vs-geng") == "lol-t1-vs-geng"

    def test_game_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("dota2-og-vs-spirit-game-2") == "dota2-og-vs-spirit"

    def test_winner_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-winner") == "cs2-faze-vs-navi"

    def test_over_under_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-over") == "cs2-faze-vs-navi"
        assert extract_match_key("cs2-faze-vs-navi-under") == "cs2-faze-vs-navi"

    def test_handicap_spread(self):
        from src.correlation import extract_match_key
        assert extract_match_key("lol-t1-vs-geng-handicap") == "lol-t1-vs-geng"
        assert extract_match_key("lol-t1-vs-geng-spread") == "lol-t1-vs-geng"

    def test_first_prefix_suffix(self):
        from src.correlation import extract_match_key
        assert extract_match_key("cs2-faze-vs-navi-first-blood") == "cs2-faze-vs-navi"


class TestNetExposure:
    def test_single_position(self):
        from src.correlation import get_match_exposure
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 50.0, "direction": "BUY_YES"}]
        exposure = get_match_exposure("cs2-faze-vs-navi", positions)
        assert exposure == 50.0

    def test_opposing_positions_net(self):
        from src.correlation import get_match_exposure
        positions = [
            {"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 50.0, "direction": "BUY_YES"},
            {"slug": "cs2-faze-vs-navi-map-2", "size_usdc": 30.0, "direction": "BUY_NO"},
        ]
        exposure = get_match_exposure("cs2-faze-vs-navi", positions)
        assert exposure == 20.0  # 50 - 30

    def test_unrelated_match_excluded(self):
        from src.correlation import get_match_exposure
        positions = [
            {"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 50.0, "direction": "BUY_YES"},
            {"slug": "lol-t1-vs-geng", "size_usdc": 100.0, "direction": "BUY_YES"},
        ]
        exposure = get_match_exposure("cs2-faze-vs-navi", positions)
        assert exposure == 50.0


class TestCorrelationCap:
    def test_within_limit_returns_full_size(self):
        from src.correlation import apply_correlation_cap
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=[], bankroll=1000.0,
        )
        assert capped == 30.0  # 30 < 150 (15% of 1000)

    def test_exceeds_limit_caps_size(self):
        from src.correlation import apply_correlation_cap
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 130.0, "direction": "BUY_YES"}]
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=positions, bankroll=1000.0,
        )
        assert capped == 20.0  # remaining = 150 - 130 = 20, min(30, 20) = 20

    def test_small_bankroll_tighter(self):
        from src.correlation import apply_correlation_cap
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=[], bankroll=100.0,
        )
        assert capped == 15.0  # max_exposure = 15 (15% of 100), min(30, 15) = 15

    def test_at_limit_returns_zero(self):
        from src.correlation import apply_correlation_cap
        positions = [{"slug": "cs2-faze-vs-navi-map-1", "size_usdc": 150.0, "direction": "BUY_YES"}]
        capped = apply_correlation_cap(
            proposed_size=30.0, match_key="cs2-faze-vs-navi",
            existing_positions=positions, bankroll=1000.0,
        )
        assert capped == 0.0  # already at limit
