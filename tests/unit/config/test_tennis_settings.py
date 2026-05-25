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
    # WTA disabled by default — empty list means rebuild script skips women's tour.
    assert cfg.sackmann_wta_years == []


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


# ── EntryExcludeCombo (data-driven entry exclusion) ──────────────────────────


def test_edge_exclude_combos_loaded_from_yaml() -> None:
    """2026-05-26 analysis: ATP_set_totals B (-$179 net) blocked via config."""
    from pathlib import Path

    from src.config.settings import load_config
    cfg = load_config(Path("config_tennis.yaml"))
    excl = cfg.edge.exclude_combos
    assert any(
        c.tour == "atp" and c.market_type == "tennis_set_totals" and c.confidence == "B"
        for c in excl
    )


def test_edge_exclude_combos_default_empty() -> None:
    """When not configured, exclude_combos defaults to []."""
    from src.config.settings import EdgeConfig
    cfg = EdgeConfig()
    assert cfg.exclude_combos == []


# ── stop_loss_exempt_market_types (bimodal SL bug fix) ───────────────────────


def test_stop_loss_exempt_market_types_loaded_from_yaml() -> None:
    """tennis_set_handicap is exempt from simple stop_loss (bimodal SL bug).

    shnaide-zarazua case (2026-05-26): entry 0.64, transient -50% to 0.32,
    simple SL fired at -$10. Market resolved at 0.9995 — would have won +$56.
    """
    from pathlib import Path

    from src.config.settings import load_config
    cfg = load_config(Path("config_tennis.yaml"))
    assert "tennis_set_handicap" in cfg.risk.stop_loss_exempt_market_types


def test_stop_loss_exempt_market_types_default_empty() -> None:
    """When not configured, exemption list defaults to []."""
    from src.config.settings import RiskConfig
    cfg = RiskConfig()
    assert cfg.stop_loss_exempt_market_types == []
