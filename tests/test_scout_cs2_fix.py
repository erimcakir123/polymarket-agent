"""Verify CS2 slug fix — PandaScore uses 'csgo' not 'cs2'."""
import pytest


def test_esport_games_uses_csgo_slug():
    """_ESPORT_GAMES must use 'csgo' (PandaScore's slug), not 'cs2'."""
    from src.scout_scheduler import _ESPORT_GAMES
    assert "csgo" in _ESPORT_GAMES, "CS2 must use 'csgo' slug for PandaScore API"
    assert "cs2" not in _ESPORT_GAMES, "'cs2' is not a valid PandaScore game slug"


def test_esport_games_contains_all_games():
    """All four main esports games must be present."""
    from src.scout_scheduler import _ESPORT_GAMES
    expected = {"csgo", "lol", "dota2", "valorant"}
    assert set(_ESPORT_GAMES) == expected
