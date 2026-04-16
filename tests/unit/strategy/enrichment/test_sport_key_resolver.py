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


def test_tennis_wta_slug_prefix_wins_when_question_lacks_wta_token() -> None:
    """Regression: slug 'wta-...' prefix'i, question'da 'tennis' geçip 'wta'
    geçmese bile ATP'ye yönlendirmemeli. Bug: Porsche Tennis Grand Prix
    (WTA Stuttgart) → ATP Barcelona key dönüyordu."""
    client = _client(sports=[
        {"key": "tennis_atp_barcelona_open", "active": True},
        {"key": "tennis_wta_stuttgart_open", "active": True},
    ])
    result = resolve_sport_key(
        "Porsche Tennis Grand Prix: Eva Lys vs Elina Svitolina",
        "wta-lys-svitoli-2026-04-15", [], client,
    )
    assert result == "tennis_wta_stuttgart_open"


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


# --- SPEC-002: remove keys[0] fallback in _match_tennis_key ---


def test_match_tennis_key_no_score_no_tourney_match_returns_none():
    """Multiple active tennis_atp keys, nothing in question/slug matches → None.

    Previously returned keys[0] (first active key), which mapped unknown
    tournaments (Oeiras, Tallahassee, BMW Open) to Barcelona Open in April 2026
    and caused misleading event_no_match skips. Fix: honest None signal.
    """
    from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

    class FakeClient:
        def get_sports(self, include_inactive=False):
            return [
                {"key": "tennis_atp_barcelona_open", "active": True},
                {"key": "tennis_atp_monte_carlo", "active": True},
            ]

        def get_events(self, sport_key):
            return []

        def get_odds(self, sport_key, params=None):
            return []

    # Question and slug contain none of: barcelona, monte, carlo, open
    result = resolve_sport_key(
        question="Oeiras 3: Ali Veli vs Ahmet Mehmet",
        slug="atp-ali-ahmet-2026-04-16",
        tags=[],
        odds_client=FakeClient(),
    )
    assert result is None


# --- SPEC-003: sponsor→city alias augmentation ---


def test_match_tennis_key_bmw_open_resolves_to_munich():
    """Polymarket 'BMW Open: ...' → Odds API 'tennis_atp_munich' correctly mapped."""
    from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

    class FakeClient:
        def get_sports(self, include_inactive=False):
            return [
                {"key": "tennis_atp_barcelona_open", "active": True},
                {"key": "tennis_atp_munich", "active": True},
            ]

        def get_events(self, sport_key):
            return []

        def get_odds(self, sport_key, params=None):
            return []

    result = resolve_sport_key(
        question="BMW Open: Alexander Zverev vs Gabriel Diallo",
        slug="atp-zverev-diallo-2026-04-15",
        tags=[],
        odds_client=FakeClient(),
    )
    assert result == "tennis_atp_munich"


def test_match_tennis_key_porsche_tt_resolves_to_stuttgart_open():
    """Polymarket 'Porsche Tennis Grand Prix: ...' → 'tennis_wta_stuttgart_open'."""
    from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

    class FakeClient:
        def get_sports(self, include_inactive=False):
            return [
                {"key": "tennis_wta_stuttgart_open", "active": True},
                {"key": "tennis_wta_dubai", "active": True},
            ]

        def get_events(self, sport_key):
            return []

        def get_odds(self, sport_key, params=None):
            return []

    result = resolve_sport_key(
        question="Porsche Tennis Grand Prix: Ekaterina Alexandrova vs Linda Noskova",
        slug="wta-alexand-noskov-2026-04-16",
        tags=[],
        odds_client=FakeClient(),
    )
    assert result == "tennis_wta_stuttgart_open"


def test_match_tennis_key_barcelona_open_still_resolves_without_alias():
    """Regresyon: Barcelona Open already city-matches — augmentation is not
    triggered by alias table, existing score-based match still wins."""
    from src.strategy.enrichment.sport_key_resolver import resolve_sport_key

    class FakeClient:
        def get_sports(self, include_inactive=False):
            return [
                {"key": "tennis_atp_barcelona_open", "active": True},
                {"key": "tennis_atp_munich", "active": True},
            ]

        def get_events(self, sport_key):
            return []

        def get_odds(self, sport_key, params=None):
            return []

    result = resolve_sport_key(
        question="Barcelona Open: Cameron Norrie vs Rafael Jodar",
        slug="atp-norrie-jodar-2026-04-17",
        tags=[],
        odds_client=FakeClient(),
    )
    assert result == "tennis_atp_barcelona_open"
