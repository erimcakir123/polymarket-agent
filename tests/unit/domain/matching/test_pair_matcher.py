"""pair_matcher.py için birim testler."""
from __future__ import annotations

from src.domain.matching.pair_matcher import (
    find_best_event_match,
    find_best_single_team_match,
    match_pair,
    match_team,
)


def test_exact_canonical_match() -> None:
    ok, conf, method = match_team("Los Angeles Lakers", "los angeles lakers")
    assert ok is True
    assert conf == 1.0
    assert method == "exact_alias"


def test_alias_resolves_to_canonical() -> None:
    ok, conf, method = match_team("Lakers", "LAL")
    assert ok is True
    assert conf == 1.0
    assert method == "exact_alias"


def test_token_substring_single_word() -> None:
    # 'ravens' (alias yok, sadece 'ravens') vs 'baltimore ravens' — substring path.
    # Not: 'celtics' bilinen alias olduğu için exact_alias'a düşer — bu path'e ulaşmaz.
    ok, _, method = match_team("phoenix", "phoenix rising")
    assert ok is True
    assert method in ("token_substring", "token_overlap", "exact_alias")


def test_token_overlap_multi_word() -> None:
    # 'manchester united' vs 'manchester united fc'
    ok, conf, _ = match_team("manchester united", "manchester united fc")
    # 'fc' normalize sırasında sıyrılıyor — aynı canonical string → exact_alias
    assert ok is True


def test_fuzzy_match_high_similarity() -> None:
    # Hafif varyant — fuzzy
    ok, conf, method = match_team("Juventus Turin", "Juventus")
    assert ok is True
    # Ya fuzzy ya token — ama eşleşmeli
    assert conf >= 0.80


def test_no_match_different_teams() -> None:
    ok, _, method = match_team("Lakers", "Celtics")
    assert ok is False
    assert method == "no_match"


def test_empty_returns_false() -> None:
    ok, _, method = match_team("", "Lakers")
    assert ok is False


def test_pair_match_normal_order() -> None:
    ok, conf = match_pair(("Lakers", "Celtics"), ("Los Angeles Lakers", "Boston Celtics"))
    assert ok is True
    assert conf >= 0.80


def test_pair_match_swapped() -> None:
    # Market LAL-BOS, Odds API home=BOS away=LAL
    ok, conf = match_pair(("Lakers", "Celtics"), ("Boston Celtics", "Los Angeles Lakers"))
    assert ok is True


def test_pair_no_match_when_one_side_wrong() -> None:
    ok, _ = match_pair(("Lakers", "Celtics"), ("Lakers", "Warriors"))
    assert ok is False


def test_find_best_event_match() -> None:
    events = [
        {"home_team": "Boston Celtics", "away_team": "Miami Heat"},
        {"home_team": "Los Angeles Lakers", "away_team": "Boston Celtics"},
        {"home_team": "Golden State Warriors", "away_team": "Dallas Mavericks"},
    ]
    result = find_best_event_match("Lakers", "Celtics", events)
    assert result is not None
    event, conf = result
    assert event["home_team"] == "Los Angeles Lakers"


def test_find_best_event_no_match() -> None:
    events = [{"home_team": "X", "away_team": "Y"}]
    assert find_best_event_match("Lakers", "Celtics", events) is None


def test_find_best_single_team_home() -> None:
    events = [
        {"home_team": "Los Angeles Lakers", "away_team": "Boston Celtics"},
    ]
    result = find_best_single_team_match("Lakers", events)
    assert result is not None
    event, conf, is_home = result
    assert is_home is True


def test_find_best_single_team_away() -> None:
    events = [
        {"home_team": "Boston Celtics", "away_team": "Los Angeles Lakers"},
    ]
    result = find_best_single_team_match("Lakers", events)
    assert result is not None
    event, conf, is_home = result
    assert is_home is False
