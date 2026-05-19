"""Integration: sandbox factory builds tennis system without main bot interference."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.orchestration.tennis_factory import build_tennis_deps


def test_factory_builds_with_paper_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Minimal config in tmp
    config_text = """
mode: paper
initial_bankroll: 500
scanner:
  min_liquidity: 1000
  max_markets_per_cycle: 100
  max_duration_days: 7
  max_hours_to_start: 24.0
  max_post_start_hours: 1.0
  resolved_price_threshold: 0.98
  allowed_categories: [sports]
  allowed_sport_tags: [tennis, atp]
  allowed_sports_market_types:
    - tennis_first_set_winner
    - tennis_set_handicap
    - tennis_set_totals
edge:
  min_edge: 0.05
risk:
  max_single_bet_usdc: 50
  max_bet_pct: 0.05
  confidence_bet_pct: {A: 0.05, B: 0.04}
  max_positions: 20
  max_positions_per_event: 2
dashboard:
  port: 5051
tennis:
  data_dir: "data/sackmann_cache"
  ratings_cache: "data/tennis_ratings.json"
  diagnostic_log_dir: "logs/tennis_diagnostics"
"""
    cfg_path = tmp_path / "config_tennis.yaml"
    cfg_path.write_text(config_text)
    deps = build_tennis_deps(config_path=cfg_path)
    assert deps is not None
    assert deps.config.tennis is not None
    assert deps.config.dashboard.port == 5051
    assert deps.config.mode.value == "paper"
