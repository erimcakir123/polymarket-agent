"""Cricket sport key + tag mapping tests (SPEC-011 Task 3)."""
from __future__ import annotations

from src.config.sport_rules import get_sport_rule
from src.domain.matching.odds_sport_keys import resolve_odds_key


def test_cricket_ipl_slug_maps_to_odds_key():
    assert resolve_odds_key("cricipl-kkr-rr-2026-04-19", []) == "cricket_ipl"


def test_cricket_odi_slug_maps_to_odds_key():
    assert resolve_odds_key("odi-ind-aus-2026", []) == "cricket_odi"


def test_cricket_psl_slug_maps():
    assert resolve_odds_key("cricpsl-lahore-karachi", []) == "cricket_psl"


def test_cricket_bbl_slug_maps():
    assert resolve_odds_key("cricbbl-syd-mel", []) == "cricket_bbl"


def test_cricket_pm_tag_indian_premier_league():
    assert resolve_odds_key("some-slug", ["indian-premier-league"]) == "cricket_ipl"


def test_cricket_pm_tag_big_bash_league():
    assert resolve_odds_key("", ["big-bash-league"]) == "cricket_bbl"


def test_cricket_bbl_alias_resolves_to_sport_rules():
    """Odds API 'cricket_bbl' key should resolve via _ALIASES to big_bash rules."""
    assert get_sport_rule("cricket_bbl", "score_exit_c1_balls", 0) == 30
    assert get_sport_rule("cricket_bbl", "score_source", "none") == "cricapi"


def test_cricket_cpl_alias_resolves_to_sport_rules():
    assert get_sport_rule("cricket_cpl", "score_exit_c1_balls", 0) == 30
    assert get_sport_rule("cricket_cpl", "score_source", "none") == "cricapi"


def test_cricket_sa20_falls_back_to_generic_cricket():
    # SA20 not in MVP scope, falls back to generic cricket (T20 default)
    assert get_sport_rule("cricket_sa20", "score_source", "none") == "cricapi"


def test_cricket_odi_direct_key_works():
    assert get_sport_rule("cricket_odi", "score_exit_c1_balls", 0) == 60
    assert get_sport_rule("cricket_odi", "match_duration_hours", 0) == 8.0
