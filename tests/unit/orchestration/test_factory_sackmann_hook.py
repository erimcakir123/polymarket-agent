"""Phase 3: factory tennis startup hook gated by allowed_sport_tags."""
from unittest.mock import patch

from src.config.settings import AppConfig
from src.orchestration import factory


def test_sackmann_refresh_skipped_when_tennis_not_in_whitelist() -> None:
    cfg = AppConfig()
    cfg.scanner.allowed_sport_tags = ["nba", "wnba"]
    with patch("src.orchestration.factory_refresh_hooks.maybe_refresh_sackmann_on_startup") as m:
        factory._maybe_invoke_sackmann_refresh(cfg)
        m.assert_not_called()


def test_sackmann_refresh_invoked_when_atp_in_whitelist() -> None:
    cfg = AppConfig()
    cfg.scanner.allowed_sport_tags = ["nba", "atp"]
    with patch("src.orchestration.factory_refresh_hooks.maybe_refresh_sackmann_on_startup") as m:
        factory._maybe_invoke_sackmann_refresh(cfg)
        m.assert_called_once()


def test_sackmann_refresh_invoked_when_wta_in_whitelist() -> None:
    cfg = AppConfig()
    cfg.scanner.allowed_sport_tags = ["wta"]
    with patch("src.orchestration.factory_refresh_hooks.maybe_refresh_sackmann_on_startup") as m:
        factory._maybe_invoke_sackmann_refresh(cfg)
        m.assert_called_once()


def test_sackmann_refresh_case_insensitive() -> None:
    cfg = AppConfig()
    cfg.scanner.allowed_sport_tags = ["ATP", "WTA"]
    with patch("src.orchestration.factory_refresh_hooks.maybe_refresh_sackmann_on_startup") as m:
        factory._maybe_invoke_sackmann_refresh(cfg)
        m.assert_called_once()
