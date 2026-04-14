"""sport_classifier.py için birim testler."""
from __future__ import annotations

from src.domain.matching.sport_classifier import classify_sport


def test_slug_prefix_nba_returns_basketball() -> None:
    assert classify_sport(slug="nba-lal-bos-2026-04-13") == "basketball"


def test_slug_prefix_mlb_returns_baseball() -> None:
    assert classify_sport(slug="mlb-nyy-bos-2026-04-13") == "baseball"


def test_slug_prefix_nhl_returns_hockey() -> None:
    assert classify_sport(slug="nhl-nyr-bos-2026-04-13") == "hockey"


def test_slug_prefix_nfl_returns_football() -> None:
    assert classify_sport(slug="nfl-kc-buf-2026-04-13") == "football"


def test_slug_prefix_soccer_epl() -> None:
    assert classify_sport(slug="epl-manu-liv-2026-04-13") == "soccer"


def test_sport_tag_fallback() -> None:
    # Bilinmeyen slug, ama sport_tag nba
    assert classify_sport(slug="random-match-2026", sport_tag="nba") == "basketball"


def test_question_keyword_fallback() -> None:
    assert classify_sport(slug="", question="Will Lakers beat Celtics in NBA Finals?") == "basketball"


def test_unknown_returns_none() -> None:
    assert classify_sport(slug="xyz-random", sport_tag="unknown", question="No hint") is None


def test_empty_inputs_return_none() -> None:
    assert classify_sport() is None
    assert classify_sport("", "", "") is None


def test_tennis_atp() -> None:
    assert classify_sport(slug="atp-djokovic-alcaraz-2026") == "tennis"


def test_golf_lpga() -> None:
    assert classify_sport(slug="lpga-korda-2026") == "golf"
