"""ScoreEnricher sport-dispatch + fallback testleri (SPEC-B Task 3)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import ScoreConfig
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.models.position import Position
from src.orchestration.score_enricher import ScoreEnricher


def _pos(slug: str = "test", sport_tag: str = "nhl", current_price: float = 0.50,
         question: str = "Will Maple Leafs beat Bruins?") -> Position:
    return Position(
        condition_id=slug, token_id=slug, direction="BUY_YES",
        entry_price=0.4, size_usdc=50.0, shares=125.0,
        current_price=current_price, anchor_probability=0.5,
        event_id=f"e_{slug}", slug=slug, sport_tag=sport_tag,
        question=question,
    )


def _espn_score(event_id: str = "1", home: str = "Maple Leafs", away: str = "Bruins",
                home_score: int = 2, away_score: int = 1, is_live: bool = True) -> ESPNMatchScore:
    return ESPNMatchScore(
        event_id=event_id, home_name=home, away_name=away,
        home_score=home_score, away_score=away_score,
        is_live=is_live, period="In Progress",
    )


# -- Disabled gate --

def test_enricher_disabled_returns_empty() -> None:
    espn = MagicMock()
    odds = MagicMock()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        config=ScoreConfig(enabled=False),
    )
    positions = {"a": _pos("a")}
    result = enricher.get_scores_if_due(positions)
    assert result == {}
    espn.fetch_scoreboard.assert_not_called()


def test_enricher_empty_positions_returns_empty() -> None:
    espn = MagicMock()
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    result = enricher.get_scores_if_due({})
    assert result == {}
    espn.fetch_scoreboard.assert_not_called()


# -- Sport dispatch --

def test_enricher_dispatches_to_espn_for_nhl() -> None:
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = [_espn_score("nhl1", "Maple Leafs", "Bruins")]
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"a": _pos("a", sport_tag="nhl")}
    result = enricher.get_scores_if_due(positions)
    espn.fetch_scoreboard.assert_called()
    args, kwargs = espn.fetch_scoreboard.call_args
    sport_arg = args[0] if args else kwargs.get("sport")
    league_arg = args[1] if len(args) > 1 else kwargs.get("league")
    assert sport_arg == "hockey"
    assert league_arg == "nhl"


def test_enricher_dispatches_to_espn_for_mlb() -> None:
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = []
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"b": _pos("b", sport_tag="mlb", question="Will Yankees beat Red Sox?")}
    enricher.get_scores_if_due(positions)
    args, kwargs = espn.fetch_scoreboard.call_args
    sport_arg = args[0] if args else kwargs.get("sport")
    assert sport_arg == "baseball"


def test_enricher_skips_unsupported_sport() -> None:
    """Sport_tag golf/mma/boxing -> ESPN cagrilmaz (score_source yok)."""
    espn = MagicMock()
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    positions = {"g": _pos("g", sport_tag="golf")}
    result = enricher.get_scores_if_due(positions)
    assert result == {}
    espn.fetch_scoreboard.assert_not_called()


# -- Polling throttle --

def test_enricher_normal_polling_respects_interval() -> None:
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = []
    odds = MagicMock()
    enricher = ScoreEnricher(
        espn_client=espn, odds_client=odds,
        config=ScoreConfig(poll_normal_sec=60, poll_critical_sec=30, critical_price_threshold=0.35),
    )
    positions = {"a": _pos("a", sport_tag="nhl", current_price=0.5)}  # > threshold
    enricher.get_scores_if_due(positions)
    enricher.get_scores_if_due(positions)
    # Ikinci cagri interval alti -> skip
    assert espn.fetch_scoreboard.call_count == 1


# -- Score mapping --

def test_enricher_maps_score_info_for_matched_position() -> None:
    """ESPN skor pozisyona match olursa score_info dogru doner."""
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = [
        _espn_score("nhl1", "Maple Leafs", "Bruins", home_score=3, away_score=1),
    ]
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    pos = _pos("a", sport_tag="nhl", question="Will Maple Leafs beat Bruins?")
    result = enricher.get_scores_if_due({"a": pos})
    assert "a" in result
    info = result["a"]
    assert info["available"] is True
    # "Maple Leafs" question'da -> us=home -> our=3, opp=1
    assert info["our_score"] == 3
    assert info["opp_score"] == 1
    assert info["map_diff"] == 2
    assert info["deficit"] == 0


def test_enricher_skips_completed_match() -> None:
    """is_live=False -> skor map'e dahil edilmez."""
    espn = MagicMock()
    espn.fetch_scoreboard.return_value = [
        _espn_score("done", "Maple Leafs", "Bruins", is_live=False),
    ]
    odds = MagicMock()
    enricher = ScoreEnricher(espn_client=espn, odds_client=odds, config=ScoreConfig())
    pos = _pos("a", sport_tag="nhl", question="Will Maple Leafs beat Bruins?")
    result = enricher.get_scores_if_due({"a": pos})
    assert result == {}
