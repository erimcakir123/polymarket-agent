"""Tests for ESPN odds sharp bookmaker weighting in sports_data.py."""
from unittest.mock import MagicMock

import pytest


def _make_odds_response(providers_odds: list) -> dict:
    """Build a fake ESPN odds API response from a list of (provider_name, home_odds, away_odds)."""
    return {
        "items": [
            {
                "provider": {"name": name},
                "homeTeamOdds": {"current": {"moneyLine": {"decimal": h}}},
                "awayTeamOdds": {"current": {"moneyLine": {"decimal": a}}},
            }
            for name, h, a in providers_odds
        ]
    }


def _patch_client(monkeypatch, client, team_a: str, team_b: str, fake_resp):
    monkeypatch.setattr(client, "detect_sport", lambda *a, **k: ("basketball", "nba"))
    monkeypatch.setattr(client, "_extract_teams_from_question", lambda *a, **k: (team_a, team_b))
    monkeypatch.setattr(client, "_extract_teams_from_slug", lambda *a, **k: (team_a, team_b))
    monkeypatch.setattr(client, "_find_espn_event", lambda *a, **k: (
        "evt1", "comp1", team_a, team_b, True
    ))
    monkeypatch.setattr("src.sports_data.requests.get", lambda *a, **k: fake_resp)
    monkeypatch.setattr(client, "_rate_limit", lambda: None)


def test_espn_odds_applies_sharp_weight(monkeypatch):
    """Bet365 (weight 1.5) should pull the average toward its value vs DraftKings (1.0)."""
    from src.sports_data import SportsDataClient

    client = SportsDataClient()

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = _make_odds_response([
        ("DraftKings", 1.4286, 3.3333),
        ("Bet365", 1.4706, 3.125),
    ])

    _patch_client(monkeypatch, client, "Lakers", "Celtics", fake_resp)

    result = client.get_espn_odds("Lakers vs Celtics", "lakers-vs-celtics", [])
    assert result is not None
    assert result["total_weight"] == 2.5
    assert result["num_bookmakers"] == 2
    assert 0.685 <= result["bookmaker_prob_a"] <= 0.695


def test_espn_odds_has_sharp_false_for_retail_only(monkeypatch):
    """has_sharp should be False when no sharp book is in the ESPN response."""
    from src.sports_data import SportsDataClient

    client = SportsDataClient()

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = _make_odds_response([
        ("DraftKings", 1.90, 2.00),
    ])

    _patch_client(monkeypatch, client, "Yankees", "Red Sox", fake_resp)

    result = client.get_espn_odds("Yankees vs Red Sox", "yankees-vs-red-sox", [])
    assert result is not None
    assert result["has_sharp"] is False
    assert result["total_weight"] == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Question parser tests (Monte Carlo / tournament-prefix bug fix)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("question,expected_a,expected_b", [
    # Existing short-prefix behavior preserved
    ("NBA: Lakers vs Warriors", "Lakers", "Warriors"),
    ("MLB: Yankees vs Red Sox", "Yankees", "Red Sox"),
    ("KHL: SKA vs CSKA", "SKA", "CSKA"),
    ("Will the Lakers beat the Warriors?", "Lakers", "Warriors"),
    ("Real Madrid vs Barcelona", "Real Madrid", "Barcelona"),
    ("A vs B: O/U 238.5", "A", "B"),

    # Monte Carlo bug fix — multi-word tournament prefix with colon
    (
        "Rolex Monte Carlo Masters: Matteo Berrettini vs Joao Fonseca",
        "Matteo Berrettini",
        "Joao Fonseca",
    ),
    (
        "Rolex Monte Carlo Masters: Felix Auger-Aliassime vs Casper Ruud",
        "Felix Auger-Aliassime",
        "Casper Ruud",
    ),
    (
        "Rolex Monte Carlo Masters: Alexander Blockx vs Alex de Minaur",
        "Alexander Blockx",
        "Alex de Minaur",
    ),
    (
        "Rolex Monte Carlo Masters: Tomas Machac vs Jannik Sinner",
        "Tomas Machac",
        "Jannik Sinner",
    ),

    # Challenger city prefixes (single-word)
    ("Campinas: Gonzalo Bueno vs Lucio Ratti", "Gonzalo Bueno", "Lucio Ratti"),
    ("Wuning: Li Tu vs Alastair Gray", "Li Tu", "Alastair Gray"),
    (
        "Campinas: Guido Justo vs Juan Manuel La Serna",
        "Guido Justo",
        "Juan Manuel La Serna",
    ),

    # Bonus fix — other sports with multi-word prefixes
    ("Premier League: Arsenal vs Chelsea", "Arsenal", "Chelsea"),
    ("UFC 300: Jones vs Miocic", "Jones", "Miocic"),
    (
        "Champions League Final: Real Madrid vs Liverpool",
        "Real Madrid",
        "Liverpool",
    ),

    # Nested colons
    ("Masters: Round 1: Sinner vs Alcaraz", "Sinner", "Alcaraz"),

    # Single-player "win" / "be the winner" patterns
    ("Will Jannik Sinner win the 2026 French Open?", "Jannik Sinner", None),
    (
        "Will Carlos Alcaraz be the 2026 Wimbledon winner?",
        "Carlos Alcaraz",
        None,
    ),
])
def test_extract_teams_from_question(question, expected_a, expected_b):
    """Parser handles tournament prefixes, nested colons, and winner patterns."""
    from src.sports_data import SportsDataClient

    client = SportsDataClient()
    a, b = client._extract_teams_from_question(question)
    assert a == expected_a, f"team_a mismatch for {question!r}: got {a!r}"
    assert b == expected_b, f"team_b mismatch for {question!r}: got {b!r}"


@pytest.mark.parametrize("name,expected", [
    # Should be detected as tournament
    ("Rolex Monte Carlo Masters", True),
    ("Monte Carlo Masters", True),
    ("French Open", True),
    ("ATP 500 Dubai", True),       # "atp 500" keyword matches (case-insensitive)
    ("Grand Slam Cup", True),
    ("Wimbledon Championships", True),
    ("US Open", True),
    ("Madrid Open", True),
    # Should NOT be detected (actual player/team names)
    ("Jannik Sinner", False),
    ("Carlos Alcaraz", False),
    ("Real Madrid", False),         # no tournament keyword
    ("Alex de Minaur", False),
    ("", False),
    ("A", False),                   # too short
    ("Cup", False),                 # single word, even with keyword
])
def test_looks_like_tournament(name, expected):
    """Tournament name detector is conservative: keyword + 2+ words required."""
    from src.sports_data import _looks_like_tournament

    assert _looks_like_tournament(name) is expected, (
        f"_looks_like_tournament({name!r}) expected {expected}"
    )
