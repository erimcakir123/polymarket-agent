"""Tests for MlbSubmarketEngine team-matching logic (A4).

Verifies that process() picks the schedule game whose home/away team_ids
match the abbreviations parsed from the slug — not simply schedule[0].
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import MlbSubmarketConfig
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def _make_market(slug: str, yes_price: float = 0.5) -> MagicMock:
    m = MagicMock(spec=["condition_id", "event_id", "slug", "yes_price"])
    m.condition_id = "cid-test"
    m.event_id = "evt-test"
    m.slug = slug
    m.yes_price = yes_price
    return m


def _make_engine(schedule_return):
    statsapi = MagicMock()
    statsapi.get_schedule.return_value = schedule_return
    statsapi.get_lineup.return_value = {"home": [], "away": []}
    engine = MlbSubmarketEngine(
        statsapi=statsapi,
        statcast=MagicMock(),
        weather=MagicMock(),
        rate_cache=MagicMock(),
        config=MlbSubmarketConfig(enabled=True, min_edge=0.05),
        ballpark_metadata={"FAKE": {"lat": 0, "lon": 0, "cf_orientation_deg": 0, "park_id": "FAKE"}},
    )
    return engine, statsapi


def test_process_picks_game_matching_slug_teams():
    # slug = mlb-cle-phi-2026-05-22: away=cle(114), home=phi(143)
    # schedule[0] has non-matching IDs; schedule[1] matches → lineup called with 222
    schedule = [
        {"gamePk": 111, "home_team_id": 999, "away_team_id": 999, "status": "Scheduled"},
        {"gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled"},
    ]
    engine, statsapi = _make_engine(schedule)
    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    engine.process(market)
    statsapi.get_lineup.assert_called_with(222)


def test_process_returns_none_when_no_team_match():
    # schedule only has a game with IDs that don't match cle/phi
    schedule = [
        {"gamePk": 111, "home_team_id": 999, "away_team_id": 999, "status": "Scheduled"},
    ]
    engine, statsapi = _make_engine(schedule)
    market = _make_market("mlb-cle-phi-2026-05-22-total-8pt5")
    result = engine.process(market)
    assert result is None
    statsapi.get_lineup.assert_not_called()


def test_process_returns_none_for_unknown_abbreviation():
    # 'zzz' not in TEAM_ABBREVIATIONS → engine returns None before fetching lineup
    schedule = [
        {"gamePk": 222, "home_team_id": 143, "away_team_id": 114, "status": "Scheduled"},
    ]
    engine, statsapi = _make_engine(schedule)
    market = _make_market("mlb-zzz-phi-2026-05-22-total-8pt5")
    result = engine.process(market)
    assert result is None
    statsapi.get_lineup.assert_not_called()
