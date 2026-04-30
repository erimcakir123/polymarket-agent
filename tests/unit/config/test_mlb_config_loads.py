"""Smoke test for MLB config loading."""
from src.config.settings import AppConfig


def test_mlb_entry_config_has_defaults():
    s = AppConfig()
    assert s.entry.mlb_pre_game_window_max_hours == 12.0
    assert s.entry.mlb_rain_skip_threshold == 0.60
    assert s.entry.mlb_forbid_runline_minus_15_favorite is True


def test_mlb_exit_configs_exist():
    s = AppConfig()
    assert s.exit_mlb.near_resolve_threshold == 0.95
    assert s.exit_mlb_run_line.near_resolve_threshold == 0.95
    assert s.exit_mlb_totals.near_resolve_threshold == 0.95
