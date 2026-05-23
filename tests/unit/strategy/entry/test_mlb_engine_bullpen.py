"""Tests for MlbSubmarketEngine opt-in bullpen interface (SPEC-R Task B1 revised).

5 test cases:
- default (no bullpen rates) → starter all innings
- with bullpen rates, inning 8, close game → setup tier
- with bullpen rates, inning 5 → always starter
- with bullpen rates, inning 9, score_diff=0 (close non-save) → setup
- with bullpen rates, unknown team_id → falls back to starter
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import MlbSubmarketConfig
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def _engine_no_bullpen() -> MlbSubmarketEngine:
    """Default engine: no bullpen rates → starter used all innings."""
    return MlbSubmarketEngine(
        statsapi=MagicMock(),
        statcast=MagicMock(),
        weather=MagicMock(),
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
        team_id_to_park_id={143: "FAKE"},
    )


def _engine_with_bullpen(
    bullpen_rates: dict[int, dict[str, dict[str, float]]],
) -> MlbSubmarketEngine:
    return MlbSubmarketEngine(
        statsapi=MagicMock(),
        statcast=MagicMock(),
        weather=MagicMock(),
        rate_cache=MagicMock(get=MagicMock(return_value=None)),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
        team_id_to_park_id={143: "FAKE"},
        team_bullpen_rates=bullpen_rates,
    )


def test_default_no_bullpen_uses_starter_all_innings() -> None:
    """Geriye uyumluluk: bullpen rates verilmezse starter tüm inning'ler boyunca."""
    engine = _engine_no_bullpen()
    starter = {"hr_rate": 0.04, "k_rate": 0.25}
    pitcher_for_inning = engine._select_pitcher_for_inning(
        inning=8, opposing_team_id=143, starter_rates=starter,
    )
    assert pitcher_for_inning == starter


def test_with_bullpen_inning_8_uses_setup() -> None:
    """Score_diff=0 (close game) varsayımıyla inning 8 → setup tier."""
    bullpen = {
        143: {
            "middle": {"hr_rate": 0.03, "k_rate": 0.22},
            "setup":  {"hr_rate": 0.02, "k_rate": 0.30},
            "closer": {"hr_rate": 0.01, "k_rate": 0.35},
        },
    }
    engine = _engine_with_bullpen(bullpen)
    starter = {"hr_rate": 0.05, "k_rate": 0.20}
    pitcher_for_inning = engine._select_pitcher_for_inning(
        inning=8, opposing_team_id=143, starter_rates=starter,
    )
    assert pitcher_for_inning == bullpen[143]["setup"]


def test_with_bullpen_inning_5_still_starter() -> None:
    """Inning 1-5 daima starter."""
    bullpen = {
        143: {
            "middle": {"hr_rate": 0.03},
            "setup":  {"hr_rate": 0.02},
            "closer": {"hr_rate": 0.01},
        },
    }
    engine = _engine_with_bullpen(bullpen)
    starter = {"hr_rate": 0.05}
    assert engine._select_pitcher_for_inning(5, 143, starter) == starter


def test_with_bullpen_inning_9_uses_setup() -> None:
    """Inning 9, score_diff=0 (close non-save situation) → setup tier."""
    bullpen = {
        143: {
            "middle": {"hr_rate": 0.03},
            "setup":  {"hr_rate": 0.02},
            "closer": {"hr_rate": 0.01},
        },
    }
    engine = _engine_with_bullpen(bullpen)
    starter = {"hr_rate": 0.05}
    # score_diff=0 → not a save situation (save = 1-3 lead) → setup
    assert engine._select_pitcher_for_inning(9, 143, starter) == bullpen[143]["setup"]


def test_with_bullpen_missing_team_falls_back_to_starter() -> None:
    """Eşleşmeyen team_id → starter (defensive fallback)."""
    bullpen = {
        999: {"middle": {"hr_rate": 0.03}, "setup": {"hr_rate": 0.02}, "closer": {"hr_rate": 0.01}},
    }
    engine = _engine_with_bullpen(bullpen)
    starter = {"hr_rate": 0.05}
    assert engine._select_pitcher_for_inning(8, 143, starter) == starter
