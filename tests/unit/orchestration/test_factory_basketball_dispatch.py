"""factory.py sport_tag dispatch — basketball → basketball_anchor_enricher."""
from __future__ import annotations


def test_basketball_tag_routes_to_model_anchor():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("nba") == "basketball_model"


def test_wnba_tag_routes_to_model_anchor():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("wnba") == "basketball_model"


def test_tennis_tag_still_routes_to_tennis_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("atp") == "tennis_model"
    assert _select_enricher_for_sport("wta") == "tennis_model"


def test_unsupported_sport_falls_back_to_bookmaker():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("nfl") == "bookmaker"


def test_g_league_routes_to_basketball_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("g_league") == "basketball_model"


def test_summer_league_routes_to_basketball_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("summer_league") == "basketball_model"


def test_eurocup_routes_to_basketball_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("eurocup") == "basketball_model"


def test_bsl_acb_lega_route_to_basketball_model():
    from src.orchestration.factory import _select_enricher_for_sport
    assert _select_enricher_for_sport("bsl") == "basketball_model"
    assert _select_enricher_for_sport("acb") == "basketball_model"
    assert _select_enricher_for_sport("lega") == "basketball_model"
