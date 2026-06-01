"""BRScraper wrapper — Avrupa yerel ligler (BSL/ACB/Lega) testleri."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.data.basketball.brscraper_refresher import (
    _SUPPORTED_BR_LEAGUES,
    fetch_european_league_games,
)


def _row(home: str = "ANA", away: str = "FB",
         hs: int = 90, as_: int = 85) -> dict:
    """Helper — geçerli BRScraper satırı."""
    return {
        "date": "2024-11-01",
        "season": "2024-25",
        "home_team_abbr": home,
        "away_team_abbr": away,
        "home_points": hs,
        "away_points": as_,
        "home_fga": 70, "away_fga": 68,
        "home_fta": 20, "away_fta": 18,
        "home_orb": 10, "away_orb": 9,
        "home_tov": 12, "away_tov": 11,
    }


def test_supported_european_leagues_listed():
    assert "bsl" in _SUPPORTED_BR_LEAGUES
    assert "acb" in _SUPPORTED_BR_LEAGUES
    assert "lega" in _SUPPORTED_BR_LEAGUES


def test_fetch_unknown_league_raises():
    with pytest.raises(ValueError, match="European league"):
        fetch_european_league_games(
            league="bundesliga_basketball", season="2024-25", fetcher=MagicMock(),
        )


def test_fetch_empty_result_returns_empty_list():
    fake = MagicMock(return_value=[])
    games = fetch_european_league_games(league="bsl", season="2024-25", fetcher=fake)
    assert games == []


def test_fetch_valid_row_produces_game_record():
    fake = MagicMock(return_value=[_row("ANA", "FB", 90, 85)])
    games = fetch_european_league_games(league="bsl", season="2024-25", fetcher=fake)
    assert len(games) == 1
    rec = games[0]
    assert rec.home_team == "ANA"
    assert rec.away_team == "FB"
    assert rec.home_score == 90
    assert rec.league == "bsl"
    # FIBA possessions: 70 + 0.46 × 20 - 10 + 12 = 81.2
    assert abs(rec.home_possessions - 81.2) < 0.01


def test_fetch_skips_unparseable_rows():
    """Bozuk satır → log warning + skip (sessiz hata YASAK)."""
    fake = MagicMock(return_value=[
        _row("ANA", "FB"),
        {"date": "BOZUK", "home_team_abbr": None},  # malformed
    ])
    games = fetch_european_league_games(league="bsl", season="2024-25", fetcher=fake)
    assert len(games) == 1
    assert games[0].home_team == "ANA"


def test_fetch_network_exception_returns_empty_no_raise():
    """Fetcher exception fırlattığında: log + empty list (NO DATA → NO TRADE)."""
    fake = MagicMock(side_effect=ConnectionError("captcha or block"))
    games = fetch_european_league_games(league="acb", season="2024-25", fetcher=fake)
    assert games == []


def test_fetch_acb_and_lega_also_supported():
    fake = MagicMock(return_value=[_row("RM", "FCB", 80, 75)])
    g1 = fetch_european_league_games(league="acb", season="2024-25", fetcher=fake)
    assert g1[0].league == "acb"
    g2 = fetch_european_league_games(league="lega", season="2024-25", fetcher=fake)
    assert g2[0].league == "lega"
