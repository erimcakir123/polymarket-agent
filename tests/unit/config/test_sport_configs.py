"""Sport config pattern tests (SPEC-015)."""


def test_soccer_config_basics() -> None:
    from src.config.sport_configs.soccer import SOCCER_CONFIG
    assert SOCCER_CONFIG["regulation_minutes"] == 90
    assert SOCCER_CONFIG["score_exit_first_half_lock"] == 65
    assert SOCCER_CONFIG["score_exit_2goal_minute"] == 65
    assert SOCCER_CONFIG["score_exit_1goal_minute"] == 75
    assert SOCCER_CONFIG["draw_protect_until"] == 70
    assert SOCCER_CONFIG["draw_exit_after_goal"] == 75
    assert SOCCER_CONFIG["knockout_auto_exit_draw"] is True
    assert "International Friendly" in SOCCER_CONFIG["excluded_competitions"]


def test_rugby_union_config_basics() -> None:
    from src.config.sport_configs.rugby_union import RUGBY_UNION_CONFIG
    assert RUGBY_UNION_CONFIG["regulation_minutes"] == 80
    assert RUGBY_UNION_CONFIG["score_exit_blowout_deficit"] == 14


def test_afl_config_basics() -> None:
    from src.config.sport_configs.afl import AFL_CONFIG
    assert AFL_CONFIG["regulation_minutes"] == 80
    assert AFL_CONFIG["score_exit_blowout_deficit"] == 30


def test_handball_config_basics() -> None:
    from src.config.sport_configs.handball import HANDBALL_CONFIG
    assert HANDBALL_CONFIG["regulation_minutes"] == 60


def test_get_sport_config_resolver_exact() -> None:
    from src.config.sport_configs import get_sport_config
    cfg = get_sport_config("soccer")
    assert cfg is not None
    assert cfg["regulation_minutes"] == 90


def test_get_sport_config_resolver_substring() -> None:
    """'soccer_epl' → 'soccer' substring match."""
    from src.config.sport_configs import get_sport_config
    cfg = get_sport_config("soccer_epl")
    assert cfg is not None
    assert cfg["regulation_minutes"] == 90


def test_get_sport_config_unknown_returns_none() -> None:
    from src.config.sport_configs import get_sport_config
    assert get_sport_config("unknown_sport") is None


def test_get_sport_config_empty_returns_none() -> None:
    from src.config.sport_configs import get_sport_config
    assert get_sport_config("") is None
    assert get_sport_config(None) is None


def test_rugby_alias_works() -> None:
    """'rugby' alias → RUGBY_UNION_CONFIG."""
    from src.config.sport_configs import get_sport_config
    cfg = get_sport_config("rugby")
    assert cfg is not None
    assert cfg["regulation_minutes"] == 80
