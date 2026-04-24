"""PLAN-012: SoccerLeagueDiscovery tests."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.persistence.soccer_league_cache import SoccerLeagueCache
from src.orchestration.soccer_league_discovery import SoccerLeagueDiscovery


# ── Fixtures ─────────────────────────────────────────────────────────────

def _make_pos(slug: str, question: str):
    pos = MagicMock()
    pos.slug = slug
    pos.question = question
    return pos


def _espn_score(home: str, away: str) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id="1", home_name=home, away_name=away,
        home_score=0, away_score=0, period="", is_completed=False,
        is_live=True, last_updated="",
    )


@pytest.fixture
def cache(tmp_path: Path) -> SoccerLeagueCache:
    return SoccerLeagueCache(cache_path=tmp_path / "cache.json", ttl_hours=24)


@pytest.fixture
def leagues_fetcher():
    """fetch_soccer_leagues mock — returns full 250 league list (trimmed)."""
    return MagicMock(return_value=[
        "arg.1", "arg.2", "arg.copa",
        "rus.1", "rus.1.promotion.relegation",
        "eng.1", "eng.2", "esp.1",
        "uefa.champions", "uefa.europa",
    ])


@pytest.fixture
def espn_fetcher():
    """espn_client.fetch mock — league slug'e göre farklı dönüş."""
    def fetch(sport: str, league: str):
        lookup = {
            "rus.1": [_espn_score("Sochi", "Krylia Sovetov")],
            "arg.1": [_espn_score("Defensa y Justicia", "Boca Juniors")],
            "arg.2": [_espn_score("CA Platense", "CA Central Cordoba")],
            "arg.copa": [],
            "eng.1": [_espn_score("Manchester City", "Arsenal")],
        }
        return lookup.get(league, [])
    return MagicMock(side_effect=fetch)


# ── Testler ──────────────────────────────────────────────────────────────

class TestLearnedCacheHit:
    def test_returns_cached_league_without_http_calls(self, cache, leagues_fetcher, espn_fetcher):
        cache.set_learned("rus", "PFK Krylia Sovetov Samara", "rus.1")
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos(
            "rus-soc-kss-2026-04-21-kss",
            "Will PFK Krylia Sovetov Samara win on 2026-04-21?",
        )
        assert disc.discover(pos) == "rus.1"
        # 0 HTTP calls
        leagues_fetcher.assert_not_called()
        espn_fetcher.assert_not_called()


class TestFirstTimeDiscovery:
    def test_finds_correct_league_by_team_match(self, cache, leagues_fetcher, espn_fetcher):
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos(
            "rus-soc-kss-2026-04-21-kss",
            "Will PFK Krylia Sovetov Samara win on 2026-04-21?",
        )
        assert disc.discover(pos) == "rus.1"

    def test_writes_to_learned_cache(self, cache, leagues_fetcher, espn_fetcher):
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos(
            "rus-soc-kss-2026-04-21-kss",
            "Will PFK Krylia Sovetov Samara win on 2026-04-21?",
        )
        disc.discover(pos)
        assert cache.get_learned("rus", "PFK Krylia Sovetov Samara") == "rus.1"

    def test_prefers_arg_2_when_team_only_in_second_tier(self, cache, leagues_fetcher, espn_fetcher):
        """arg.1 → Def y Jus / Boca. arg.2 → Platense → bizim maç arg.2."""
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos(
            "arg-cac-pla-2026-04-20-pla",
            "Will CA Platense win on 2026-04-20?",
        )
        # Platense arg.2'de, arg.1'de yok → discovery arg.2'yi bulmalı
        assert disc.discover(pos) == "arg.2"


class TestNoMatch:
    def test_unknown_team_returns_none(self, cache, leagues_fetcher, espn_fetcher):
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos("arg-xxx-yyy-2026", "Will Nonexistent FC win?")
        assert disc.discover(pos) is None

    def test_unknown_prefix_returns_none_without_fetch(self, cache, leagues_fetcher, espn_fetcher):
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos("zzz-foo-bar", "Will ZZZ FC win?")
        assert disc.discover(pos) is None
        # prefix zzz için league listesinde eşleşme yok → espn fetch'e hiç gitmez
        espn_fetcher.assert_not_called()


class TestLeaguesFetchFailure:
    def test_empty_leagues_list_returns_none(self, cache, espn_fetcher):
        failing = MagicMock(return_value=[])
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=failing,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos("rus-soc-kss", "Will Krylia Sovetov win?")
        assert disc.discover(pos) is None


class TestEmptyPosition:
    def test_empty_slug_returns_none(self, cache, leagues_fetcher, espn_fetcher):
        disc = SoccerLeagueDiscovery(
            leagues_fetcher=leagues_fetcher,
            espn_fetcher=espn_fetcher,
            cache=cache,
        )
        pos = _make_pos("", "Will X win?")
        assert disc.discover(pos) is None
