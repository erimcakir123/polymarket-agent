"""Basketball team resolver — Polymarket slug ↔ NBA team abbreviation."""
from __future__ import annotations
import pytest
from src.domain.matching.basketball_team_resolver import (
    resolve_team_pair, ResolveResult,
)


def test_resolve_nba_standard_slug():
    res = resolve_team_pair("nba-lal-gsw-2024-11-01", league="nba")
    assert res.home == "LAL"
    assert res.away == "GSW"
    assert res.ok is True


def test_resolve_handles_full_team_names():
    """Bazı Polymarket slug'larda "lakers-warriors" pattern var."""
    res = resolve_team_pair("nba-lakers-vs-warriors-2024-11-01", league="nba")
    assert res.home == "LAL"
    assert res.away == "GSW"


def test_resolve_wnba_abbreviation():
    res = resolve_team_pair("wnba-lva-nyl-2024-08-15", league="wnba")
    assert res.home == "LVA"
    assert res.away == "NYL"


def test_resolve_unknown_team_returns_not_ok():
    res = resolve_team_pair("nba-xxx-yyy-2024-11-01", league="nba")
    assert res.ok is False
    assert res.fail_reason is not None
