"""sport_rules.py için birim testler."""
from __future__ import annotations

from src.config.sport_rules import (
    DEFAULT_RULES,
    get_match_duration_hours,
    get_sport_rule,
)


def test_get_match_duration_tennis_default() -> None:
    assert get_match_duration_hours("tennis") == 2.5


def test_get_match_duration_alias_basketball_nba() -> None:
    assert get_match_duration_hours("basketball_nba") == 2.5


def test_get_match_duration_unknown_returns_default() -> None:
    assert get_match_duration_hours("unknown_sport") == DEFAULT_RULES["match_duration_hours"]


def test_get_sport_rule_period_exit_deficit_nhl() -> None:
    assert get_sport_rule("nhl", "period_exit_deficit") == 3


def test_get_sport_rule_missing_key_returns_default_arg() -> None:
    assert get_sport_rule("nba", "nonexistent_key", default=42) == 42


# ── ESPN mapping tests (SPEC-005 Task 2) ──

def test_get_score_source_nhl() -> None:
    assert get_sport_rule("nhl", "score_source") == "espn"


def test_get_espn_mapping_nhl() -> None:
    assert get_sport_rule("nhl", "espn_sport") == "hockey"
    assert get_sport_rule("nhl", "espn_league") == "nhl"


def test_get_espn_mapping_tennis() -> None:
    assert get_sport_rule("tennis", "score_source") == "espn"
    assert get_sport_rule("tennis", "espn_sport") == "tennis"
    assert get_sport_rule("tennis", "espn_league") == "atp"


def test_get_score_source_mlb() -> None:
    assert get_sport_rule("mlb", "score_source") == "espn"


# ── AHL hockey family (SPEC-014) ──

def test_ahl_inherits_nhl_thresholds() -> None:
    """SPEC-014: AHL K1-K4 esikleri NHL ile ayni."""
    for key in ("period_exit_deficit", "late_deficit"):
        nhl_val = get_sport_rule("nhl", key)
        ahl_val = get_sport_rule("ahl", key)
        if nhl_val is not None:
            assert ahl_val == nhl_val, f"AHL should inherit NHL's {key}"


def test_ahl_has_own_espn_league() -> None:
    """SPEC-014: AHL kendi ESPN endpoint'i (nhl != ahl)."""
    assert get_sport_rule("ahl", "espn_league") == "ahl"


def test_ahl_espn_sport_inherits_hockey() -> None:
    """SPEC-014: AHL NHL'in espn_sport'unu paylasir (hockey)."""
    nhl_sport = get_sport_rule("nhl", "espn_sport")
    if nhl_sport:
        assert get_sport_rule("ahl", "espn_sport") == nhl_sport


def test_nba_has_score_exit_n1_n2_n3_thresholds() -> None:
    """SPEC-A4: NBA N1=18 (regime change payı), N2=8, N3 Q4-son2dk + def5."""
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("nba", "score_exit_n1_elapsed") == 0.75
    assert get_sport_rule("nba", "score_exit_n1_deficit") == 18
    assert get_sport_rule("nba", "score_exit_n2_elapsed") == 0.92
    assert get_sport_rule("nba", "score_exit_n2_deficit") == 8
    assert get_sport_rule("nba", "score_exit_n3_clock_seconds") == 120
    assert get_sport_rule("nba", "score_exit_n3_deficit") == 5


def test_tennis_wta_espn_league_is_wta() -> None:
    assert get_sport_rule("tennis_wta", "espn_league") == "wta"


def test_tennis_wta_espn_sport_is_tennis() -> None:
    assert get_sport_rule("tennis_wta", "espn_sport") == "tennis"


def test_nfl_has_score_exit_n1_n2_n3_thresholds() -> None:
    """SPEC-A4: NFL N1=17 (σ-model %99 güven), N2=9, N3 Q4-son150s + def4."""
    from src.config.sport_rules import get_sport_rule
    assert get_sport_rule("nfl", "score_exit_n1_elapsed") == 0.75
    assert get_sport_rule("nfl", "score_exit_n1_deficit") == 17
    assert get_sport_rule("nfl", "score_exit_n2_elapsed") == 0.92
    assert get_sport_rule("nfl", "score_exit_n2_deficit") == 9
    assert get_sport_rule("nfl", "score_exit_n3_clock_seconds") == 150
    assert get_sport_rule("nfl", "score_exit_n3_deficit") == 4
