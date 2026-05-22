"""Tennis sport_rules girdisinin var olduğunu doğrula."""
from src.config.sport_rules import get_sport_rule


def test_tennis_has_start_source_espn():
    assert get_sport_rule("tennis", "start_source") == "espn"


def test_tennis_espn_leagues_contain_atp_and_wta():
    leagues = get_sport_rule("tennis", "espn_leagues")
    assert "atp" in leagues
    assert "wta" in leagues


def test_tennis_atp_alias_normalizes_to_tennis():
    assert get_sport_rule("tennis_atp", "start_source") == "espn"


def test_tennis_wta_alias_normalizes_to_tennis():
    assert get_sport_rule("tennis_wta", "start_source") == "espn"


def test_tennis_has_no_score_source():
    """Tennis ESPN sadece match_start için; skor entegrasyonu yok."""
    # default=None should return None since key absent
    assert get_sport_rule("tennis", "score_source", default=None) is None
