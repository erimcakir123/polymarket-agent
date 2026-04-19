"""sport_rules.py için birim testler."""
from __future__ import annotations

from src.config.sport_rules import (
    DEFAULT_RULES,
    get_match_duration_hours,
    get_sport_rule,
    get_stop_loss,
)


def test_get_stop_loss_nba_returns_035() -> None:
    assert get_stop_loss("nba") == 0.35


def test_get_stop_loss_nfl_returns_030() -> None:
    assert get_stop_loss("nfl") == 0.30


def test_get_stop_loss_nhl_returns_030() -> None:
    assert get_stop_loss("nhl") == 0.30


def test_get_stop_loss_mlb_returns_030() -> None:
    assert get_stop_loss("mlb") == 0.30


def test_get_stop_loss_tennis_returns_035() -> None:
    assert get_stop_loss("tennis") == 0.35


def test_get_stop_loss_golf_returns_030() -> None:
    assert get_stop_loss("golf") == 0.30


def test_get_stop_loss_unknown_returns_default() -> None:
    assert get_stop_loss("unknown_sport") == DEFAULT_RULES["stop_loss_pct"]


def test_get_match_duration_tennis_default() -> None:
    assert get_match_duration_hours("tennis") == 2.5


def test_odds_api_key_alias_basketball_nba() -> None:
    assert get_stop_loss("basketball_nba") == 0.35


def test_odds_api_key_alias_baseball_milb() -> None:
    assert get_stop_loss("baseball_milb") == 0.30


def test_odds_api_key_alias_americanfootball_ncaaf() -> None:
    assert get_stop_loss("americanfootball_ncaaf") == 0.30


def test_odds_api_key_alias_tennis_dynamic() -> None:
    # tennis_atp_french_open → tennis
    assert get_stop_loss("tennis_atp_french_open") == 0.35


def test_mvp_sports_have_stop_loss() -> None:
    for sport in ["nba", "nfl", "nhl", "mlb", "tennis", "golf"]:
        sl = get_stop_loss(sport)
        assert 0.05 <= sl <= 0.70, f"{sport} sl out of range: {sl}"


def test_get_sport_rule_halftime_deficit_nba() -> None:
    assert get_sport_rule("nba", "halftime_exit_deficit") == 15


def test_get_sport_rule_period_exit_deficit_nhl() -> None:
    assert get_sport_rule("nhl", "period_exit_deficit") == 3


def test_get_sport_rule_inning_exit_deficit_mlb() -> None:
    assert get_sport_rule("mlb", "inning_exit_deficit") == 5


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


def test_get_score_source_golf_none() -> None:
    assert get_sport_rule("golf", "score_source") is None


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
