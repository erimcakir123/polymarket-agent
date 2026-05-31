"""refresh_runner — primary OK / primary fail → fallback / total fail."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.infrastructure.data.basketball.refresh_runner import (
    BasketballRefreshRunner,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def sample_game():
    return GameRecord(
        game_id="0022400001", season="2024-25",
        game_date_utc="2024-11-01T23:30:00Z",
        home_team="LAL", away_team="GSW",
        home_score=110, away_score=104,
        home_possessions=101.7, away_possessions=98.4,
        is_final=True, league="nba",
    )


def test_primary_success_marks_health_and_returns_games(tmp_path: Path, sample_game):
    primary = MagicMock(return_value=[sample_game])
    secondary = MagicMock()
    runner = BasketballRefreshRunner(
        league="nba", health_path=tmp_path / "h.json",
        primary_fetch=primary, secondary_fetch=secondary,
        now_utc_str=lambda: "2024-11-01T00:00:00Z",
    )
    result = runner.run()
    assert len(result.games) == 1
    assert result.source_used == "nba_api"
    secondary.assert_not_called()


def test_primary_fail_falls_back_to_secondary(tmp_path: Path, sample_game):
    primary = MagicMock(side_effect=Exception("network"))
    secondary = MagicMock(return_value=[sample_game])
    runner = BasketballRefreshRunner(
        league="nba", health_path=tmp_path / "h.json",
        primary_fetch=primary, secondary_fetch=secondary,
        now_utc_str=lambda: "2024-11-01T00:00:00Z",
    )
    result = runner.run()
    assert result.source_used == "espn"
    assert len(result.games) == 1


def test_both_sources_fail_returns_empty_degrade(tmp_path: Path):
    primary = MagicMock(side_effect=Exception("network"))
    secondary = MagicMock(side_effect=Exception("network"))
    runner = BasketballRefreshRunner(
        league="nba", health_path=tmp_path / "h.json",
        primary_fetch=primary, secondary_fetch=secondary,
        now_utc_str=lambda: "2024-11-01T00:00:00Z",
    )
    result = runner.run()
    assert result.games == []
    assert result.source_used is None  # degrade
