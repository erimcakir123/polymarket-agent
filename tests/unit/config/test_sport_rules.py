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
