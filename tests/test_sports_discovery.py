"""Tests for SportsDiscovery routing and resolution."""
from unittest.mock import MagicMock
import pytest

from src.sports_discovery import SportsDiscovery, DiscoveryResult


def _make_discovery(espn_ctx=None, panda_ctx=None, cricket_ctx=None):
    espn = MagicMock()
    espn.get_match_context = MagicMock(return_value=espn_ctx)
    espn.get_espn_odds = MagicMock(return_value=None)
    espn.search_team = MagicMock(return_value=("soccer", "eng.3") if espn_ctx else None)

    panda = MagicMock()
    panda.available = True
    panda.get_match_context = MagicMock(return_value=panda_ctx)

    cricket = MagicMock()
    cricket.available = True
    cricket.get_match_context = MagicMock(return_value=cricket_ctx)

    odds = MagicMock()
    odds.available = False

    return SportsDiscovery(espn=espn, pandascore=panda, cricket=cricket, odds_api=odds)


def test_route_esports_by_tag():
    d = _make_discovery()
    route = d._detect_route("Fnatic vs G2", "cs2-fnatic-g2", ["esports", "cs2"])
    assert route == "esports"


def test_route_esports_by_slug():
    d = _make_discovery()
    route = d._detect_route("Fnatic vs G2", "cs2-fnatic-g2", [])
    assert route == "esports"


def test_route_cricket_by_tag():
    d = _make_discovery()
    route = d._detect_route("India vs Pakistan", "ipl-ind-pak", ["cricket"])
    assert route == "cricket"


def test_route_cricket_by_slug():
    d = _make_discovery()
    route = d._detect_route("India vs Pakistan", "ipl-ind-pak", [])
    assert route == "cricket"


def test_route_default_espn():
    d = _make_discovery()
    route = d._detect_route("Lakers vs Celtics", "nba-lakers-celtics", ["sports"])
    assert route == "espn"


def test_resolve_espn_returns_context():
    d = _make_discovery(espn_ctx="=== ESPN DATA ===")
    result = d.resolve("Lakers vs Celtics", "nba-lakers-celtics", ["sports"])
    assert result is not None
    assert "=== ESPN DATA ===" in result.context
    assert result.source == "ESPN"


def test_resolve_cricket_returns_context():
    d = _make_discovery(cricket_ctx="=== CRICKET DATA ===")
    result = d.resolve("India vs Pakistan", "ipl-ind-pak", ["cricket"])
    assert result is not None
    assert result.context == "=== CRICKET DATA ==="
    assert result.source == "CricketData"


def test_resolve_returns_none_when_no_data():
    d = _make_discovery()  # all return None
    result = d.resolve("Unknown vs Team", "xyz-unk-team", ["sports"])
    assert result is None
