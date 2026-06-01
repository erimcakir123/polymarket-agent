"""euroleague-api refresher testleri — mocked endpoint."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from src.infrastructure.data.basketball.euroleague_refresher import (
    fetch_game_log_via_euroleague_api,
    _convert_euroleague_row_to_game_record,
)
from src.infrastructure.data.basketball.schemas import GameRecord


@pytest.fixture
def fake_eul_home_row():
    return {
        "Gamecode": "2024-101",
        "Season": 2024,
        "Date": "2024-10-15T19:00:00Z",
        "TeamCode": "RM",
        "Points": 85,
        "FieldGoalsAttempted": 70,
        "FreeThrowsAttempted": 18,
        "OffensiveRebounds": 9,
        "Turnovers": 11,
        "HomeAway": "home",
    }


@pytest.fixture
def fake_eul_away_row(fake_eul_home_row):
    row = dict(fake_eul_home_row)
    row["TeamCode"] = "FB"
    row["Points"] = 79
    row["FieldGoalsAttempted"] = 68
    row["FreeThrowsAttempted"] = 16
    row["OffensiveRebounds"] = 8
    row["Turnovers"] = 13
    row["HomeAway"] = "away"
    return row


def test_convert_row_produces_valid_game_record(fake_eul_home_row, fake_eul_away_row):
    rec = _convert_euroleague_row_to_game_record(fake_eul_home_row, fake_eul_away_row)
    assert isinstance(rec, GameRecord)
    assert rec.home_team == "RM"
    assert rec.away_team == "FB"
    assert rec.home_score == 85
    assert rec.away_score == 79
    assert rec.league == "euroleague"
    # FIBA possessions: 70 + 0.46 × 18 - 9 + 11 = 80.28
    assert abs(rec.home_possessions - 80.28) < 0.01


def test_fetch_empty_endpoint_returns_empty_list():
    fake_endpoint = MagicMock()
    fake_endpoint.return_value.get_game_stats.return_value = []
    games = fetch_game_log_via_euroleague_api(
        season="2024", endpoint_factory=fake_endpoint,
    )
    assert games == []


def test_fetch_uses_fiba_possessions_factor():
    """FIBA 0.46 NBA 0.44'ten yüksek → aynı veride daha fazla possessions."""
    fake_endpoint = MagicMock()
    fake_endpoint.return_value.get_game_stats.return_value = [
        {"Gamecode": "1", "Season": 2024, "Date": "2024-10-15T00:00:00Z",
         "TeamCode": "RM", "Points": 85, "FieldGoalsAttempted": 70,
         "FreeThrowsAttempted": 20, "OffensiveRebounds": 9, "Turnovers": 11,
         "HomeAway": "home"},
        {"Gamecode": "1", "Season": 2024, "Date": "2024-10-15T00:00:00Z",
         "TeamCode": "FB", "Points": 79, "FieldGoalsAttempted": 68,
         "FreeThrowsAttempted": 20, "OffensiveRebounds": 8, "Turnovers": 13,
         "HomeAway": "away"},
    ]
    games = fetch_game_log_via_euroleague_api(season="2024", endpoint_factory=fake_endpoint)
    assert len(games) == 1
    # FIBA: 70 + 0.46 × 20 - 9 + 11 = 81.2 (NBA 0.44 olsaydı 80.8 olurdu)
    assert abs(games[0].home_possessions - 81.2) < 0.01


def test_fetch_eurocup_uses_competition_code_U():
    """Task 6: EuroCup competition='eurocup' → competition_code='U'."""
    fake = MagicMock()
    fake.return_value.get_game_stats.return_value = []
    fetch_game_log_via_euroleague_api(
        season="2024", endpoint_factory=fake, competition="eurocup",
    )
    fake.assert_called_once_with(season="2024", competition_code="U")


def test_fetch_euroleague_default_competition_code_E():
    """Task 6: Euroleague default → competition_code='E'."""
    fake = MagicMock()
    fake.return_value.get_game_stats.return_value = []
    fetch_game_log_via_euroleague_api(season="2024", endpoint_factory=fake)
    fake.assert_called_once_with(season="2024", competition_code="E")


def test_fetch_unknown_competition_raises():
    """Task 6: Bilinmeyen competition → ValueError fail-fast."""
    fake = MagicMock()
    with pytest.raises(ValueError, match="competition"):
        fetch_game_log_via_euroleague_api(
            season="2024", endpoint_factory=fake, competition="basketball_champions_league",
        )


def test_eurocup_games_have_eurocup_league_field(fake_eul_home_row, fake_eul_away_row):
    """Task 6: EuroCup oyunlarında GameRecord.league = 'eurocup' (Euroleague değil)."""
    fake = MagicMock()
    fake.return_value.get_game_stats.return_value = [fake_eul_home_row, fake_eul_away_row]
    games = fetch_game_log_via_euroleague_api(
        season="2024", endpoint_factory=fake, competition="eurocup",
    )
    assert len(games) == 1
    assert games[0].league == "eurocup"


def test_fetch_unpaired_game_skipped():
    """Tek satır (eksik away) → atla + warning."""
    fake_endpoint = MagicMock()
    fake_endpoint.return_value.get_game_stats.return_value = [
        {"Gamecode": "X", "Season": 2024, "Date": "2024-10-15T00:00:00Z",
         "TeamCode": "RM", "Points": 85, "FieldGoalsAttempted": 70,
         "FreeThrowsAttempted": 20, "OffensiveRebounds": 9, "Turnovers": 11,
         "HomeAway": "home"},
    ]
    games = fetch_game_log_via_euroleague_api(season="2024", endpoint_factory=fake_endpoint)
    assert games == []
