"""sport_key_resolver.py için birim testler."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.strategy.enrichment.sport_key_resolver import resolve_sport_key


def _client(sports=None, events=None) -> MagicMock:
    c = MagicMock()
    c.get_sports.return_value = sports or []
    c.get_events.return_value = events or []
    return c


def test_static_slug_mapping_wins() -> None:
    # 'nba-lal-bos-...' → basketball_nba (static tablodan)
    client = _client()
    result = resolve_sport_key("Will Lakers beat Celtics?", "nba-lal-bos-2026-04-13", [], client)
    assert result == "basketball_nba"
    # Odds client hiç çağrılmamalı (static mapping sufficient)
    client.get_sports.assert_not_called()


def test_static_tag_mapping_fallback() -> None:
    # Slug bilinmez, tag 'premier-league' static'ten soccer_epl döner
    client = _client()
    result = resolve_sport_key("Match Q", "unknown-slug-2026", ["premier-league"], client)
    assert result == "soccer_epl"


def test_tennis_dynamic_single_key() -> None:
    # ATP, 1 aktif turnuva
    client = _client(sports=[
        {"key": "tennis_atp_miami_open", "active": True},
        {"key": "tennis_wta_miami_open", "active": True},
        {"key": "other_sport", "active": True},
    ])
    result = resolve_sport_key("Will Djokovic win?", "atp-djoko-2026", [], client)
    assert result == "tennis_atp_miami_open"


def test_tennis_dynamic_tournament_match() -> None:
    # Birden çok key, slug/question'da 'french' geçiyor
    client = _client(sports=[
        {"key": "tennis_atp_miami_open", "active": True},
        {"key": "tennis_atp_french_open", "active": True},
    ])
    result = resolve_sport_key("ATP French Open: Djokovic", "atp-french-djoko-2026", [], client)
    assert result == "tennis_atp_french_open"


def test_tennis_wta_routing() -> None:
    client = _client(sports=[
        {"key": "tennis_atp_miami_open", "active": True},
        {"key": "tennis_wta_miami_open", "active": True},
    ])
    result = resolve_sport_key("WTA Miami: Will Swiatek win?", "wta-swiatek", [], client)
    assert result == "tennis_wta_miami_open"


def test_discovery_fallback() -> None:
    # Static yok, tennis değil, event listesinde takım ara
    client = _client(
        sports=[{"key": "custom_sport", "active": True}],
        events=[{"home_team": "Custom Team A", "away_team": "Custom Team B"}],
    )
    result = resolve_sport_key("Will Custom Team A beat Custom Team B?", "custom-a-b", [], client)
    assert result == "custom_sport"


def test_no_match_returns_none() -> None:
    client = _client(sports=[{"key": "s1", "active": True}], events=[])
    result = resolve_sport_key("Random Q", "xyz-unknown", [], client)
    # Static yok, tennis yok, events empty → None
    assert result is None
