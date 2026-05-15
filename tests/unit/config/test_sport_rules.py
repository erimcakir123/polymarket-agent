"""sport_rules.py için birim testler."""
from __future__ import annotations

from src.config.sport_rules import (
    DEFAULT_RULES,
    get_sport_rule,
    get_stop_loss,
    is_moneyline_only,
    is_spread_blocked,
)


def test_is_spread_blocked_nba_returns_true():
    assert is_spread_blocked("nba") is True


def test_is_spread_blocked_wnba_returns_true_via_basketball_tags():
    # Polymarket sport_tag "wnba" → BASKETBALL_TAGS via _normalize → "nba" rule → spread_blocked True
    assert is_spread_blocked("wnba") is True


def test_is_spread_blocked_basketball_wnba_alias_returns_true():
    # Odds API key "basketball_wnba" → alias → "nba" rule → spread_blocked True
    assert is_spread_blocked("basketball_wnba") is True


def test_is_spread_blocked_ncaab_via_basketball_tags():
    assert is_spread_blocked("ncaab") is True


def test_is_spread_blocked_nhl_returns_false():
    # NHL moneyline_only flag var, spread_blocked yok
    assert is_spread_blocked("nhl") is False


def test_is_spread_blocked_mlb_returns_false():
    assert is_spread_blocked("mlb") is False


def test_is_spread_blocked_unknown_returns_false():
    assert is_spread_blocked("unknown_sport") is False


def test_get_stop_loss_nba_returns_035() -> None:
    assert get_stop_loss("nba") == 0.35


def test_get_stop_loss_nfl_returns_030() -> None:
    assert get_stop_loss("nfl") == 0.30


def test_get_stop_loss_nhl_returns_030() -> None:
    assert get_stop_loss("nhl") == 0.30


def test_get_stop_loss_mlb_returns_030() -> None:
    assert get_stop_loss("mlb") == 0.30


def test_get_stop_loss_golf_returns_030() -> None:
    assert get_stop_loss("golf") == 0.30


def test_get_stop_loss_unknown_returns_default() -> None:
    assert get_stop_loss("unknown_sport") == DEFAULT_RULES["stop_loss_pct"]


def test_odds_api_key_alias_basketball_nba() -> None:
    assert get_stop_loss("basketball_nba") == 0.35


def test_odds_api_key_alias_baseball_milb() -> None:
    assert get_stop_loss("baseball_milb") == 0.30


def test_odds_api_key_alias_americanfootball_ncaaf() -> None:
    assert get_stop_loss("americanfootball_ncaaf") == 0.30


def test_mvp_sports_have_stop_loss() -> None:
    for sport in ["nba", "nfl", "nhl", "mlb", "golf"]:
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


def test_sport_rule_score_source_nhl() -> None:
    assert get_sport_rule("nhl", "score_source") == "espn"
    assert get_sport_rule("nhl", "espn_sport") == "hockey"
    assert get_sport_rule("nhl", "espn_league") == "nhl"


def test_sport_rule_score_source_mlb() -> None:
    assert get_sport_rule("mlb", "score_source") == "espn"
    assert get_sport_rule("mlb", "espn_sport") == "baseball"
    assert get_sport_rule("mlb", "espn_league") == "mlb"


def test_sport_rule_score_source_nba() -> None:
    assert get_sport_rule("nba", "score_source") == "espn"
    assert get_sport_rule("nba", "espn_sport") == "basketball"
    assert get_sport_rule("nba", "espn_league") == "nba"


# ── is_moneyline_only (NHL ML-only kanıt, SPEC-L 2026-05-11) ──

def test_is_moneyline_only_nhl_returns_true() -> None:
    """NHL: eski projede 4 günde 13W/2L +$126 ML-only kanıtı → flag True."""
    assert is_moneyline_only("nhl") is True


def test_is_moneyline_only_nba_returns_false() -> None:
    """NBA spreads/totals serbest (SPEC-J) → flag False."""
    assert is_moneyline_only("nba") is False


def test_is_moneyline_only_mlb_returns_false() -> None:
    """MLB için kısıt yok → flag False."""
    assert is_moneyline_only("mlb") is False


def test_is_moneyline_only_unknown_returns_false() -> None:
    """Bilinmeyen sport_tag default False döner."""
    assert is_moneyline_only("unknown_sport") is False


def test_is_moneyline_only_alias_icehockey_nhl_returns_true() -> None:
    """Odds API key alias 'icehockey_nhl' de NHL'e normalize olur."""
    assert is_moneyline_only("icehockey_nhl") is True
