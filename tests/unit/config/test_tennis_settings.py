"""TennisConfig için birim test (DECISIONS spec tennis lab v1.0)."""
from __future__ import annotations

from src.config.settings import AppConfig, TennisConfig, TennisConfidenceTier


def test_tennis_config_defaults():
    cfg = TennisConfig()
    assert cfg.data_dir == "data/sackmann_cache"
    assert cfg.tml_dir == "data/tml_cache"
    assert cfg.ratings_cache == "data/tennis_ratings.json"
    assert cfg.glicko_initial_rating == 1500
    assert cfg.glicko_initial_rd == 350
    assert cfg.glicko_tau == 0.5
    assert cfg.sackmann_years == [2022, 2023, 2024, 2025, 2026]


def test_tennis_confidence_tier_a_defaults():
    cfg = TennisConfig()
    assert cfg.confidence_tier_a.min_matches_12mo == 40
    assert cfg.confidence_tier_a.min_surface_matches == 15
    assert cfg.confidence_tier_a.min_h2h_years == 5
    assert cfg.confidence_tier_a.max_form_age_days == 60
    assert cfg.confidence_tier_a.max_glicko_rd == 100


def test_tennis_confidence_tier_b_defaults():
    cfg = TennisConfig()
    assert cfg.confidence_tier_b.min_matches_12mo == 20
    assert cfg.confidence_tier_b.min_surface_matches == 8
    assert cfg.confidence_tier_b.max_form_age_days == 90
    assert cfg.confidence_tier_b.max_glicko_rd == 150


def test_app_config_includes_tennis():
    cfg = AppConfig()
    assert cfg.tennis is not None
    assert isinstance(cfg.tennis, TennisConfig)


def test_confidence_tier_b_has_no_h2h_requirement():
    """Spec §6: Tier B does NOT enforce H2H requirement."""
    cfg = TennisConfig()
    assert cfg.confidence_tier_b.min_h2h_years is None


def test_confidence_tier_a_enforces_h2h():
    """Spec §6: Tier A requires H2H (default 5 years)."""
    cfg = TennisConfig()
    assert cfg.confidence_tier_a.min_h2h_years == 5
