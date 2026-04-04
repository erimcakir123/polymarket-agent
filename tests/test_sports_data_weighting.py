"""Tests for ESPN odds sharp bookmaker weighting in sports_data.py."""
from unittest.mock import MagicMock


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
